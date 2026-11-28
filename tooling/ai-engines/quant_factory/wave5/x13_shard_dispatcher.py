"""Wave 5 Owner-Override X13 Full-Performance Shard Dispatcher (`OrderSend = 0`, `Holdout 2025+ SEALED`).

Implements the HARD OWNER OVERRIDE for all Total Offensive #5 workloads:
  - `<DEV_PC>` MUST ALWAYS run strictly in `MODE_A_OWNER_ACTIVE`:
      * `2` CPU cores if GPU > 25% or fullscreen busy, else `3` CPU cores
      * `BELOW_NORMAL` OS priority (`0x00004000`)
      * `0%` GPU (strictly forbidden)
      * `force_mode_b=True` is HARD-REJECTED fail-closed (`OWNER_OVERRIDE_VIOLATION`).
  - `<X13_WORKER>` (`naqex-x13` -> `naqex-x13-ts`) runs at `FULL_PERFORMANCE`:
      * ALL available logical CPU cores (`os.cpu_count()`, default 8 threads on X13)
      * High share (`75-85%`, default `80%`) of multi-shard workloads, or `100%` when `x13_only=True`
      * Strictly enforces AC-only (`ACLineStatus == 1` & `BatteryStatus != 1`),
        RAM >= 4 GB, C: >= 15 GB, |NTP| < 1000 ms, `forbidden_files == 0`,
        and presence of all `required_packages`.
      * Silent automatic fallback to `<DEV_PC>` in `MODE_A_OWNER_ACTIVE` (NEVER Mode B)
        if X13 is offline, on battery, ineligible, missing a required package, or drops mid-flight.
  - Air-gap & OPSEC invariants:
      * Rejects forbidden tokens (`holdout`, `2025`, `2026`, `private_vault`, etc.) in any
        job_id, filename, directory, or argument (job IDs normalized to `w5_shard_<id>`).
      * Rejects any module importing `quant_core.holdout_guard` or `research_council.py`.
      * Zero bare `assert` statements (`python -O` safe), `CREATE_NO_WINDOW` on EVERY subprocess.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DATE: str = "2024-12-31"

DEV_PC_POLICY_MODE: str = "MODE_A_OWNER_ACTIVE"
DEV_PC_BELOW_NORMAL_PRIORITY_CLASS: int = 0x00004000
DEV_PC_MAX_CORES_GAMING: int = 2
DEV_PC_MAX_CORES_DESKTOP: int = 3
DEV_PC_GPU_ALLOWED: bool = False

X13_POLICY_MODE: str = "FULL_PERFORMANCE"
X13_MIN_SHARE_PCT: int = 75
X13_DEFAULT_SHARE_PCT: int = 80
X13_MAX_SHARE_PCT: int = 85
X13_DEFAULT_CORES_FALLBACK: int = 8
X13_WAVE5_NPZ_DIR_WIN: str = r"C:\NaqexResearch\wave5_m1_16sym_npz"
WAVE5_SHARD_JOB_PREFIX: str = "w5_shard_"
DEFAULT_REQUIRED_PACKAGES: tuple[str, ...] = ("numpy", "pyarrow")
PROBE_PACKAGES: tuple[str, ...] = ("numpy", "pyarrow", "numba", "duckdb", "scipy")

_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
_REPO_ROOT = Path(__file__).resolve().parents[4]
_AI_ENGINES_DIR = _REPO_ROOT / "tooling" / "ai-engines"


def _load_compute_router() -> Any:
    """Resolve `ops_cloud.compute_router` lazily (reusing any already-loaded compute_router module)."""
    if "ops_cloud.compute_router" in sys.modules:
        return sys.modules["ops_cloud.compute_router"]
    if "compute_router" in sys.modules:
        return sys.modules["compute_router"]
    ai_str = str(_AI_ENGINES_DIR)
    if ai_str not in sys.path and _AI_ENGINES_DIR.is_dir():
        sys.path.insert(0, ai_str)
    from ops_cloud import compute_router as cr

    return cr


def assert_dev_pc_mode_a_enforced(*, force_mode_b: bool = False) -> None:
    """Hard Owner Override guard: PC Dev MUST NEVER enter Mode B in Wave 5."""
    if force_mode_b:
        raise ValueError(
            "OWNER_OVERRIDE_VIOLATION: force_mode_b=True is forbidden on PC Dev in Wave 5 "
            "(strictly locked to MODE_A_OWNER_ACTIVE: 2-3 cores BELOW_NORMAL 0x4000, 0% GPU)"
        )


def normalize_wave5_job_id(raw_id: str) -> str:
    """Normalize a shard job identifier to `w5_shard_<id>` and reject any forbidden air-gap token."""
    cr = _load_compute_router()
    cleaned = str(raw_id or "").strip()
    if not cleaned:
        raise ValueError("Wave 5 shard job_id must be non-empty")
    if not cleaned.startswith(WAVE5_SHARD_JOB_PREFIX):
        cleaned = f"{WAVE5_SHARD_JOB_PREFIX}{cleaned}"
    return cr._validate_job_id(cleaned)


def assert_wave5_x13_safe_module(path: Path) -> None:
    """Fail-closed air-gap check rejecting forbidden path tokens, `research_council.py`, and `holdout_guard`."""
    cr = _load_compute_router()
    cr.assert_dev_only_module(path)


def compute_dev_pc_mode_a_cap(dev_pc: dict[str, Any]) -> dict[str, Any]:
    """Compute strict Wave 5 PC Dev `MODE_A_OWNER_ACTIVE` cap (2 cores gaming/GPU>25%, else 3; 0x4000; 0% GPU)."""
    cr = _load_compute_router()
    gpu_val = cr._finite_float(dev_pc.get("gpu_util_pct"))
    gaming_or_gpu = (gpu_val is None or gpu_val > 25.0) or bool(dev_pc.get("fullscreen_busy", False))
    cores = DEV_PC_MAX_CORES_GAMING if gaming_or_gpu else DEV_PC_MAX_CORES_DESKTOP
    return {
        "mode": DEV_PC_POLICY_MODE,
        "cores": cores,
        "priority": "BELOW_NORMAL",
        "priority_class": DEV_PC_BELOW_NORMAL_PRIORITY_CLASS,
        "gpu_allowed": DEV_PC_GPU_ALLOWED,
    }


def _probe_x13_runtime_details(
    alias: str,
    *,
    packages: Sequence[str] = PROBE_PACKAGES,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Run a single read-only SSH stdin inspection on `<X13_WORKER>` for CPU count, Python, packages, & NPZ count."""
    cr = _load_compute_router()
    safe_alias = cr._validate_host(alias)
    pkg_list = [str(p).strip() for p in packages if str(p).strip()]
    for pkg in pkg_list:
        cr.assert_dev_only_path(pkg)

    remote_script = (
        "import importlib, importlib.metadata, json, os, pathlib, platform, sys\n"
        f"pkgs = {pkg_list!r}\n"
        "versions = {}\n"
        "import_ok = {}\n"
        "for p in pkgs:\n"
        "    try:\n"
        "        versions[p] = importlib.metadata.version(p)\n"
        "    except Exception:\n"
        "        versions[p] = None\n"
        "    mod_name = p.replace('-', '_')\n"
        "    if mod_name == 'scikit_learn':\n"
        "        mod_name = 'sklearn'\n"
        "    try:\n"
        "        importlib.import_module(mod_name)\n"
        "        import_ok[p] = True\n"
        "    except Exception as exc:\n"
        "        import_ok[p] = f'ERR:{type(exc).__name__}'\n"
        "npz_dir = pathlib.Path(r'C:\\NaqexResearch\\wave5_m1_16sym_npz')\n"
        "npz_files = sorted(f.name for f in npz_dir.glob('*.npz')) if npz_dir.is_dir() else []\n"
        "print(json.dumps({\n"
        "    'python_version': sys.version.split()[0],\n"
        "    'cpu_count_logical': os.cpu_count(),\n"
        "    'platform': platform.platform(),\n"
        "    'packages': versions,\n"
        "    'import_ok': import_ok,\n"
        "    'wave5_npz_count': len(npz_files),\n"
        "    'wave5_npz_files': npz_files,\n"
        "}, sort_keys=True))\n"
    )
    proc = subprocess.run(
        [
            "ssh",
            "-o",
            "ConnectTimeout=4",
            "-o",
            "BatchMode=yes",
            safe_alias,
            f'"{cr.X13_REMOTE_PYTHON}" -',
        ],
        input=remote_script,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=_NO_WINDOW_FLAGS,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"x13_runtime_probe_failed(rc={proc.returncode}): {(proc.stderr or '').strip()[:200]}")
    data = json.loads((proc.stdout or "{}").strip())
    if not isinstance(data, dict):
        raise RuntimeError("x13_runtime_probe_malformed_json")
    return data


