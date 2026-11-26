"""Negative-mutation & contract tests for Compute Router, X13 Probe, node_ctl, and quant_factory."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
OPS_CLOUD = AI_ENGINES / "ops_cloud"
for p in (AI_ENGINES, OPS_CLOUD):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import compute_router as cr  # noqa: E402
import node_ctl  # noqa: E402
import x13_probe  # noqa: E402


def _healthy_x13(**overrides) -> dict:
    base = {
        "ssh_alias": "naqex-x13",
        "transport": "LAN",
        "probe_ms": 380.0,
        "reachable": True,
        "ac_online": True,
        "ac_line_status": 1,
        "battery_status_code": 2,
        "battery_pct": 100,
        "cpu_util_pct": 6.5,
        "free_ram_gb": 11.2,
        "disk_free_gb": 120.5,
        "venv_ok": True,
        "active_job_lock": None,
        "ntp_offset_ms": -42.0,
        "forbidden_files": 0,
        "eligible": True,
        "ineligible_reasons": [],
    }
    base.update(overrides)
    return base


def _mode_a_gaming_dev(**overrides) -> dict:
    base = {
        "mode": "MODE_A_OWNER_ACTIVE",
        "idle_sec": 12.0,
        "in_overnight_window_ict": False,
        "gpu_util_pct": 68,
        "fullscreen_busy": True,
        "cpu_util_pct": 22.0,
        "free_ram_gb": 18.0,
        "ntp_offset_ms": -35.0,
        "ntp_ok": True,
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
        "cpu_util_pct": 5.0,
        "free_ram_gb": 22.0,
        "ntp_offset_ms": -25.0,
        "ntp_ok": True,
    }
    base.update(overrides)
    return base


def test_x13_on_battery_discharging_rejected_and_silent_fallback():
    x13_bat = _healthy_x13(ac_online=False, ac_line_status=0, battery_status_code=1)
    dec = cr.decide_route(_mode_a_gaming_dev(), x13_bat, est_minutes=25.0, ram_gb=4.0)
    assert dec["target"] == "DEV_PC_ONLY"
    assert dec["fallback_used"] is True
    assert "BatteryStatus=1" in (dec["fallback_reason"] or "")
    assert dec["dev_pc_cores"] == 2
    assert dec["dev_pc_priority"] == "BELOW_NORMAL"
    assert dec["dev_pc_gpu_allowed"] is False

    # Even if ac_online claims True, BatteryStatus == 1 MUST still fail-closed!
    x13_conflict = _healthy_x13(ac_online=True, ac_line_status=1, battery_status_code=1)
    ok, reasons = cr.evaluate_x13_eligibility(x13_conflict)
    assert ok is False
    assert any("BatteryStatus=1" in r for r in reasons)


def test_x13_unreachable_triggers_silent_fallback():
    x13_down = {
        "ssh_alias": "naqex-x13",
        "transport": "NONE",
        "probe_ms": None,
        "reachable": False,
        "eligible": False,
        "ineligible_reasons": ["x13_ssh_unreachable(naqex-x13-ts)"],
    }
    dec = cr.decide_route(_mode_b_idle_dev(), x13_down, est_minutes=30.0, shardable=True)
    assert dec["target"] == "DEV_PC_ONLY"
    assert dec["fallback_used"] is True
    assert "unreachable" in (dec["fallback_reason"] or "")
    assert dec["dev_pc_cores"] == 5
    assert dec["dev_pc_priority"] == "NORMAL"
    assert dec["ask_owner_required"] is False


def test_x13_ntp_drift_ge_1000ms_rejected():
    for bad_ntp in (1000.0, 1450.5, -1001.2):
        ok, reasons = cr.evaluate_x13_eligibility(_healthy_x13(ntp_offset_ms=bad_ntp))
        assert ok is False
        assert any("ntp_drift_ge_1000ms" in r for r in reasons)

    dec = cr.decide_route(_mode_a_gaming_dev(), _healthy_x13(ntp_offset_ms=1350.0), est_minutes=20.0)
    assert dec["target"] == "DEV_PC_ONLY"
    assert dec["fallback_used"] is True
    assert "ntp_drift_ge_1000ms" in (dec["fallback_reason"] or "")


def test_x13_forbidden_files_gt_0_rejected():
    ok, reasons = cr.evaluate_x13_eligibility(_healthy_x13(forbidden_files=1))
    assert ok is False
    assert any("forbidden_files" in r for r in reasons)

    dec = cr.decide_route(_mode_a_gaming_dev(), _healthy_x13(forbidden_files=2), est_minutes=20.0)
    assert dec["target"] == "DEV_PC_ONLY"
    assert dec["fallback_used"] is True
    assert "forbidden_files" in (dec["fallback_reason"] or "")


def test_mode_a_gaming_cap_vs_mode_b_60_40_split():
    # Mode A gaming + X13 healthy -> offloads 100% to X13 (0 cores on PC Dev, 0% GPU)
    dec_offload = cr.decide_route(_mode_a_gaming_dev(), _healthy_x13(), est_minutes=25.0)
    assert dec_offload["target"] == "X13_ONLY"
    assert dec_offload["dev_pc_cores"] == 0
    assert dec_offload["x13_threads"] == 7
    assert dec_offload["dev_pc_gpu_allowed"] is False
    assert dec_offload["shard_split_pct"] == {"dev_pc": 0, "x13_worker": 100}

    # Mode A gaming local fallback -> capped at 2 cores BELOW_NORMAL 0% GPU
    dec_game_local = cr.decide_route(_mode_a_gaming_dev(), _healthy_x13(reachable=False), est_minutes=25.0)
    assert dec_game_local["target"] == "DEV_PC_ONLY"
    assert dec_game_local["dev_pc_cores"] == 2
    assert dec_game_local["dev_pc_priority"] == "BELOW_NORMAL"
    assert dec_game_local["dev_pc_gpu_allowed"] is False

    # Mode A desktop (non-gaming, gpu <= 25%, not fullscreen) local -> 3 cores BELOW_NORMAL 0% GPU
    dev_office = _mode_a_gaming_dev(gpu_util_pct=8, fullscreen_busy=False)
    dec_office = cr.decide_route(dev_office, _healthy_x13(reachable=False), est_minutes=25.0)
    assert dec_office["dev_pc_cores"] == 3
    assert dec_office["dev_pc_priority"] == "BELOW_NORMAL"
    assert dec_office["dev_pc_gpu_allowed"] is False

    # Mode B idle/overnight + shardable >= 15m + X13 healthy -> 5 cores NORMAL + 60/40 10 micro-shards
    dec_par = cr.decide_route(_mode_b_idle_dev(), _healthy_x13(), est_minutes=30.0, shardable=True, shards=10)
    assert dec_par["target"] == "PARALLEL_60_40"
    assert dec_par["dev_pc_cores"] == 5
    assert dec_par["dev_pc_priority"] == "NORMAL"
    assert dec_par["x13_threads"] == 7
    assert dec_par["shard_split_pct"] == {"dev_pc": 60, "x13_worker": 40}
    assert dec_par["micro_shards"] == {"total": 10, "dev_pc": 6, "x13_worker": 4}


def test_manifest_sha_mismatch_and_traversal_rejected(tmp_path: Path):
    res_dir = tmp_path / "job_ok"
    res_dir.mkdir()
    data_file = res_dir / "summary.json"
    data_file.write_text('{"sharpe": 1.85}\n', encoding="utf-8")
    cr.write_result_manifest(res_dir, job_id="smoke_v1", host_label="X13_WORKER")

    ok = cr.verify_result_manifest(res_dir)
    assert ok["ok"] is True
    assert ok["status"] == "VERIFIED_PASS"
    assert ok["files_verified"] == 1

    # Tamper 1 byte -> MUST fail-closed
    data_file.write_text('{"sharpe": 1.86}\n', encoding="utf-8")
    bad = cr.verify_result_manifest(res_dir)
    assert bad["ok"] is False
    assert bad["status"] == "FAILED_INTEGRITY"
    assert any("sha256 mismatch" in e for e in bad["errors"])

    # Path traversal inside manifest -> MUST fail-closed
    mpath = res_dir / "manifest.sha256.json"
    mdata = json.loads(mpath.read_text(encoding="utf-8"))
    mdata["files"]["../escape.txt"] = {"sha256": "0" * 64, "bytes": 1}
    mpath.write_text(json.dumps(mdata), encoding="utf-8")
    trav = cr.verify_result_manifest(res_dir)
    assert trav["ok"] is False
    assert any("unsafe relative path" in e for e in trav["errors"])


def test_holdout_airgap_vps_isolation_and_anti_pid_reuse(tmp_path: Path):
    # Static OPSEC & read-only invariants
    assert cr.ORDER_SEND_CAPABLE is False
    assert cr.ORDER_SEND_COUNT == 0
    assert x13_probe.ORDER_SEND_CAPABLE is False
    assert x13_probe.ORDER_SEND_COUNT == 0

    # VPS compute strictly blocked
    dec_vps = cr.decide_route(_mode_b_idle_dev(), _healthy_x13(), est_minutes=10.0, touches_vps=True)
    assert dec_vps["target"] == "BLOCKED_NEEDS_APPROVAL"
    assert dec_vps["autonomy_tier"] == "TIER_3_ASK_OWNER"
    with pytest.raises(ValueError, match="Invalid or forbidden"):
        cr._validate_host("naqex-node1")

    # Holdout air-gap blocks X13 paths & pins to PC Dev
    for bad in ("holdout_eval_2025_2026.py", "data/2025/m1.parquet", "accounts.dat", "private_vault/x.json"):
        with pytest.raises(ValueError, match="AIRGAP_VIOLATION"):
            cr.assert_dev_only_path(bad)
    dec_hold = cr.decide_route(_mode_a_gaming_dev(), _healthy_x13(), est_minutes=20.0, touches_holdout=True)
    assert dec_hold["target"] == "DEV_PC_ONLY"
    assert dec_hold["x13_threads"] == 0

    # Anti-PID-reuse verification on active_job.lock
    lock_file = tmp_path / "active_job.lock"
    py_exe = r"C:\NaqexResearch\.venv\Scripts\python.exe"
    lock_file.write_text(
        json.dumps({"job_id": "job_a", "pid": 4242, "created_at": "2026-11-27T01:00:00Z", "executable": py_exe}),
        encoding="utf-8",
    )
    # Matching PID + CreationDate -> active lock
    alive = x13_probe.inspect_active_lock(
        lock_file,
        process_inspector=lambda pid: {"pid": pid, "createdAt": "2026-11-27T01:00:00Z", "executable": py_exe},
    )
    assert alive is not None and alive["job_id"] == "job_a"
    # Reused PID with different CreationDate -> stale (None)
    reused = x13_probe.inspect_active_lock(
        lock_file,
        process_inspector=lambda pid: {
            "pid": pid, "createdAt": "2026-11-27T02:30:00Z", "executable": r"C:\Windows\System32\svchost.exe"
        },
    )
    assert reused is None
    # Dead PID -> stale (None)
    assert x13_probe.inspect_active_lock(lock_file, process_inspector=lambda _pid: None) is None

    # Forbidden file scanner catches holdout / 2025 / accounts.dat
    (tmp_path / "ok_2024.json").write_text("{}", encoding="utf-8")
    (tmp_path / "holdout_leak.parquet").write_text("x", encoding="utf-8")
    (tmp_path / "accounts.dat").write_text("x", encoding="utf-8")
    cnt, sample = x13_probe.count_forbidden_files(tmp_path)
    assert cnt == 2
    assert set(sample) == {"holdout_leak.parquet", "accounts.dat"}


def test_node_ctl_single_handshake_and_rc255_only_fallback():
    calls: list[str] = []

    def fake_ok(cmd, **_kw):
        calls.append(cmd[5])

        class _R:
            returncode = 0
            stdout = json.dumps({"ok": True, "order_send_count": 0})
            stderr = ""

        return _R()

    with patch.object(node_ctl.subprocess, "run", side_effect=fake_ok):
        res = node_ctl.run_remote_probe("status")
    assert res["_ssh_host"] == "naqex-node1"
    # Eliminated double SSH handshake: exactly ONE ssh call on primary LAN success!
    assert calls == ["naqex-node1"]

    # Non-255 remote error must NOT silently retry on -ts
    calls.clear()

    def fake_script_err(cmd, **_kw):
        calls.append(cmd[5])

        class _R:
            returncode = 1
            stdout = ""
            stderr = "script traceback"

        return _R()

    with patch.object(node_ctl.subprocess, "run", side_effect=fake_script_err):
        with pytest.raises(RuntimeError, match="rc=1"):
            node_ctl.run_remote_probe("status")
    assert calls == ["naqex-node1"]

    # Exit code 255 falls back to naqex-node1-ts in 2 total calls (no echo OK probe)
    calls.clear()

    def fake_255_then_ok(cmd, **_kw):
        host = cmd[5]
        calls.append(host)

        class _R:
            returncode = 255 if host == "naqex-node1" else 0
            stdout = "" if returncode == 255 else json.dumps({"ok": True, "order_send_count": 0})
            stderr = "timeout" if returncode == 255 else ""

        return _R()

    with patch.object(node_ctl.subprocess, "run", side_effect=fake_255_then_ok):
        res2 = node_ctl.run_remote_probe("status")
    assert res2["_ssh_host"] == "naqex-node1-ts"
    assert calls == ["naqex-node1", "naqex-node1-ts"]


def test_eval_pipeline_normaldist_parity_and_data_store_binding_and_calendars(tmp_path: Path):
    from quant_factory.data_store import compute_tapes_binding, load_red_news_calendar
    from quant_factory.eval_pipeline import _STD_NORM
    from scipy.stats import norm

    # Parity < 1e-15 between statistics.NormalDist and scipy.stats.norm
    for x in (-4.0, -2.5, -1.0, 0.0, 0.5, 1.96, 3.5):
        assert abs(_STD_NORM.cdf(x) - float(norm.cdf(x))) < 1e-15
    for m in (2, 5, 13, 40, 200, 1000):
        for p in (1.0 - 1.0 / m, 1.0 - 1.0 / (m * math.e)):
            assert abs(_STD_NORM.inv_cdf(p) - float(norm.ppf(p))) < 1e-15

    # Builder-hashed compute_tapes_binding invalidates immediately when builder source changes
    bdir = tmp_path / "builders"
    bdir.mkdir()
    for fname in (
        "pass24_mtf_new_archetypes.py",
        "pass27_portfolio_m1_phase_audit.py",
        "pass28_final_discovery_rednews_frontier.py",
        "whitebox_discovery.py",
    ):
        (bdir / fname).write_text("v1\n", encoding="utf-8")
    b1, stem1 = compute_tapes_binding("lockA", "regA", profile_mode="Swing", cache_dir=tmp_path, builders_dir=bdir)
    assert stem1 == "frozen_9e_tapes_v2"
    (bdir / "pass28_final_discovery_rednews_frontier.py").write_text("v2_lookahead_fixed\n", encoding="utf-8")
    b2, stem2 = compute_tapes_binding("lockA", "regA", profile_mode="Swing", cache_dir=tmp_path, builders_dir=bdir)
    assert stem2 == "frozen_9e_tapes_v2"
    assert b1 != b2

    # Both `events_by_day` AND flat `events` red-news calendar schemas load cleanly
    cal_1824 = load_red_news_calendar("red_news_official_2018_2024")
    assert sum(len(v) for v in cal_1824.values()) == 224
    cal_multi = load_red_news_calendar("red_news_official_2026_2027_multi_ccy")
    assert sum(len(v) for v in cal_multi.values()) >= 200
    assert any(ccy == "JPY" for evs in cal_multi.values() for _, ccy in evs)


def test_touches_holdout_blocked_in_dispatch_and_cli_exits_2(tmp_path: Path):
    marker = tmp_path / "executed.flag"
    sentinel = tmp_path / "holdout_sentinel.py"
    sentinel.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('RAN', encoding='utf-8')\n",
        encoding="utf-8",
    )
    with (
        patch.object(cr, "probe_dev_pc", return_value=_mode_b_idle_dev()),
        patch.object(cr, "probe_x13_worker", return_value=_healthy_x13()),
    ):
        res = cr.dispatch_job(
            "hold_block_v1",
            sentinel,
            est_minutes=5.0,
            touches_holdout=True,
            dry_run=False,
            dest_dir=tmp_path / "out",
        )
        assert res["ok"] is False
        assert res["decision"]["ask_owner_required"] is True
        assert res["decision"]["autonomy_tier"] == "TIER_3_ASK_OWNER"
        assert res.get("blocked_reason") == "TIER_3_ASK_OWNER_APPROVAL_REQUIRED"
        assert not marker.exists(), "Holdout script must NEVER execute without owner approval"

        rc_route = cr.main(["route", "--est-minutes", "5", "--touches-holdout"])
        assert rc_route == 2

        rc_disp = cr.main([
            "dispatch",
            "--job-id",
            "hold_block_cli",
            "--entry",
            str(sentinel),
            "--est-minutes",
            "5",
            "--touches-holdout",
            "--dest",
            str(tmp_path / "out_cli"),
        ])
        assert rc_disp == 2
        assert not marker.exists()


def test_poisoned_nan_inf_none_negative_inputs_fail_closed():
    poisoned_x13_cases = [
        {"cpu_util_pct": float("nan")},
        {"cpu_util_pct": None},
        {"cpu_util_pct": -1.0},
        {"free_ram_gb": float("nan")},
        {"free_ram_gb": None},
        {"disk_free_gb": float("nan")},
        {"disk_free_gb": None},
        {"ntp_offset_ms": float("nan")},
        {"ntp_offset_ms": float("inf")},
        {"venv_ok": None},
        {"venv_ok": False},
        {"forbidden_files": -1},
        {"forbidden_files": None},
        {"forbidden_files": True},
        {"ac_line_status": None},
        {"ac_line_status": True},
    ]
    for overrides in poisoned_x13_cases:
        ok, reasons = cr.evaluate_x13_eligibility(_healthy_x13(**overrides))
        assert ok is False, f"Poisoned X13 payload bypassed eligibility: {overrides}"
        assert reasons

    # probe_x13_worker must fail closed on missing venv_ok and explicit JSON null numerics
    class _NullJsonProc:
        returncode = 0
        stdout = json.dumps({
            "ac_online": True,
            "ac_line_status": 1,
            "battery_status_code": 2,
            "cpu_util_pct": None,
            "free_ram_gb": None,
            "disk_free_gb": None,
            "forbidden_files": 0,
            "ntp_offset_ms": None,
        })
        stderr = ""

    with patch.object(cr.subprocess, "run", return_value=_NullJsonProc()):
        probed = cr.probe_x13_worker(lan_only=True)
    assert probed["venv_ok"] is False
    assert probed["eligible"] is False
    assert probed["ineligible_reasons"]

    # decide_route must reject NaN / Inf / negative est_minutes and ram_gb
    for bad_est in (float("nan"), float("inf"), float("-inf"), -1.0):
        with pytest.raises(ValueError, match="Invalid est_minutes"):
            cr.decide_route(_mode_b_idle_dev(), _healthy_x13(), est_minutes=bad_est)
    for bad_ram in (float("nan"), float("inf"), -0.5):
        with pytest.raises(ValueError, match="Invalid ram_gb"):
            cr.decide_route(_mode_b_idle_dev(), _healthy_x13(), est_minutes=15.0, ram_gb=bad_ram)

    # strict_ntp_passed must fail closed when x13 ntp_offset_ms is None or NaN or >= 1000ms
    dev_ntp_ok = _mode_b_idle_dev(ntp_offset_ms=-20.0)
    assert cr._strict_ntp_passed(dev_ntp_ok, _healthy_x13(ntp_offset_ms=None)) is False
    assert cr._strict_ntp_passed(dev_ntp_ok, _healthy_x13(ntp_offset_ms=float("nan"))) is False
    assert cr._strict_ntp_passed(dev_ntp_ok, _healthy_x13(ntp_offset_ms=1200.0)) is False
    assert cr._strict_ntp_passed(dev_ntp_ok, _healthy_x13(ntp_offset_ms=-45.0)) is True


def test_remote_runner_streams_large_output_without_pipe_deadlock(tmp_path: Path):
    import subprocess

    # Build a Dev-only child script emitting >200KB stdout AND >200KB stderr (would deadlock PIPE+poll)
    child = tmp_path / "noisy_dev.py"
    child.write_text(
        "import sys\n"
        "sys.stdout.write('O' * 220000 + '\\n')\n"
        "sys.stderr.write('E' * 220000 + '\\n')\n",
        encoding="utf-8",
    )
    job_id = "pipe_test_v1"
    job_dir = tmp_path / "jobs" / job_id
    (tmp_path / "locks").mkdir(parents=True)
    cr.build_job_bundle(job_id, child, job_dir)

    # Point _REMOTE_RUNNER_PY's base path at tmp_path and stub AC=True for platform-independent test
    patched_runner = cr._REMOTE_RUNNER_PY.replace(
        'base = pathlib.Path(r"C:\\NaqexResearch")',
        f"base = pathlib.Path({str(tmp_path)!r})",
    ).replace(
        "return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))) and int(s.AC) == 1",
        "return True",
    )
    runner_py = job_dir / "run_job.py"
    runner_py.write_text(patched_runner, encoding="utf-8", newline="\n")

    proc = subprocess.run(
        [sys.executable, str(runner_py), job_id, "2"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    res_dir = tmp_path / "results" / job_id
    verify = cr.verify_result_manifest(res_dir)
    assert verify["ok"] is True
    assert (res_dir / "stdout.log").stat().st_size >= 220_000
    assert (res_dir / "stderr.log").stat().st_size >= 220_000
    assert not (tmp_path / "locks" / "active_job.lock").exists()
