"""Offline contract & integration tests for Mode-Aware Parallel Dispatcher, Safe Lease Queue, and Atomic Dev Cache.

100% offline (zero SSH/network calls, OrderSend = 0, Holdout 2025+ strictly sealed),
and fully `python -O` safe via `_check(...)`.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
OPS_CLOUD = AI_ENGINES / "ops_cloud"
for _p in (AI_ENGINES, OPS_CLOUD):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import compute_router as cr  # noqa: E402
import x13_probe  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Assertion helper immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _healthy_x13(**overrides) -> dict:
    base = {
        "ssh_alias": "naqex-x13",
        "transport": "LAN",
        "probe_ms": 210.0,
        "reachable": True,
        "ac_online": True,
        "ac_line_status": 1,
        "battery_status_code": 2,
        "battery_pct": 100,
        "cpu_util_pct": 4.5,
        "free_ram_gb": 11.4,
        "disk_free_gb": 130.0,
        "venv_ok": True,
        "active_job_lock": None,
        "ntp_offset_ms": -18.0,
        "forbidden_files": 0,
        "eligible": True,
        "ineligible_reasons": [],
    }
    base.update(overrides)
    return base


def _mode_b_idle_dev(**overrides) -> dict:
    base = {
        "mode": "MODE_B_IDLE_OVERNIGHT",
        "idle_sec": 1800.0,
        "in_overnight_window_ict": True,
        "gpu_util_pct": 2,
        "fullscreen_busy": False,
        "cpu_util_pct": 4.0,
        "free_ram_gb": 22.0,
        "ntp_offset_ms": -14.0,
        "ntp_ok": True,
    }
    base.update(overrides)
    return base


def _mode_a_gaming_dev(**overrides) -> dict:
    base = {
        "mode": "MODE_A_OWNER_ACTIVE",
        "idle_sec": 8.0,
        "in_overnight_window_ict": False,
        "gpu_util_pct": 64,
        "fullscreen_busy": True,
        "cpu_util_pct": 18.0,
        "free_ram_gb": 18.0,
        "ntp_offset_ms": -16.0,
        "ntp_ok": True,
    }
    base.update(overrides)
    return base


def _make_shard_worker_script(path: Path) -> Path:
    path.write_text(
        "import json, os, pathlib\n"
        "batch_file = pathlib.Path(os.environ['NAQEX_SHARD_BATCH_FILE'])\n"
        "batch = json.loads(batch_file.read_text(encoding='utf-8'))\n"
        "role = os.environ.get('NAQEX_WORKER_ROLE', 'UNKNOWN')\n"
        "threads = int(os.environ.get('NUMBA_NUM_THREADS', '0'))\n"
        "results = [\n"
        "    {\n"
        "        'index': idx,\n"
        "        'shard_id': spec['shard_id'] if isinstance(spec, dict) else idx,\n"
        "        'value': (spec['x'] * 2) if isinstance(spec, dict) and 'x' in spec else idx * 10,\n"
        "        'worker_role': role,\n"
        "        'threads': threads,\n"
        "    }\n"
        "    for idx, spec in zip(batch['shard_indices'], batch['shards'])\n"
        "]\n"
        "res_dir = pathlib.Path(os.environ['NAQEX_RESULT_DIR'])\n"
        "(res_dir / 'shard_results.json').write_text(\n"
        "    json.dumps({'worker': role, 'shards': results}, indent=2) + '\\n',\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _make_sandboxed_x13_executor(fake_x13_root: Path, call_log: list[dict]):
    """Simulate `_execute_x13_bundle` offline by running real `_REMOTE_RUNNER_PY` in `fake_x13_root`."""
    (fake_x13_root / "locks").mkdir(parents=True, exist_ok=True)
    (fake_x13_root / "tooling" / "ai-engines").mkdir(parents=True, exist_ok=True)

    def _exec(
        job_id: str,
        entry: Path,
        out_dir: Path,
        *,
        alias: str,
        x13_threads: int,
        safe_args: list[str],
        extra_files: tuple[Path, ...] = (),
        shard_batch_arc: str | None = None,
        shard_arg_flag: str | None = None,
        **_kw,
    ) -> dict:
        call_log.append(
            {
                "job_id": job_id,
                "alias": alias,
                "x13_threads": x13_threads,
                "shard_batch_arc": shard_batch_arc,
                "extra_files": [p.name for p in extra_files],
            }
        )
        job_dir = fake_x13_root / "jobs" / job_id
        cr.build_job_bundle(
            job_id,
            entry,
            job_dir,
            extra_files=extra_files,
            shard_batch_arc=shard_batch_arc,
            shard_arg_flag=shard_arg_flag,
        )
        patched_runner = cr._REMOTE_RUNNER_PY.replace(
            'base = pathlib.Path(r"C:\\NaqexResearch")',
            f"base = pathlib.Path({str(fake_x13_root)!r})",
        ).replace(
            "return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))) and int(s.AC) == 1",
            "return True",
        )
        runner_py = job_dir / "run_job.py"
        runner_py.write_text(patched_runner, encoding="utf-8", newline="\n")

        proc = subprocess.run(
            [sys.executable, str(runner_py), job_id, str(x13_threads), *safe_args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        _check(proc.returncode == 0, f"Sandboxed X13 runner failed rc={proc.returncode}: {proc.stderr}")

        remote_res = fake_x13_root / "results" / job_id
        verify_remote = cr.verify_result_manifest(remote_res)
        _check(verify_remote["ok"] is True, f"Remote manifest failed: {verify_remote}")
        _check(not (fake_x13_root / "locks" / "active_job.lock").exists(), "active_job.lock must be cleaned up")

        out_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(remote_res.rglob("*")):
            if src.is_file():
                dst = out_dir / src.relative_to(remote_res)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())

        verify_pulled = cr.verify_result_manifest(out_dir)
        _check(verify_pulled["ok"] is True, f"Pulled manifest failed: {verify_pulled}")
        return {
            "executed_on": "X13_WORKER",
            "ssh_alias": alias,
            "x13_threads": x13_threads,
            "lock_retries": 0,
            "pull": {"ok": True, "status": "VERIFIED_PASS", "verify": verify_pulled},
            "verify": verify_pulled,
        }

    return _exec


# ==============================================================================
# 1. PARALLEL_60_40 (Mode B) & PARALLEL_20_80_MODE_A (Mode A Assist)
# ==============================================================================


def test_parallel_60_40_mode_b_concurrent_atomic_batch_and_verified_merge(tmp_path: Path) -> None:
    worker = _make_shard_worker_script(tmp_path / "shard_worker.py")
    shards = [{"shard_id": i, "x": i + 1} for i in range(10)]
    x13_calls: list[dict] = []
    out_dir = tmp_path / "out_60_40"

    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_b_idle_dev()),
        patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()),
        patch.object(
            cr,
            "_execute_x13_bundle",
            side_effect=_make_sandboxed_x13_executor(tmp_path / "fake_x13", x13_calls),
        ),
    ):
        receipt = cr.dispatch_parallel_shards(
            "par6040_v1",
            worker,
            shards,
            est_minutes=30.0,
            dest_dir=out_dir,
            lease_max_wait_sec=0.0,
        )

    _check(receipt["ok"] is True, f"Expected ok=True, got {receipt}")
    _check(receipt["decision"]["target"] == "PARALLEL_60_40", "Mode B >=15m shardable must select PARALLEL_60_40")
    _check(receipt["decision"]["dev_pc_cores"] == 5, "Mode B dev_pc_cores must be 5")
    _check(receipt["decision"]["dev_pc_priority"] == "NORMAL", "Mode B priority must be NORMAL")
    _check(receipt["decision"]["x13_threads"] == 7, "X13 must use 7 threads")
    _check(receipt["shard_plan"]["dev_pc_indices"] == [0, 1, 2, 3, 4, 5], "60% of 10 shards -> 6 on PC Dev")
    _check(receipt["shard_plan"]["x13_worker_indices"] == [6, 7, 8, 9], "40% of 10 shards -> 4 on X13")
    _check(len(x13_calls) == 1, "X13 share MUST execute as exactly 1 atomic batched job (single active_job.lock)")
    _check(x13_calls[0]["x13_threads"] == 7, "X13 batched job must receive 7 threads")
    _check(receipt["hosts_executed"] == ["DEV_PC", "X13_WORKER"], f"Unexpected hosts: {receipt['hosts_executed']}")
    _check(receipt["merged_verify"]["ok"] is True, "Merged manifest.sha256.json must verify")

    merged = json.loads((out_dir / "merged_results.json").read_text(encoding="utf-8"))
    _check(merged["total_merged_items"] == 10, "All 10 shards must be merged")
    _check([s["index"] for s in merged["shards"]] == list(range(10)), "Merged shard indices must be 0..9 sorted")
    _check([s["value"] for s in merged["shards"]] == [(i + 1) * 2 for i in range(10)], "Merged values mismatch")
    dev_roles = [s["worker_role"] for s in merged["shards"][:6]]
    x13_roles = [s["worker_role"] for s in merged["shards"][6:]]
    _check(dev_roles == ["DEV_PC"] * 6, f"First 6 shards must come from DEV_PC: {dev_roles}")
    _check(x13_roles == ["X13_WORKER"] * 4, f"Last 4 shards must come from X13_WORKER: {x13_roles}")
    _check(cr.verify_result_manifest(out_dir)["ok"] is True, "Top-level manifest.sha256.json must pass")


def test_parallel_20_80_mode_a_assist_capped_2_cores_below_normal(tmp_path: Path) -> None:
    worker = _make_shard_worker_script(tmp_path / "shard_worker_mode_a.py")
    shards = [{"shard_id": i, "x": i + 10} for i in range(10)]
    x13_calls: list[dict] = []
    out_dir = tmp_path / "out_20_80"

    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_a_gaming_dev()),
        patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()),
        patch.object(
            cr,
            "_execute_x13_bundle",
            side_effect=_make_sandboxed_x13_executor(tmp_path / "fake_x13_a", x13_calls),
        ),
    ):
        receipt = cr.dispatch_parallel_shards(
            "par2080_v1",
            worker,
            shards,
            est_minutes=20.0,
            allow_mode_a_assist=True,
            dest_dir=out_dir,
            lease_max_wait_sec=0.0,
        )

    _check(receipt["ok"] is True, f"Expected ok=True, got {receipt}")
    _check(receipt["decision"]["target"] == "PARALLEL_20_80_MODE_A", "Expected PARALLEL_20_80_MODE_A")
    _check(1 <= receipt["decision"]["dev_pc_cores"] <= 2, "Mode A assist must cap PC Dev <= 2 cores")
    _check(receipt["decision"]["dev_pc_priority"] == "BELOW_NORMAL", "Mode A assist must run BELOW_NORMAL")
    _check(receipt["decision"]["dev_pc_gpu_allowed"] is False, "Mode A assist must forbid GPU (0% GPU)")
    _check(receipt["shard_plan"]["dev_pc_indices"] == [0, 1], "20% of 10 shards -> 2 on PC Dev")
    _check(receipt["shard_plan"]["x13_worker_indices"] == [2, 3, 4, 5, 6, 7, 8, 9], "80% -> 8 on X13")
    _check(len(x13_calls) == 1, "X13 80% slice must run as 1 atomic batched job")

    merged = json.loads((out_dir / "merged_results.json").read_text(encoding="utf-8"))
    _check([s["index"] for s in merged["shards"]] == list(range(10)), "All 10 shards must merge cleanly")
    _check([s["worker_role"] for s in merged["shards"][:2]] == ["DEV_PC", "DEV_PC"], "Shards 0..1 on DEV_PC")
    _check([s["worker_role"] for s in merged["shards"][2:]] == ["X13_WORKER"] * 8, "Shards 2..9 on X13")
    _check(merged["shards"][0]["threads"] <= 2, "PC Dev slice thread env must obey <=2 core cap")
    _check(merged["shards"][2]["threads"] == 7, "X13 slice must run with 7 threads")


def test_mode_a_default_parallel_dispatcher_offloads_100pct_x13_only(tmp_path: Path) -> None:
    worker = _make_shard_worker_script(tmp_path / "shard_worker_x13_only.py")
    x13_calls: list[dict] = []
    out_dir = tmp_path / "out_x13_only"

    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_a_gaming_dev()),
        patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()),
        patch.object(
            cr,
            "_execute_x13_bundle",
            side_effect=_make_sandboxed_x13_executor(tmp_path / "fake_x13_only", x13_calls),
        ),
    ):
        receipt = cr.dispatch_parallel_shards(
            "mode_a_x13_only",
            worker,
            6,
            est_minutes=20.0,
            allow_mode_a_assist=False,
            dest_dir=out_dir,
            lease_max_wait_sec=0.0,
        )

    _check(receipt["ok"] is True, "Expected ok=True")
    _check(receipt["decision"]["target"] == "X13_ONLY", "Mode A default must be X13_ONLY")
    _check(receipt["decision"]["dev_pc_cores"] == 0, "Mode A default uses 0 PC Dev cores")
    _check(receipt["shard_plan"]["dev_pc_indices"] == [], "0 shards on PC Dev")
    _check(receipt["shard_plan"]["x13_worker_indices"] == [0, 1, 2, 3, 4, 5], "100% shards on X13")
    _check(len(x13_calls) == 1, "100% X13 slice runs as 1 atomic batched job")
    _check(receipt["hosts_executed"] == ["X13_WORKER"], "Only X13_WORKER should execute")


# ==============================================================================
# 2. SILENT AUTOMATIC FALLBACK (X13 OFFLINE & MID-FLIGHT FAILURE)
# ==============================================================================


def test_parallel_dispatcher_silent_fallback_when_x13_offline_obeys_mode_caps(tmp_path: Path) -> None:
    worker = _make_shard_worker_script(tmp_path / "shard_worker_fb.py")
    x13_offline = _healthy_x13(reachable=False, eligible=False, ineligible_reasons=["x13_ssh_unreachable(naqex-x13)"])

    # Mode A gaming + X13 offline -> PC Dev capped at 2 cores BELOW_NORMAL
    out_a = tmp_path / "fb_mode_a"
    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_a_gaming_dev()),
        patch.object(cr, "probe_x13_worker", return_value=x13_offline),
    ):
        res_a = cr.dispatch_parallel_shards(
            "fb_mode_a_v1",
            worker,
            5,
            est_minutes=25.0,
            allow_mode_a_assist=True,
            dest_dir=out_a,
            lease_max_wait_sec=10.0,
            lease_sleep_fn=lambda _s: None,
        )
    _check(res_a["ok"] is True, "Mode A offline fallback must succeed")
    _check(res_a["decision"]["target"] == "DEV_PC_ONLY", "Must fall back to DEV_PC_ONLY")
    _check(res_a["decision"]["fallback_used"] is True, "Must record fallback_used=True")
    _check(res_a["decision"]["dev_pc_cores"] == 2, "Mode A gaming cap must stay 2 cores")
    _check(res_a["decision"]["dev_pc_priority"] == "BELOW_NORMAL", "Mode A priority must stay BELOW_NORMAL")
    _check(res_a["lease"]["attempts"] == 1 and res_a["lease"]["waited_sec"] == 0.0, "Offline X13 must fail-fast!")
    merged_a = json.loads((out_a / "merged_results.json").read_text(encoding="utf-8"))
    _check([s["index"] for s in merged_a["shards"]] == [0, 1, 2, 3, 4], "All 5 shards must complete locally")

    # Mode B idle + X13 offline -> PC Dev 5 cores NORMAL
    out_b = tmp_path / "fb_mode_b"
    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_b_idle_dev()),
        patch.object(cr, "probe_x13_worker", return_value=x13_offline),
    ):
        res_b = cr.dispatch_parallel_shards(
            "fb_mode_b_v1",
            worker,
            5,
            est_minutes=25.0,
            dest_dir=out_b,
            lease_max_wait_sec=0.0,
        )
    _check(res_b["ok"] is True, "Mode B offline fallback must succeed")
    _check(res_b["decision"]["dev_pc_cores"] == 5, "Mode B cap must be 5 cores")
    _check(res_b["decision"]["dev_pc_priority"] == "NORMAL", "Mode B priority must be NORMAL")
    _check(res_b["decision"]["fallback_used"] is True, "Must record fallback_used=True")


def test_parallel_dispatcher_midflight_x13_drop_falls_back_sequentially_on_dev(tmp_path: Path) -> None:
    worker = _make_shard_worker_script(tmp_path / "shard_worker_midflight.py")
    out_dir = tmp_path / "midflight_fb"
    local_events: list[str] = []
    real_local = cr._run_local_dev_job

    def tracked_local(job_id: str, *args, **kwargs):
        local_events.append(f"start:{job_id}:cores={kwargs['cores']}:prio={kwargs['priority']}")
        res = real_local(job_id, *args, **kwargs)
        local_events.append(f"end:{job_id}")
        return res

    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_a_gaming_dev()),
        patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()),
        patch.object(cr, "_run_local_dev_job", side_effect=tracked_local),
        patch.object(cr, "_execute_x13_bundle", side_effect=RuntimeError("x13_ac_unplugged_during_run")),
    ):
        receipt = cr.dispatch_parallel_shards(
            "midflight_v1",
            worker,
            10,
            est_minutes=20.0,
            allow_mode_a_assist=True,
            dest_dir=out_dir,
            lease_max_wait_sec=0.0,
        )

    _check(receipt["ok"] is True, "Mid-flight fallback must still complete and verify")
    _check(receipt["decision"]["fallback_used"] is True, "Must record fallback_used=True")
    _check("x13_ac_unplugged_during_run" in (receipt["decision"]["fallback_reason"] or ""), "Must keep root cause")
    # Primary local slice MUST end before fallback local slice starts (never oversubscribe Mode A 2-core cap!)
    _check(len(local_events) == 4, f"Expected 2 sequential local slices, got {local_events}")
    _check(local_events[1].startswith("end:"), f"Primary dev slice must finish before fallback starts: {local_events}")
    _check("cores=2:prio=BELOW_NORMAL" in local_events[2], f"Fallback must obey Mode A cap: {local_events}")
    merged = json.loads((out_dir / "merged_results.json").read_text(encoding="utf-8"))
    _check(
        [s["index"] for s in merged["shards"]] == list(range(10)),
        "All 10 shards must merge after mid-flight fallback",
    )


def test_parallel_dispatcher_blocks_holdout_fail_closed(tmp_path: Path) -> None:
    marker = tmp_path / "never_run.flag"
    sentinel = tmp_path / "holdout_shard_sentinel.py"
    sentinel.write_text(f"import pathlib\npathlib.Path({str(marker)!r}).write_text('BAD')\n", encoding="utf-8")

    # Forbidden air-gap token in job_id itself fails closed immediately
    with pytest.raises(ValueError, match="forbidden air-gap token"):
        cr.dispatch_parallel_shards(
            "holdout_par_block",
            sentinel,
            4,
            est_minutes=20.0,
            touches_holdout=True,
            dest_dir=tmp_path / "blocked_out_bad_id",
        )

    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_b_idle_dev()),
        patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()),
    ):
        res = cr.dispatch_parallel_shards(
            "hold_par_block_v1",
            sentinel,
            4,
            est_minutes=20.0,
            touches_holdout=True,
            dest_dir=tmp_path / "blocked_out",
        )
    _check(res["ok"] is False, "Holdout parallel dispatch must be blocked")
    _check(res.get("blocked_reason") == "TIER_3_ASK_OWNER_APPROVAL_REQUIRED", "Must require Tier-3 approval")
    _check(not marker.exists(), "Holdout sentinel script must NEVER execute")


# ==============================================================================
# 3. X13 SAFE LEASE QUEUE (RETRY + JITTERED BACKOFF AROUND active_job.lock)
# ==============================================================================


def test_safe_lease_queue_retries_busy_lock_with_jittered_backoff_and_fails_fast_otherwise(tmp_path: Path) -> None:
    busy = _healthy_x13(
        active_job_lock={"job_id": "job_prev", "pid": 9999, "created_at": "2026-11-27T00:00:00Z"},
        eligible=False,
        ineligible_reasons=["x13_busy_active_job_lock"],
    )
    free = _healthy_x13()

    # 1. Busy for 3 probes -> frees on 4th -> acquired with exponential jittered sleeps
    seq = iter([busy, busy, busy, free])
    sleeps_called: list[float] = []
    lease = cr.wait_for_x13_lease(
        probe_fn=lambda: next(seq),
        max_wait_sec=60.0,
        base_backoff_sec=2.0,
        max_backoff_sec=10.0,
        jitter_frac=0.25,
        sleep_fn=sleeps_called.append,
        rng=random.Random(42),
    )
    _check(lease["acquired"] is True, f"Expected lease acquired, got {lease}")
    _check(lease["status"] == "LEASE_ACQUIRED", "Expected LEASE_ACQUIRED")
    _check(lease["attempts"] == 4, f"Expected 4 attempts, got {lease['attempts']}")
    _check(len(sleeps_called) == 3, f"Expected 3 backoff sleeps, got {sleeps_called}")
    _check(1.5 <= sleeps_called[0] <= 2.5, f"Attempt 1 jittered backoff out of [1.5,2.5]: {sleeps_called[0]}")
    _check(3.0 <= sleeps_called[1] <= 5.0, f"Attempt 2 jittered backoff out of [3.0,5.0]: {sleeps_called[1]}")
    _check(6.0 <= sleeps_called[2] <= 10.0, f"Attempt 3 jittered backoff out of [6.0,10.0]: {sleeps_called[2]}")

    # 2. Timeout when X13 stays busy past max_wait_sec (never crashes)
    sleeps_to: list[float] = []
    lease_to = cr.wait_for_x13_lease(
        probe_fn=lambda: busy,
        max_wait_sec=5.0,
        base_backoff_sec=2.0,
        max_backoff_sec=4.0,
        jitter_frac=0.0,
        sleep_fn=sleeps_to.append,
    )
    _check(lease_to["acquired"] is False, "Must return acquired=False on timeout")
    _check(lease_to["status"] == "LEASE_TIMEOUT", f"Expected LEASE_TIMEOUT, got {lease_to['status']}")
    _check(abs(sum(sleeps_to) - 5.0) < 1e-6, f"Total waited must cap at max_wait_sec=5.0, got {sleeps_to}")

    # 3. Fail-fast immediately on non-lock errors (even if active_job_lock is also set!)
    for bad_x13 in (
        _healthy_x13(reachable=False, ineligible_reasons=["x13_unreachable"]),
        _healthy_x13(ac_online=False, ac_line_status=0, battery_status_code=1, active_job_lock={"job_id": "x"}),
        _healthy_x13(forbidden_files=1, active_job_lock={"job_id": "x"}),
    ):
        ff_sleeps: list[float] = []
        res_ff = cr.wait_for_x13_lease(
            probe_fn=lambda b=bad_x13: b,
            max_wait_sec=30.0,
            sleep_fn=ff_sleeps.append,
        )
        _check(res_ff["acquired"] is False, "Ineligible X13 must not acquire lease")
        _check(res_ff["status"] == "X13_INELIGIBLE", f"Must fail fast with X13_INELIGIBLE, got {res_ff}")
        _check(res_ff["attempts"] == 1 and not ff_sleeps, "Must NOT sleep on non-lock ineligibility")

    # 4. Integration inside dispatch_parallel_shards: busy -> free on 3rd poll -> completes PARALLEL_60_40
    worker = _make_shard_worker_script(tmp_path / "shard_worker_lease.py")
    poll_seq = iter([busy, busy, free])
    x13_calls: list[dict] = []
    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_b_idle_dev()),
        patch.object(cr, "probe_x13_worker", side_effect=lambda **_kw: next(poll_seq)),
        patch.object(
            cr,
            "_execute_x13_bundle",
            side_effect=_make_sandboxed_x13_executor(tmp_path / "fake_x13_lease", x13_calls),
        ),
    ):
        rec = cr.dispatch_parallel_shards(
            "lease_par_v1",
            worker,
            10,
            est_minutes=20.0,
            dest_dir=tmp_path / "lease_out",
            lease_max_wait_sec=30.0,
            lease_base_backoff_sec=0.5,
            lease_sleep_fn=lambda _s: None,
        )
    _check(
        rec["ok"] is True and rec["decision"]["target"] == "PARALLEL_60_40",
        "Queued job must succeed on PARALLEL_60_40",
    )
    _check(
        rec["lease"]["acquired"] is True and rec["lease"]["attempts"] == 3,
        f"Expected 3 lease attempts: {rec['lease']}",
    )
    _check(len(x13_calls) == 1, "Expected 1 atomic X13 batch after lease acquired")


# ==============================================================================
# 4. P0-2 ATOMIC sync_dev_cache() (1 tar.gz, EXCLUDES holdout_guard, INCLUDES 6ccy)
# ==============================================================================


@pytest.mark.local_cache
def test_real_workspace_dev_cache_allowlist_excludes_holdout_guard_and_verifies_tapes_v2() -> None:
    collected = cr.collect_dev_cache_files(root=cr.ROOT, include_tapes=True)
    arcs = [arc for arc, _ in collected["entries"]]
    arc_set = set(arcs)

    # Exact 40/41 quant_core/*.py (holdout_guard.py STRICTLY excluded!)
    _check(
        collected["counts"]["quant_core"] == 40,
        f"Expected 40/41 quant_core/*.py, got {collected['counts']['quant_core']}",
    )
    _check(collected["holdout_guard_excluded"] is True, "holdout_guard_excluded flag must be True")
    _check("tooling/ai-engines/quant_core/holdout_guard.py" not in arc_set, "holdout_guard.py MUST NEVER be archived!")
    _check("tooling/ai-engines/quant_core/metrics.py" in arc_set, "quant_core/metrics.py must be included")
    _check("tooling/ai-engines/quant_core/prop_sim.py" in arc_set, "quant_core/prop_sim.py must be included")

    # capital_optimizer/, configs/ssot/, red_news_official_2018_2024_6ccy.json, frozen_9e_tapes_v2.{json,npz}
    _check(
        collected["counts"]["capital_optimizer"] >= 20,
        f"Expected capital_optimizer files, got {collected['counts']}",
    )
    _check(
        "tooling/ai-engines/quant_factory/capital_optimizer/__init__.py" in arc_set,
        "capital_optimizer/__init__.py missing",
    )
    _check("tooling/ai-engines/configs/ssot/firms_catalog.json" in arc_set, "configs/ssot/firms_catalog.json missing")
    _check("tooling/ai-engines/configs/ssot/fx_rates.json" in arc_set, "configs/ssot/fx_rates.json missing")
    _check("tooling/ai-engines/configs/ssot/risk_profiles.json" in arc_set, "configs/ssot/risk_profiles.json missing")
    _check(
        "tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json" in arc_set,
        "red_news_official_2018_2024_6ccy.json MUST be included!",
    )
    _check(
        "tooling/ai-engines/configs/calendars/red_news_official_2025_2026.json" not in arc_set,
        "2025/2026 calendar MUST be excluded!",
    )
    _check(
        "tooling/ai-engines/configs/calendars/red_news_official_2026_2027_multi_ccy.json" not in arc_set,
        "2026/2027 calendar MUST be excluded!",
    )
    _check(".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.json" in arc_set, "frozen_9e_tapes_v2.json missing")
    _check(".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz" in arc_set, "frozen_9e_tapes_v2.npz missing")
    _check(
        collected["frozen_9e_tapes_v2"]["verified"] is True,
        f"frozen_9e_tapes_v2 failed check: {collected['frozen_9e_tapes_v2']}",
    )

    # Zero forbidden tokens in ANY archived member
    for arc in arcs:
        cr.assert_dev_only_path(arc)


def test_atomic_dev_cache_tar_gz_pack_and_remote_unpack_airgap(tmp_path: Path) -> None:
    fake_root = tmp_path / "repo"
    qc = fake_root / "tooling/ai-engines/quant_core"
    cap = fake_root / "tooling/ai-engines/quant_factory/capital_optimizer"
    ssot = fake_root / "tooling/ai-engines/configs/ssot"
    cals = fake_root / "tooling/ai-engines/configs/calendars"
    derived = fake_root / ".runtime/hot-m1-cache/_derived"
    for d in (qc, cap, ssot, cals, derived):
        d.mkdir(parents=True)

    (qc / "__init__.py").write_text("", encoding="utf-8")
    (qc / "metrics.py").write_text("VALUE = 1\n", encoding="utf-8")
    (qc / "holdout_guard.py").write_text("SECRET_HOLDOUT = True\n", encoding="utf-8")
    (fake_root / "tooling/ai-engines/quant_factory/__init__.py").write_text("", encoding="utf-8")
    (fake_root / "tooling/ai-engines/quant_factory/holdout_eval_2025_2026.py").write_text("BAD\n", encoding="utf-8")
    (cap / "__init__.py").write_text("CAP = 1\n", encoding="utf-8")
    (cap / "policy_kernel.py").write_text("KERNEL = 1\n", encoding="utf-8")
    (ssot / "firms_catalog.json").write_text('{"firms": []}\n', encoding="utf-8")
    (cals / "red_news_official_2018_2024_6ccy.json").write_text('{"events": []}\n', encoding="utf-8")
    (cals / "red_news_official_2025_2026.json").write_text('{"events": []}\n', encoding="utf-8")

    npz_path = derived / "frozen_9e_tapes_v2.npz"
    npz_path.write_bytes(b"FAKE_NPZ_DEV_BYTES_2018_2024")
    npz_sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    (derived / "frozen_9e_tapes_v2.json").write_text(
        json.dumps(
            {
                "schema": "naqex-frozen-tapes-v2",
                "npz_sha256": npz_sha,
                "ext_days": ["2018-01-02", "2024-12-31"],
            }
        ),
        encoding="utf-8",
    )

    # 1. Dry-run sync_dev_cache reports clean allowlist
    with patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()):
        dry = cr.sync_dev_cache(dry_run=True, root=fake_root)
    _check(dry["ok"] is True and dry["atomic_single_archive"] is True, f"Dry sync failed: {dry}")
    _check(dry["holdout_guard_excluded"] is True and dry["forbidden_files"] == 0, "Holdout guard must be excluded")
    _check(dry["frozen_9e_tapes_v2_verified"] is True, "frozen_9e_tapes_v2 must verify")
    _check("tooling/ai-engines/quant_core/holdout_guard.py" not in dry["files"], "holdout_guard leaked in dry_run")
    _check("tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json" in dry["files"], "6ccy missing")

    # 2. Pack 1 atomic tar.gz and run _REMOTE_CACHE_UNPACK_PY on simulated X13
    stage_out = tmp_path / "pack_out"
    packed = cr.build_dev_cache_archive(stage_out, root=fake_root)
    _check(packed["tar_path"].is_file(), "dev_cache_bundle.tar.gz must exist")
    with tarfile.open(packed["tar_path"], "r:gz") as tf:
        names = tf.getnames()
    _check("tooling/ai-engines/quant_core/holdout_guard.py" not in names, "holdout_guard.py in tar.gz!")
    _check("tooling/ai-engines/configs/calendars/red_news_official_2025_2026.json" not in names, "2025 cal in tar.gz!")
    _check("tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json" in names, "6ccy cal missing!")
    _check(".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.npz" in names, "frozen_9e_tapes_v2.npz missing!")

    fake_x13 = tmp_path / "fake_x13_cache"
    staging = fake_x13 / "cache_staging"
    staging.mkdir(parents=True)
    (staging / "dev_cache_bundle.tar.gz").write_bytes(packed["tar_path"].read_bytes())
    (staging / "dev_cache_manifest.sha256.json").write_bytes(packed["manifest_path"].read_bytes())
    unpacker = staging / "unpack_cache.py"
    unpacker.write_text(cr._REMOTE_CACHE_UNPACK_PY, encoding="utf-8", newline="\n")

    proc = subprocess.run(
        [sys.executable, str(unpacker), str(fake_x13)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    _check(proc.returncode == 0, f"Remote cache unpacker failed: {proc.stderr}")
    unpacked = json.loads(proc.stdout.strip())
    _check(unpacked["ok"] is True and unpacked["forbidden_members"] == 0, f"Unexpected unpack output: {unpacked}")
    _check(unpacked["frozen_9e_tapes_v2_verified"] is True, "Post-install tapes v2 SHA check must pass")
    _check(
        not (fake_x13 / "tooling/ai-engines/quant_core/holdout_guard.py").exists(),
        "holdout_guard must be absent on X13",
    )
    _check(
        (fake_x13 / "tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json").is_file(),
        "6ccy calendar must be unpacked",
    )
    cnt, sample = x13_probe.count_forbidden_files(fake_x13)
    _check(cnt == 0, f"X13 forbidden_files must be 0 after cache unpack, got {cnt}: {sample}")

    # 3. Negative mutations: missing/tampered npz_sha256, missing/empty ext_days, 2025 leak MUST fail-closed!
    for bad_meta, err_match in (
        ({"schema": "naqex-frozen-tapes-v2", "ext_days": ["2024-12-31"]}, "missing_or_invalid_npz_sha256"),
        (
            {"schema": "naqex-frozen-tapes-v2", "npz_sha256": None, "ext_days": ["2024-12-31"]},
            "missing_or_invalid_npz_sha256",
        ),
        (
            {"schema": "naqex-frozen-tapes-v2", "npz_sha256": "deadbeef", "ext_days": ["2024-12-31"]},
            "missing_or_invalid_npz_sha256",
        ),
        (
            {"schema": "naqex-frozen-tapes-v2", "npz_sha256": "0" * 64, "ext_days": ["2024-12-31"]},
            "npz_sha256_mismatch",
        ),
        ({"schema": "naqex-frozen-tapes-v2", "npz_sha256": npz_sha}, "missing_or_empty_ext_days"),
        ({"schema": "naqex-frozen-tapes-v2", "npz_sha256": npz_sha, "ext_days": []}, "missing_or_empty_ext_days"),
        (
            {
                "schema": "naqex-frozen-tapes-v2",
                "npz_sha256": npz_sha,
                "ext_days": ["2024-12-31", "2025-01-02"],
            },
            "holdout_date_leak",
        ),
    ):
        (derived / "frozen_9e_tapes_v2.json").write_text(json.dumps(bad_meta), encoding="utf-8")
        with pytest.raises(ValueError, match=err_match):
            cr.collect_dev_cache_files(root=fake_root)

    # Poisoned tar containing holdout_guard.py MUST be rejected by remote unpacker before extraction
    poison_x13 = tmp_path / "poison_x13"
    p_stage = poison_x13 / "cache_staging"
    p_stage.mkdir(parents=True)
    p_src = tmp_path / "bad_holdout.py"
    p_src.write_text("LEAK = 1\n", encoding="utf-8")
    p_tar = p_stage / "dev_cache_bundle.tar.gz"
    with tarfile.open(p_tar, "w:gz") as tf:
        tf.add(str(p_src), arcname="tooling/ai-engines/quant_core/holdout_guard.py")
    p_sha = hashlib.sha256(p_tar.read_bytes()).hexdigest()
    (p_stage / "dev_cache_manifest.sha256.json").write_text(
        json.dumps(
            {
                "archive_sha256": p_sha,
                "files": {
                    "tooling/ai-engines/quant_core/holdout_guard.py": {
                        "sha256": hashlib.sha256(p_src.read_bytes()).hexdigest(),
                        "bytes": p_src.stat().st_size,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    p_unpack = p_stage / "unpack_cache.py"
    p_unpack.write_text(cr._REMOTE_CACHE_UNPACK_PY, encoding="utf-8", newline="\n")
    proc_bad = subprocess.run(
        [sys.executable, str(p_unpack), str(poison_x13)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    _check(proc_bad.returncode != 0, "Poisoned tar with holdout_guard.py must fail closed")
    _check("HOLDOUT_OR_SECRET_AIRGAP_VIOLATION" in proc_bad.stderr, f"Expected airgap error: {proc_bad.stderr}")
    _check(not (poison_x13 / "tooling/ai-engines/quant_core/holdout_guard.py").exists(), "Must never extract!")


# ==============================================================================
# 5. HYPOTHESIS SPLIT (7/8 ON AIR-GAPPED X13 VS 8/8 ON PC DEV)
# ==============================================================================


def test_hypothesis_suite_skips_holdout_only_when_airgapped(tmp_path: Path) -> None:
    import importlib

    # On PC Dev (real repo), holdout_guard MUST be present & NOT skipped
    if str(AI_ENGINES / "tests") not in sys.path:
        sys.path.insert(0, str(AI_ENGINES / "tests"))
    hyp_mod = importlib.import_module("test_hypothesis_quant_invariants")
    _check(hyp_mod._HAS_HOLDOUT_GUARD is True, "On PC Dev, _HAS_HOLDOUT_GUARD must NEVER be False!")

    # Real unpacked air-gapped X13 cache (40/41 quant_core/*.py with holdout_guard.py physically absent!)
    # AND test file dispatched under jobs/<job_id>/src/ matching _REMOTE_RUNNER_PY bundle layout.
    fake_x13 = tmp_path / "real_airgap_x13"
    staging = fake_x13 / "cache_staging"
    packed = cr.build_dev_cache_archive(staging, root=cr.ROOT, include_tapes=False)
    _check(packed["tar_path"].is_file(), "Real air-gap cache archive must be created")
    unpacker = staging / "unpack_cache.py"
    unpacker.write_text(cr._REMOTE_CACHE_UNPACK_PY, encoding="utf-8", newline="\n")
    up = subprocess.run(
        [sys.executable, str(unpacker), str(fake_x13)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    _check(up.returncode == 0, f"Real air-gap cache unpack failed: {up.stderr}")
    _check(
        not (fake_x13 / "tooling/ai-engines/quant_core/holdout_guard.py").exists(),
        "holdout_guard.py must be physically absent in unpacked X13 cache",
    )

    bundle_src = fake_x13 / "jobs" / "hyp_bundle_v1" / "src"
    bundle_src.mkdir(parents=True)
    hyp_copy = bundle_src / "test_hypothesis_quant_invariants.py"
    hyp_copy.write_bytes((AI_ENGINES / "tests" / "test_hypothesis_quant_invariants.py").read_bytes())

    env = os.environ.copy()
    env["PYTHONPATH"] = str(fake_x13 / "tooling" / "ai-engines")
    env["HYPOTHESIS_MAX_EXAMPLES"] = "3"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-rs", str(hyp_copy)],
        cwd=str(bundle_src),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    _check(proc.returncode == 0, f"Real air-gapped X13 hypothesis run failed:\n{proc.stdout}\n{proc.stderr}")
    _check(
        "14 passed, 2 skipped" in proc.stdout,
        f"Expected exactly 14 passed, 2 skipped on real air-gapped X13:\n{proc.stdout}",
    )