def probe_x13_full_capabilities(
    *,
    hosts: tuple[str, ...] | None = None,
    lan_only: bool = False,
    connect_timeout: int = 2,
    timeout: float = 15.0,
    strict_ntp: bool = True,
    allow_ntp_drift: bool = False,
    packages: Sequence[str] = PROBE_PACKAGES,
) -> dict[str, Any]:
    """Probe `<X13_WORKER>` health gates plus CPU core count, installed packages, and synced NPZ count."""
    cr = _load_compute_router()
    base_probe = cr.probe_x13_worker(
        hosts=hosts or cr.X13_HOSTS,
        lan_only=lan_only,
        connect_timeout=connect_timeout,
        strict_ntp=strict_ntp,
        allow_ntp_drift=allow_ntp_drift,
    )
    enriched = dict(base_probe)
    if base_probe.get("reachable") is not True:
        enriched.update(
            {
                "python_version": None,
                "cpu_count_logical": None,
                "platform": None,
                "packages": {p: None for p in packages},
                "import_ok": {p: False for p in packages},
                "wave5_npz_count": 0,
            }
        )
        return enriched

    try:
        details = _probe_x13_runtime_details(
            str(base_probe["ssh_alias"]),
            packages=packages,
            timeout=timeout,
        )
        enriched.update(details)
    except Exception as exc:
        enriched.update(
            {
                "python_version": None,
                "cpu_count_logical": None,
                "platform": None,
                "packages": {p: None for p in packages},
                "import_ok": {p: False for p in packages},
                "wave5_npz_count": 0,
                "runtime_probe_error": str(exc),
            }
        )
    return enriched


def evaluate_x13_wave5_eligibility(
    x13: dict[str, Any],
    *,
    min_ram_gb: float = 4.0,
    required_packages: Sequence[str] = DEFAULT_REQUIRED_PACKAGES,
    strict_ntp: bool = True,
    allow_ntp_drift: bool = False,
) -> tuple[bool, list[str]]:
    """Apply all X13 hardware/power/NTP/air-gap gates PLUS required package verification."""
    cr = _load_compute_router()
    ok, reasons = cr.evaluate_x13_eligibility(
        x13,
        min_ram_gb=min_ram_gb,
        strict_ntp=strict_ntp,
        allow_ntp_drift=allow_ntp_drift,
    )
    all_reasons = list(reasons)
    if x13.get("reachable") is True and required_packages:
        pkg_versions = x13.get("packages")
        import_map = x13.get("import_ok")
        for pkg in required_packages:
            pkg_name = str(pkg).strip()
            if not pkg_name:
                continue
            has_import_info = isinstance(import_map, dict) and pkg_name in import_map
            has_version_info = isinstance(pkg_versions, dict) and pkg_name in pkg_versions
            if has_import_info:
                if import_map[pkg_name] is not True:
                    all_reasons.append(f"x13_missing_package({pkg_name})")
            elif has_version_info:
                if not pkg_versions[pkg_name]:
                    all_reasons.append(f"x13_missing_package({pkg_name})")
            else:
                all_reasons.append(f"x13_missing_package({pkg_name})")
    return (ok and len(all_reasons) == 0), all_reasons


def decide_wave5_route(
    dev_pc: dict[str, Any],
    x13_worker: dict[str, Any],
    *,
    shard_count: int = 10,
    x13_share_pct: int = X13_DEFAULT_SHARE_PCT,
    min_ram_gb: float = 4.0,
    required_packages: Sequence[str] = DEFAULT_REQUIRED_PACKAGES,
    touches_holdout: bool = False,
    touches_vps: bool = False,
    requires_admin: bool = False,
    needs_gpu: bool = False,
    strict_ntp: bool = True,
    allow_ntp_drift: bool = False,
    x13_only: bool = False,
    force_mode_b: bool = False,
) -> dict[str, Any]:
    """Deterministic Wave 5 Owner-Override route decision: PC Dev Mode A + X13 Full Performance."""
    assert_dev_pc_mode_a_enforced(force_mode_b=force_mode_b)
    if isinstance(shard_count, bool) or not isinstance(shard_count, int) or shard_count < 1:
        raise ValueError(f"shard_count must be an int >= 1, got {shard_count!r}")
    if isinstance(x13_share_pct, bool) or not isinstance(x13_share_pct, int):
        raise ValueError(f"x13_share_pct must be an int in [75, 85], got {x13_share_pct!r}")
    if not x13_only and not (X13_MIN_SHARE_PCT <= x13_share_pct <= X13_MAX_SHARE_PCT):
        raise ValueError(
            f"x13_share_pct must be in [{X13_MIN_SHARE_PCT}, {X13_MAX_SHARE_PCT}], got {x13_share_pct!r}"
        )

    dev_cap = compute_dev_pc_mode_a_cap(dev_pc)
    reasons: list[str] = []

    # Tier 3 fail-closed safety gates
    if touches_vps:
        return _build_wave5_decision(
            target="BLOCKED_NEEDS_APPROVAL",
            ask_owner=True,
            dev_cap=dev_cap,
            dev_cores=0,
            x13_threads=0,
            x13_policy="BLOCKED",
            split={"dev_pc": 0, "x13_worker": 0},
            micro_shards={"total": shard_count, "dev_pc": 0, "x13_worker": 0},
            reasons=["naqex-node1 compute/mutations are strictly forbidden in Wave 5"],
        )
    if requires_admin:
        return _build_wave5_decision(
            target="BLOCKED_NEEDS_APPROVAL",
            ask_owner=True,
            dev_cap=dev_cap,
            dev_cores=0,
            x13_threads=0,
            x13_policy="BLOCKED",
            split={"dev_pc": 0, "x13_worker": 0},
            micro_shards={"total": shard_count, "dev_pc": 0, "x13_worker": 0},
            reasons=["Admin/UAC action requires explicit Tier-3 owner approval"],
        )
    if needs_gpu:
        return _build_wave5_decision(
            target="BLOCKED_NEEDS_APPROVAL",
            ask_owner=True,
            dev_cap=dev_cap,
            dev_cores=0,
            x13_threads=0,
            x13_policy="BLOCKED",
            split={"dev_pc": 0, "x13_worker": 0},
            micro_shards={"total": shard_count, "dev_pc": 0, "x13_worker": 0},
            reasons=["PC Dev is locked to MODE_A_OWNER_ACTIVE (0% GPU) in Wave 5"],
        )
    if touches_holdout:
        return _build_wave5_decision(
            target="DEV_PC_ONLY",
            ask_owner=True,
            dev_cap=dev_cap,
            dev_cores=dev_cap["cores"],
            x13_threads=0,
            x13_policy="AIRGAP_EXCLUDED",
            split={"dev_pc": 100, "x13_worker": 0},
            micro_shards={"total": shard_count, "dev_pc": shard_count, "x13_worker": 0},
            reasons=["Holdout 2025+ SEALED: strictly blocked from X13 and requires explicit owner unlock"],
        )

    x13_ok, x13_reasons = evaluate_x13_wave5_eligibility(
        x13_worker,
        min_ram_gb=min_ram_gb,
        required_packages=required_packages,
        strict_ntp=strict_ntp,
        allow_ntp_drift=allow_ntp_drift,
    )
    raw_cores = x13_worker.get("cpu_count_logical")
    if isinstance(raw_cores, int) and not isinstance(raw_cores, bool) and raw_cores >= 1:
        x13_all_cores = raw_cores
    else:
        x13_all_cores = X13_DEFAULT_CORES_FALLBACK

    if x13_ok:
        if x13_only or shard_count == 1:
            reasons.append(
                f"X13 eligible (AC-only, 0 forbidden) -> FULL_PERFORMANCE ({x13_all_cores} threads, 100% X13, 0 PC Dev)"
            )
            return _build_wave5_decision(
                target="X13_FULL_ONLY",
                ask_owner=False,
                dev_cap=dev_cap,
                dev_cores=0,
                x13_threads=x13_all_cores,
                x13_policy=X13_POLICY_MODE,
                split={"dev_pc": 0, "x13_worker": 100},
                micro_shards={"total": shard_count, "dev_pc": 0, "x13_worker": shard_count},
                reasons=reasons,
            )

        n_x13 = max(1, min(shard_count - 1, int(round(shard_count * (x13_share_pct / 100.0)))))
        n_dev = shard_count - n_x13
        dev_pct = 100 - x13_share_pct
        reasons.append(
            f"Wave 5 Owner Override: PC Dev locked to MODE_A_OWNER_ACTIVE "
            f"({dev_cap['cores']} cores BELOW_NORMAL 0x4000, 0% GPU, {dev_pct}%={n_dev} shards) "
            f"+ X13 FULL_PERFORMANCE ({x13_all_cores} threads, {x13_share_pct}%={n_x13} shards)"
        )
        return _build_wave5_decision(
            target="WAVE5_X13_FULL_PLUS_DEV_MODE_A",
            ask_owner=False,
            dev_cap=dev_cap,
            dev_cores=dev_cap["cores"],
            x13_threads=x13_all_cores,
            x13_policy=X13_POLICY_MODE,
            split={"dev_pc": dev_pct, "x13_worker": x13_share_pct},
            micro_shards={"total": shard_count, "dev_pc": n_dev, "x13_worker": n_x13},
            reasons=reasons,
        )

    fb_reason = "; ".join(x13_reasons) or "x13_ineligible"
    reasons.append(
        f"X13 ineligible ({fb_reason}) -> silent fallback to PC Dev strictly in MODE_A_OWNER_ACTIVE "
        f"({dev_cap['cores']} cores BELOW_NORMAL 0x4000, 0% GPU; NEVER Mode B)"
    )
    return _build_wave5_decision(
        target="DEV_PC_MODE_A_FALLBACK",
        ask_owner=False,
        dev_cap=dev_cap,
        dev_cores=dev_cap["cores"],
        x13_threads=0,
        x13_policy="FALLBACK_OFFLINE_OR_INELIGIBLE",
        split={"dev_pc": 100, "x13_worker": 0},
        micro_shards={"total": shard_count, "dev_pc": shard_count, "x13_worker": 0},
        fallback_used=True,
        fallback_reason=fb_reason,
        reasons=reasons,
    )


def _build_wave5_decision(
    *,
    target: str,
    ask_owner: bool,
    dev_cap: dict[str, Any],
    dev_cores: int,
    x13_threads: int,
    x13_policy: str,
    split: dict[str, int],
    micro_shards: dict[str, int],
    reasons: list[str],
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "policy": "WAVE5_OWNER_OVERRIDE_V5_3",
        "target": target,
        "ask_owner_required": ask_owner,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "dev_pc_mode": DEV_PC_POLICY_MODE,
        "dev_pc_cores": dev_cores,
        "dev_pc_priority": dev_cap["priority"],
        "dev_pc_priority_class": dev_cap["priority_class"],
        "dev_pc_gpu_allowed": False,
        "x13_policy": x13_policy,
        "x13_threads": x13_threads,
        "shard_split_pct": split,
        "micro_shards": micro_shards,
        "reasons": reasons,
    }


def dispatch_wave5_shards(
    job_id: str,
    entry_script: Path,
    shard_specs: Sequence[Any] | int,
    *,
    x13_share_pct: int = X13_DEFAULT_SHARE_PCT,
    min_ram_gb: float = 4.0,
    required_packages: Sequence[str] = DEFAULT_REQUIRED_PACKAGES,
    touches_holdout: bool = False,
    touches_vps: bool = False,
    requires_admin: bool = False,
    needs_gpu: bool = False,
    strict_ntp: bool = True,
    allow_ntp_drift: bool = False,
    x13_only: bool = False,
    force_mode_b: bool = False,
    lan_only: bool = False,
    dry_run: bool = False,
    dest_dir: Path | None = None,
    extra_files: tuple[Path, ...] = (),
    extra_args: list[str] | None = None,
    shard_arg_flag: str | None = None,
    lease_max_wait_sec: float = 60.0,
    lease_base_backoff_sec: float = 2.0,
    lease_max_backoff_sec: float = 15.0,
    lease_sleep_fn: Callable[[float], None] = time.sleep,
    result_filename: str = "shard_results.json",
    merge_fn: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None,
    timeout: int = 3600,
) -> dict[str, Any]:
    """Dispatch Wave 5 shards under the Owner Override policy (PC Dev Mode A + X13 Full Performance)."""
    assert_dev_pc_mode_a_enforced(force_mode_b=force_mode_b)
    cr = _load_compute_router()

    jid = normalize_wave5_job_id(job_id)
    safe_args = cr._validate_extra_args(extra_args)
    if shard_arg_flag is not None and not cr._SAFE_FLAG_RE.fullmatch(shard_arg_flag):
        raise ValueError(f"Unsafe shard_arg_flag rejected: {shard_arg_flag!r}")
    shards_list = cr._normalize_shard_specs(shard_specs)
    n_total = len(shards_list)

    entry = entry_script.resolve()
    if not touches_holdout:
        assert_wave5_x13_safe_module(entry)
        for ef in extra_files:
            assert_wave5_x13_safe_module(ef.resolve())

    dev_pc = cr.probe_dev_pc()
    probe_pkgs = tuple(dict.fromkeys((*PROBE_PACKAGES, *required_packages)))
    x13 = probe_x13_full_capabilities(
        lan_only=lan_only,
        strict_ntp=strict_ntp,
        allow_ntp_drift=allow_ntp_drift,
        packages=probe_pkgs,
    )

    decision = decide_wave5_route(
        dev_pc,
        x13,
        shard_count=n_total,
        x13_share_pct=x13_share_pct,
        min_ram_gb=min_ram_gb,
        required_packages=required_packages,
        touches_holdout=touches_holdout,
        touches_vps=touches_vps,
        requires_admin=requires_admin,
        needs_gpu=needs_gpu,
        strict_ntp=strict_ntp,
        allow_ntp_drift=allow_ntp_drift,
        x13_only=x13_only,
        force_mode_b=force_mode_b,
    )

    n_dev = int(decision["micro_shards"]["dev_pc"])
    n_x13 = int(decision["micro_shards"]["x13_worker"])
    dev_indices = list(range(0, n_dev))
    x13_indices = list(range(n_dev, n_dev + n_x13))

    out_dir = dest_dir or (_REPO_ROOT / ".tmp" / "wave5_results" / jid)
    shard_plan: dict[str, Any] = {
        "total_shards": n_total,
        "dev_pc_indices": dev_indices,
        "x13_worker_indices": x13_indices,
        "x13_atomic_batch": bool(x13_indices),
    }
    receipt: dict[str, Any] = {
        "schema": "naqex-wave5-x13-dispatch-v1",
        "job_id": jid,
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "dry_run": dry_run,
        "dev_pc": dev_pc,
        "x13_worker": x13,
        "decision": decision,
        "shard_plan": shard_plan,
        "dest_dir": str(out_dir),
    }

    blocked = decision["target"] == "BLOCKED_NEEDS_APPROVAL" or bool(decision.get("ask_owner_required"))
    if dry_run or blocked:
        receipt["ok"] = not blocked
        if blocked:
            receipt["blocked_reason"] = "TIER_3_ASK_OWNER_APPROVAL_REQUIRED"
        return receipt

    out_dir.mkdir(parents=True, exist_ok=True)
    workers_root = out_dir / "workers"
    workers_root.mkdir(parents=True, exist_ok=True)

    def _write_batch(path: Path, role: str, sub_jid: str, idxs: list[int]) -> Path:
        payload = {
            "schema": "naqex-shard-batch-v1",
            "job_id": jid,
            "batch_job_id": sub_jid,
            "worker": role,
            "total_shards": n_total,
            "shard_indices": idxs,
            "shards": [shards_list[i] for i in idxs],
        }
        cr._atomic_write_json(path, payload)
        return path

    def _run_dev_mode_a_slice(slice_name: str, idxs: list[int], cores: int) -> dict[str, Any]:
        sub_jid = f"{jid}_{slice_name}"[:64]
        sub_dir = workers_root / slice_name
        sub_dir.mkdir(parents=True, exist_ok=True)
        batch_path = _write_batch(sub_dir / "shard_batch.json", "DEV_PC", sub_jid, idxs)
        local_args = list(safe_args)
        if shard_arg_flag is not None:
            local_args.extend([shard_arg_flag, str(batch_path)])
        local_env = {
            "NAQEX_SHARD_BATCH_FILE": str(batch_path),
            "NAQEX_SHARD_INDICES": ",".join(str(i) for i in idxs),
            "NAQEX_SHARD_COUNT": str(len(idxs)),
            "NAQEX_TOTAL_SHARDS": str(n_total),
            "NAQEX_DEV_POLICY": DEV_PC_POLICY_MODE,
        }
        res = cr._run_local_dev_job(
            sub_jid,
            entry,
            sub_dir,
            cores=max(1, min(DEV_PC_MAX_CORES_DESKTOP, int(cores))),
            priority="BELOW_NORMAL",
            extra_args=local_args,
            extra_env=local_env,
            timeout=timeout,
        )
        return {
            "worker": slice_name,
            "executed_on": "DEV_PC",
            "shard_indices": idxs,
            "result_dir": sub_dir,
            "execution": res,
            "verify": res["verify"],
        }

    def _run_x13_full_slice(idxs: list[int]) -> dict[str, Any]:
        sub_jid = f"{jid}_x13"[:64]
        sub_dir = workers_root / "x13_worker"
        sub_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"w5_x13_batch_{sub_jid}_") as td:
            batch_path = _write_batch(Path(td) / "shard_batch.json", "X13_WORKER", sub_jid, idxs)
            res = cr._execute_x13_bundle(
                sub_jid,
                entry,
                sub_dir,
                alias=str(x13["ssh_alias"]),
                x13_threads=int(decision["x13_threads"]),
                safe_args=safe_args,
                extra_files=(*extra_files, batch_path),
                shard_batch_arc="shard_batch.json",
                shard_arg_flag=shard_arg_flag,
                timeout=timeout,
                lease_max_wait_sec=lease_max_wait_sec,
                lease_base_backoff_sec=lease_base_backoff_sec,
                lease_max_backoff_sec=lease_max_backoff_sec,
                lease_sleep_fn=lease_sleep_fn,
                lan_only=lan_only,
                strict_ntp=strict_ntp,
                allow_ntp_drift=allow_ntp_drift,
                ram_gb=min_ram_gb,
            )
        return {
            "worker": "x13_worker",
            "executed_on": "X13_WORKER",
            "shard_indices": idxs,
            "result_dir": sub_dir,
            "execution": res,
            "verify": res["verify"],
        }

    completed_workers: list[dict[str, Any]] = []
    x13_error: Exception | None = None
    dev_cap = compute_dev_pc_mode_a_cap(dev_pc)
    dev_cores = int(decision["dev_pc_cores"]) or dev_cap["cores"]

    if dev_indices and x13_indices:
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_dev = pool.submit(_run_dev_mode_a_slice, "dev_pc", dev_indices, dev_cores)
            f_x13 = pool.submit(_run_x13_full_slice, x13_indices)
            # Await PC Dev Mode-A slice first so any X13 fallback never oversubscribes the 2-3 core cap.
            completed_workers.append(f_dev.result())
            try:
                completed_workers.append(f_x13.result())
            except Exception as exc:
                x13_error = exc
    elif x13_indices:
        try:
            completed_workers.append(_run_x13_full_slice(x13_indices))
        except Exception as exc:
            x13_error = exc
    elif dev_indices:
        completed_workers.append(_run_dev_mode_a_slice("dev_pc", dev_indices, dev_cores))

    if x13_error is not None:
        # Silent fallback to PC Dev strictly in MODE_A_OWNER_ACTIVE (NEVER Mode B!)
        decision["fallback_used"] = True
        decision["fallback_reason"] = f"x13_runtime_fallback: {x13_error}"
        decision["dev_pc_mode"] = DEV_PC_POLICY_MODE
        decision["dev_pc_cores"] = dev_cap["cores"]
        decision["dev_pc_priority"] = "BELOW_NORMAL"
        decision["dev_pc_priority_class"] = DEV_PC_BELOW_NORMAL_PRIORITY_CLASS
        decision["dev_pc_gpu_allowed"] = False
        completed_workers.append(_run_dev_mode_a_slice("x13_fallback_dev_pc", x13_indices, dev_cap["cores"]))

    worker_payloads: list[dict[str, Any]] = []
    worker_receipts: list[dict[str, Any]] = []
    all_workers_ok = True
    for w in completed_workers:
        v = cr.verify_result_manifest(w["result_dir"])
        if not v["ok"]:
            all_workers_ok = False
        worker_receipts.append(
            {
                "worker": w["worker"],
                "executed_on": w["executed_on"],
                "shard_indices": w["shard_indices"],
                "result_dir": str(w["result_dir"]),
                "verify": v,
            }
        )
        res_file = w["result_dir"] / result_filename
        if v["ok"] and res_file.is_file():
            worker_payloads.append(
                {
                    "worker": w["worker"],
                    "executed_on": w["executed_on"],
                    "shard_indices": w["shard_indices"],
                    "payload": json.loads(res_file.read_text(encoding="utf-8")),
                }
            )

    if not all_workers_ok:
        receipt["ok"] = False
        receipt["status"] = "FAILED_INTEGRITY"
        receipt["workers"] = worker_receipts
        return receipt

    merged_payload: dict[str, Any] | None = None
    if worker_payloads:
        merged_payload = (
            merge_fn(worker_payloads)
            if merge_fn is not None
            else cr._default_merge_shard_payloads(worker_payloads)
        )
        cr._atomic_write_json(out_dir / "merged_results.json", merged_payload)

    hosts_used = sorted({w["executed_on"] for w in completed_workers})
    host_label = "+".join(hosts_used) if hosts_used else "DEV_PC"
    summary_doc: dict[str, Any] = {
        "schema": "naqex-wave5-dispatch-summary-v1",
        "job_id": jid,
        "target": decision["target"],
        "dev_pc_mode": DEV_PC_POLICY_MODE,
        "dev_pc_cores": decision["dev_pc_cores"],
        "dev_pc_priority": decision["dev_pc_priority"],
        "x13_policy": decision["x13_policy"],
        "x13_threads": decision["x13_threads"],
        "fallback_used": bool(decision.get("fallback_used")),
        "fallback_reason": decision.get("fallback_reason"),
        "hosts_executed": hosts_used,
        "shard_plan": shard_plan,
        "workers": worker_receipts,
        "merged_results_present": merged_payload is not None,
        "order_send_count": ORDER_SEND_COUNT,
        "completed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    cr._atomic_write_json(out_dir / "wave5_dispatch_summary.json", summary_doc)
    cr.write_result_manifest(out_dir, job_id=jid, host_label=host_label)
    merged_verify = cr.verify_result_manifest(out_dir)

    receipt["ok"] = bool(merged_verify["ok"])
    receipt["status"] = merged_verify["status"]
    receipt["hosts_executed"] = hosts_used
    receipt["workers"] = worker_receipts
    receipt["merged_verify"] = merged_verify
    if merged_payload is not None:
        receipt["merged_results_path"] = str(out_dir / "merged_results.json")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 5 Owner-Override X13 Full-Performance Shard Dispatcher.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe")
    p_probe.add_argument("--lan-only", action="store_true")
    p_probe.add_argument("--allow-ntp-drift", action="store_true")

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--shards", type=int, default=16)
    p_plan.add_argument("--x13-share-pct", type=int, default=X13_DEFAULT_SHARE_PCT)
    p_plan.add_argument("--required-packages", nargs="*", default=list(DEFAULT_REQUIRED_PACKAGES))
    p_plan.add_argument("--x13-only", action="store_true")
    p_plan.add_argument("--lan-only", action="store_true")

    args = ap.parse_args(argv)
    cr = _load_compute_router()

    if args.cmd == "probe":
        dev_pc = cr.probe_dev_pc()
        x13 = probe_x13_full_capabilities(lan_only=args.lan_only, allow_ntp_drift=args.allow_ntp_drift)
        out = {
            "schema": "naqex-wave5-x13-probe-v1",
            "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_send_count": ORDER_SEND_COUNT,
            "dev_pc": dev_pc,
            "dev_pc_wave5_cap": compute_dev_pc_mode_a_cap(dev_pc),
            "x13_worker": x13,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "plan":
        dev_pc = cr.probe_dev_pc()
        x13 = probe_x13_full_capabilities(lan_only=args.lan_only)
        dec = decide_wave5_route(
            dev_pc,
            x13,
            shard_count=args.shards,
            x13_share_pct=args.x13_share_pct,
            required_packages=args.required_packages,
            x13_only=args.x13_only,
        )
        out = {
            "schema": "naqex-wave5-x13-plan-v1",
            "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_send_count": ORDER_SEND_COUNT,
            "dev_pc": dev_pc,
            "x13_worker": x13,
            "decision": dec,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 2 if dec.get("ask_owner_required") else 0

    return 1


__all__ = [
    "DEFAULT_REQUIRED_PACKAGES",
    "DEV_PC_BELOW_NORMAL_PRIORITY_CLASS",
    "DEV_PC_GPU_ALLOWED",
    "DEV_PC_MAX_CORES_DESKTOP",
    "DEV_PC_MAX_CORES_GAMING",
    "DEV_PC_POLICY_MODE",
    "HOLDOUT_CUTOFF_DATE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PROBE_PACKAGES",
    "WAVE5_SHARD_JOB_PREFIX",
    "X13_DEFAULT_CORES_FALLBACK",
    "X13_DEFAULT_SHARE_PCT",
    "X13_MAX_SHARE_PCT",
    "X13_MIN_SHARE_PCT",
    "X13_POLICY_MODE",
    "X13_WAVE5_NPZ_DIR_WIN",
    "assert_dev_pc_mode_a_enforced",
    "assert_wave5_x13_safe_module",
    "compute_dev_pc_mode_a_cap",
    "decide_wave5_route",
    "dispatch_wave5_shards",
    "evaluate_x13_wave5_eligibility",
    "normalize_wave5_job_id",
    "probe_x13_full_capabilities",
]

if __name__ == "__main__":
    raise SystemExit(main())
