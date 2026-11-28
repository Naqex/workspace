"""Offline contract tests for Wave 5 X13 Full-Performance Shard Dispatcher & 16-Sym NPZ Sync.

Hard invariants verified (0 bare asserts, safe under `python -O`, OrderSend=0, Holdout 2025+ SEALED):
  1. Owner Override policy: PC Dev strictly locked to MODE_A_OWNER_ACTIVE (2-3 cores BELOW_NORMAL 0x4000,
     0% GPU; force_mode_b=True HARD-REJECTED) + X13 FULL_PERFORMANCE (all cores, 75-85% share).
  2. Forbidden-token rejection (`2025`, `2026`, `holdout`, `private_vault`) in job_id, paths, & NPZ sync.
  3. Air-gap rejection of `holdout_guard`-importing modules & `research_council.py` in both
     `collect_dev_cache_files()` and `dispatch_wave5_shards()`.
  4. Silent fallback to PC Dev strictly in MODE_A_OWNER_ACTIVE (NEVER Mode B) when X13 is offline,
     on battery, missing a required package (e.g. `numba` or `duckdb`), or drops mid-flight.
  5. Incremental SHA-256 16-symbol zero-pickle `.npz` sync (`C:\\NaqexResearch\\wave5_m1_16sym_npz\\`),
     never bundled into `dev_cache_bundle.tar.gz`.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
OPS_CLOUD_DIR = AI_ENGINES_DIR / "ops_cloud"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ops_cloud import compute_router as cr  # noqa: E402
from quant_factory import wave5  # noqa: E402
from quant_factory.wave5 import x13_shard_dispatcher as w5d  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit guard immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _healthy_x13_full(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ssh_alias": "naqex-x13",
        "transport": "LAN",
        "probe_ms": 320.0,
        "reachable": True,
        "ac_online": True,
        "ac_line_status": 1,
        "battery_status_code": 2,
        "battery_pct": 100,
        "cpu_util_pct": 8.0,
        "free_ram_gb": 10.5,
        "disk_free_gb": 115.0,
        "venv_ok": True,
        "active_job_lock": None,
        "ntp_offset_ms": 28.0,
        "forbidden_files": 0,
        "eligible": True,
        "ineligible_reasons": [],
        "cpu_count_logical": 8,
        "python_version": "3.14.7",
        "packages": {
            "numpy": "2.5.5",
            "pyarrow": "26.0.1",
            "numba": "0.68.1",
            "scipy": "1.18.1",
            "duckdb": None,
        },
        "import_ok": {
            "numpy": True,
            "pyarrow": True,
            "numba": True,
            "scipy": True,
            "duckdb": "ERR:ModuleNotFoundError",
        },
    }
    base.update(overrides)
    return base


def _dev_pc_idle_sensor(**overrides: Any) -> dict[str, Any]:
    """Simulate a PC Dev sensor that would normally claim Mode B — Wave 5 MUST STILL enforce Mode A!"""
    base: dict[str, Any] = {
        "mode": "MODE_B_IDLE_OVERNIGHT",
        "idle_sec": 3600.0,
        "in_overnight_window_ict": True,
        "gpu_util_pct": 4,
        "fullscreen_busy": False,
        "cpu_util_pct": 5.0,
        "free_ram_gb": 20.0,
        "ntp_offset_ms": 15.0,
        "ntp_ok": True,
    }
    base.update(overrides)
    return base


def _dev_pc_gaming(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "mode": "MODE_A_OWNER_ACTIVE",
        "idle_sec": 2.0,
        "in_overnight_window_ict": False,
        "gpu_util_pct": 65,
        "fullscreen_busy": True,
        "cpu_util_pct": 25.0,
        "free_ram_gb": 16.0,
        "ntp_offset_ms": 18.0,
        "ntp_ok": True,
    }
    base.update(overrides)
    return base


def _make_worker_script(path: Path) -> Path:
    path.write_text(
        "import json, os, pathlib\n"
        "batch_file = pathlib.Path(os.environ['NAQEX_SHARD_BATCH_FILE'])\n"
        "batch = json.loads(batch_file.read_text(encoding='utf-8'))\n"
        "role = os.environ.get('NAQEX_WORKER_ROLE', 'UNKNOWN')\n"
        "threads = int(os.environ.get('NUMBA_NUM_THREADS', '0'))\n"
        "results = [\n"
        "    {'index': idx, 'shard_id': idx, 'worker_role': role, 'threads': threads}\n"
        "    for idx in batch['shard_indices']\n"
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


def _write_clean_npz(path: Path, *, max_ts: int = 1_735_682_000, holdout_rows: int = 0) -> Path:
    np.savez(
        path,
        times_sec=np.array([1_546_401_600, max_ts], dtype=np.int64),
        bid_ohlc=np.array([[1.1, 1.2, 1.0, 1.15], [1.15, 1.25, 1.1, 1.2]], dtype=np.float64),
        holdout_rows=np.int64(holdout_rows),
    )
    return path


def test_zero_bare_asserts_and_create_no_window_in_wave5_files() -> None:
    files = [
        AI_ENGINES_DIR / "quant_factory" / "wave5" / "__init__.py",
        AI_ENGINES_DIR / "quant_factory" / "wave5" / "x13_shard_dispatcher.py",
        AI_ENGINES_DIR / "tests" / "wave5" / "__init__.py",
        Path(__file__),
    ]
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(not asserts, f"Bare assert(s) found in {path.name} at lines {asserts}")

    # Verify EVERY subprocess.run/Popen call in compute_router.py & x13_shard_dispatcher.py sets creationflags
    for path in (
        OPS_CLOUD_DIR / "compute_router.py",
        AI_ENGINES_DIR / "quant_factory" / "wave5" / "x13_shard_dispatcher.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                    and node.func.attr in ("run", "Popen", "check_output", "check_call")
                ):
                    kw_names = {kw.arg for kw in node.keywords}
                    _check(
                        "creationflags" in kw_names,
                        f"Missing creationflags on subprocess.{node.func.attr} in {path.name}:{node.lineno}",
                    )

    _check(wave5.ORDER_SEND_CAPABLE is False and wave5.ORDER_SEND_COUNT == 0, "wave5 OrderSend invariant")
    _check(wave5.HOLDOUT_CUTOFF_DATE == "2024-12-31", "wave5 holdout cutoff date")


def test_owner_override_mode_a_pc_dev_and_x13_full_performance() -> None:
    # Even when PC Dev sensors look idle overnight (Mode B), Wave 5 MUST lock PC Dev to MODE_A_OWNER_ACTIVE!
    dec_desktop = w5d.decide_wave5_route(
        _dev_pc_idle_sensor(),
        _healthy_x13_full(cpu_count_logical=8),
        shard_count=16,
        x13_share_pct=80,
        required_packages=("numpy", "pyarrow", "numba"),
    )
    _check(dec_desktop["target"] == "WAVE5_X13_FULL_PLUS_DEV_MODE_A", f"Unexpected target: {dec_desktop}")
    _check(dec_desktop["dev_pc_mode"] == "MODE_A_OWNER_ACTIVE", "PC Dev must stay MODE_A_OWNER_ACTIVE")
    _check(dec_desktop["dev_pc_cores"] == 3, f"Desktop Mode A cap must be 3 cores: {dec_desktop}")
    _check(dec_desktop["dev_pc_priority"] == "BELOW_NORMAL", "PC Dev must run BELOW_NORMAL")
    _check(dec_desktop["dev_pc_priority_class"] == 0x4000, "PC Dev priority class must be 0x4000")
    _check(dec_desktop["dev_pc_gpu_allowed"] is False, "PC Dev GPU must be 0%")
    _check(dec_desktop["x13_policy"] == "FULL_PERFORMANCE", "X13 must run FULL_PERFORMANCE")
    _check(dec_desktop["x13_threads"] == 8, f"X13 must use all 8 logical cores: {dec_desktop}")
    _check(dec_desktop["shard_split_pct"] == {"dev_pc": 20, "x13_worker": 80}, "Expected 20/80 split")
    _check(dec_desktop["micro_shards"] == {"total": 16, "dev_pc": 3, "x13_worker": 13}, "Expected 3/13 of 16")

    # Gaming / GPU > 25% caps PC Dev at 2 cores BELOW_NORMAL, while X13 runs 85% share at full 8 cores
    dec_game = w5d.decide_wave5_route(
        _dev_pc_gaming(),
        _healthy_x13_full(cpu_count_logical=8),
        shard_count=20,
        x13_share_pct=85,
    )
    _check(dec_game["dev_pc_cores"] == 2, f"Gaming Mode A cap must be 2 cores: {dec_game}")
    _check(dec_game["micro_shards"] == {"total": 20, "dev_pc": 3, "x13_worker": 17}, "Expected 3/17 of 20")

    # force_mode_b=True MUST raise OWNER_OVERRIDE_VIOLATION fail-closed!
    with pytest.raises(ValueError, match="OWNER_OVERRIDE_VIOLATION"):
        w5d.decide_wave5_route(_dev_pc_idle_sensor(), _healthy_x13_full(), force_mode_b=True)

    # Share outside [75, 85] MUST be rejected fail-closed!
    with pytest.raises(ValueError, match="x13_share_pct"):
        w5d.decide_wave5_route(_dev_pc_idle_sensor(), _healthy_x13_full(), x13_share_pct=40)

    # Tier-3 blocks (VPS, GPU, Holdout) stay fail-closed
    dec_vps = w5d.decide_wave5_route(_dev_pc_idle_sensor(), _healthy_x13_full(), touches_vps=True)
    _check(dec_vps["target"] == "BLOCKED_NEEDS_APPROVAL" and dec_vps["ask_owner_required"] is True, "VPS blocked")
    dec_gpu = w5d.decide_wave5_route(_dev_pc_idle_sensor(), _healthy_x13_full(), needs_gpu=True)
    _check(dec_gpu["target"] == "BLOCKED_NEEDS_APPROVAL" and dec_gpu["ask_owner_required"] is True, "GPU blocked")
    dec_ho = w5d.decide_wave5_route(_dev_pc_idle_sensor(), _healthy_x13_full(), touches_holdout=True)
    _check(dec_ho["target"] == "DEV_PC_ONLY" and dec_ho["ask_owner_required"] is True and dec_ho["x13_threads"] == 0,
           "Holdout blocked from X13")


def test_forbidden_token_rejection_in_job_id_paths_and_npz(tmp_path: Path) -> None:
    _check(w5d.normalize_wave5_job_id("alpha01") == "w5_shard_alpha01", "Prefix normalization failed")
    _check(w5d.normalize_wave5_job_id("w5_shard_smoke") == "w5_shard_smoke", "Existing prefix preserved")

    for bad_id in (
        "eval_2025",
        "w5_shard_2026_run",
        "holdout_check",
        "private_vault_sync",
        "accounts.dat",
    ):
        with pytest.raises(ValueError, match="forbidden air-gap token"):
            w5d.normalize_wave5_job_id(bad_id)

    for bad_path in (
        "C:/NaqexResearch/2025_data/x.npz",
        "wave5_2026_m1/EURUSD.npz",
        "holdout_bundle/file.py",
        "private_vault/secret.json",
    ):
        with pytest.raises(ValueError, match="HOLDOUT_OR_SECRET_AIRGAP_VIOLATION"):
            cr.assert_dev_only_path(bad_path)

    # NPZ sync plan rejects stray 2025 filename AND rejects 2025 timestamp inside an otherwise clean filename!
    npz_dir = tmp_path / "npz_clean"
    npz_dir.mkdir()
    _write_clean_npz(npz_dir / "EURGBP-M1-FTMO_BID_PLUS_SPREAD.npz")
    plan = cr.collect_wave5_16sym_npz_sync_plan(npz_dir=npz_dir, verify_contents=True)
    _check(plan["total_files"] == 1 and plan["zero_pickle_verified"] is True, f"Clean plan failed: {plan}")

    bad_ts_dir = tmp_path / "npz_bad_ts"
    bad_ts_dir.mkdir()
    _write_clean_npz(bad_ts_dir / "EURGBP-M1-FTMO_BID_PLUS_SPREAD.npz", max_ts=1_735_689_600)
    with pytest.raises(ValueError, match="HOLDOUT_OR_SECRET_AIRGAP_VIOLATION"):
        cr.collect_wave5_16sym_npz_sync_plan(npz_dir=bad_ts_dir, verify_contents=True)

    bad_name_dir = tmp_path / "npz_bad_name"
    bad_name_dir.mkdir()
    _write_clean_npz(bad_name_dir / "EURGBP-M1-2025.npz")
    with pytest.raises(ValueError, match="HOLDOUT_OR_SECRET_AIRGAP_VIOLATION"):
        cr.collect_wave5_16sym_npz_sync_plan(npz_dir=bad_name_dir, verify_contents=True)


def test_airgap_rejection_of_holdout_guard_importing_modules(tmp_path: Path) -> None:
    good_py = tmp_path / "clean_shard.py"
    good_py.write_text("import numpy as np\nX = 1\n", encoding="utf-8")
    _check(cr.module_imports_holdout_guard(good_py) is False, "Clean module flagged as holdout_guard")
    w5d.assert_wave5_x13_safe_module(good_py)

    for idx, bad_src in enumerate(
        (
            "from quant_core.holdout_guard import assert_dev_only\n",
            "import quant_core.holdout_guard\n",
            "from quant_core import holdout_guard\n",
            "import importlib\nimportlib.import_module('quant_core.holdout_guard')\n",
        )
    ):
        bad_py = tmp_path / f"bad_mod_{idx}.py"
        bad_py.write_text(bad_src, encoding="utf-8")
        _check(cr.module_imports_holdout_guard(bad_py) is True, f"Missed holdout_guard import in case {idx}")
        with pytest.raises(ValueError, match="HOLDOUT_OR_SECRET_AIRGAP_VIOLATION"):
            w5d.assert_wave5_x13_safe_module(bad_py)
        with pytest.raises(ValueError, match="HOLDOUT_OR_SECRET_AIRGAP_VIOLATION"):
            w5d.dispatch_wave5_shards("w5_shard_badmod", bad_py, 2, dry_run=True)

    rc_py = tmp_path / "research_council.py"
    rc_py.write_text("X = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="HOLDOUT_OR_SECRET_AIRGAP_VIOLATION"):
        w5d.assert_wave5_x13_safe_module(rc_py)


def test_collect_dev_cache_files_includes_wave5_and_4_wave4_helpers_only() -> None:
    collected = cr.collect_dev_cache_files(root=REPO_ROOT, include_tapes=False)
    arcs = {arc for arc, _ in collected["entries"]}

    _check(collected["counts"]["quant_core"] == 40, f"quant_core count must stay 40: {collected['counts']}")
    _check(collected["counts"]["wave4_helpers"] == 4, f"Expected exact 4 wave4 helpers: {collected['counts']}")
    _check(collected["counts"]["wave5_code"] >= 2, f"Expected wave5/*.py included: {collected['counts']}")

    # Exactly the 4 allowed wave4 helpers MUST be present
    expected_w4 = {
        "tooling/ai-engines/quant_factory/wave4/__init__.py",
        "tooling/ai-engines/quant_factory/wave4/ftmo_m1_exporter.py",
        "tooling/ai-engines/quant_factory/wave4/same_feed_mt5_parity.py",
        "tooling/ai-engines/quant_factory/wave4/ml_features_24.py",
    }
    actual_w4 = {a for a in arcs if a.startswith("tooling/ai-engines/quant_factory/wave4/")}
    _check(actual_w4 == expected_w4, f"wave4 allowlist drift: {actual_w4}")

    # wave5/*.py MUST be present
    _check("tooling/ai-engines/quant_factory/wave5/__init__.py" in arcs, "wave5/__init__.py missing")
    _check("tooling/ai-engines/quant_factory/wave5/x13_shard_dispatcher.py" in arcs, "x13_shard_dispatcher.py missing")

    # research_council.py + all 10 holdout_guard wave4 files + 16-sym NPZ MUST NEVER be bundled
    _check("tooling/ai-engines/quant_factory/research_council.py" not in arcs, "research_council.py leaked!")
    for forbidden_w4 in (
        "cme_intraday_prop_feasibility.py",
        "frontier_sleeves.py",
        "harvest_free_trial_forensics.py",
        "multi_source_m1_harvester.py",
        "ownbook_shadow_ops.py",
        "pareto_multi_account.py",
        "run_frontier_blind_cluster_b.py",
        "run_pareto_81cases.py",
        "wave4_m4_exec_runner.py",
        "wave4_master_council.py",
    ):
        _check(f"tooling/ai-engines/quant_factory/wave4/{forbidden_w4}" not in arcs, f"{forbidden_w4} leaked!")
    _check(not any("wave4_16sym_sealed" in a for a in arcs), "16-sym NPZ leaked into dev_cache_bundle!")


def test_silent_fallback_to_pc_dev_mode_a_on_offline_battery_missing_pkg_and_midflight(tmp_path: Path) -> None:
    worker = _make_worker_script(tmp_path / "w5_worker.py")

    # 1. Offline X13 -> fallback to PC Dev strictly MODE_A_OWNER_ACTIVE (3 cores desktop, NEVER 5 cores Mode B)
    x13_offline = _healthy_x13_full(
        reachable=False,
        eligible=False,
        ineligible_reasons=["x13_ssh_unreachable(naqex-x13)"],
    )
    dec_off = w5d.decide_wave5_route(_dev_pc_idle_sensor(), x13_offline, shard_count=10)
    _check(dec_off["target"] == "DEV_PC_MODE_A_FALLBACK" and dec_off["fallback_used"] is True, "Offline fallback")
    _check(dec_off["dev_pc_mode"] == "MODE_A_OWNER_ACTIVE" and dec_off["dev_pc_cores"] == 3, "Must stay Mode A (3)")
    _check(dec_off["dev_pc_priority"] == "BELOW_NORMAL" and dec_off["dev_pc_gpu_allowed"] is False, "BELOW_NORMAL 0GPU")

    # 2. Battery discharging X13 -> fallback to PC Dev MODE_A_OWNER_ACTIVE (2 cores gaming)
    x13_bat = _healthy_x13_full(ac_online=False, ac_line_status=0, battery_status_code=1)
    dec_bat = w5d.decide_wave5_route(_dev_pc_gaming(), x13_bat, shard_count=10)
    _check(dec_bat["target"] == "DEV_PC_MODE_A_FALLBACK" and dec_bat["dev_pc_cores"] == 2, "Battery fallback Mode A")
    _check("BatteryStatus=1" in (dec_bat["fallback_reason"] or ""), "Must record BatteryStatus=1 reason")

    # 3. Missing required package (`duckdb`) on X13 -> fallback to PC Dev MODE_A_OWNER_ACTIVE
    dec_pkg = w5d.decide_wave5_route(
        _dev_pc_idle_sensor(),
        _healthy_x13_full(),
        shard_count=10,
        required_packages=("numpy", "duckdb"),
    )
    _check(dec_pkg["target"] == "DEV_PC_MODE_A_FALLBACK" and dec_pkg["fallback_used"] is True, "Missing pkg fallback")
    _check("x13_missing_package(duckdb)" in (dec_pkg["fallback_reason"] or ""), f"Bad reason: {dec_pkg}")
    _check(dec_pkg["dev_pc_cores"] == 3 and dec_pkg["dev_pc_priority"] == "BELOW_NORMAL", "Mode A on missing pkg")

    # 4. End-to-end dispatch mid-flight X13 drop -> completes locally strictly in Mode A (2 cores BELOW_NORMAL)
    local_calls: list[dict[str, Any]] = []
    real_local = cr._run_local_dev_job

    def _track_local(jid: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        local_calls.append({"job_id": jid, "cores": kwargs["cores"], "priority": kwargs["priority"]})
        return real_local(jid, *args, **kwargs)

    out_dir = tmp_path / "w5_midflight"
    with (
        patch.object(cr, "probe_dev_pc", return_value=_dev_pc_gaming()),
        patch.object(w5d, "probe_x13_full_capabilities", return_value=_healthy_x13_full()),
        patch.object(cr, "_run_local_dev_job", side_effect=_track_local),
        patch.object(cr, "_execute_x13_bundle", side_effect=RuntimeError("x13_ac_unplugged_during_run")),
    ):
        receipt = w5d.dispatch_wave5_shards(
            "midflight_smoke",
            worker,
            10,
            x13_share_pct=80,
            dest_dir=out_dir,
            lease_max_wait_sec=0.0,
        )

    _check(receipt["ok"] is True, f"Mid-flight fallback must succeed: {receipt}")
    _check(receipt["job_id"] == "w5_shard_midflight_smoke", "Must normalize job_id with w5_shard_ prefix")
    _check(receipt["decision"]["fallback_used"] is True, "Must record fallback_used=True")
    _check(len(local_calls) == 2, f"Expected primary + fallback sequential Mode A slices: {local_calls}")
    for c in local_calls:
        _check(c["cores"] == 2 and c["priority"] == "BELOW_NORMAL", f"Must enforce Mode A 2c BELOW_NORMAL: {c}")
    merged = json.loads((out_dir / "merged_results.json").read_text(encoding="utf-8"))
    _check([s["index"] for s in merged["shards"]] == list(range(10)), "All 10 shards must merge cleanly")


def test_sync_wave5_16sym_npz_incremental_sha_skip_and_battery_fallback(tmp_path: Path) -> None:
    npz_dir = tmp_path / "npz"
    npz_dir.mkdir()
    _write_clean_npz(npz_dir / "AUDJPY-M1-FTMO_BID_PLUS_SPREAD.npz")
    _write_clean_npz(npz_dir / "USOIL-M1-QDM_PROVIDER_DEFAULT_SINGLE_SIDE.npz")

    remote_store: dict[str, str] = {}
    uploads: list[str] = []

    def _query(_alias: str) -> dict[str, str]:
        return dict(remote_store)

    def _upload(_alias: str, local_p: Path, rel_posix: str) -> None:
        uploads.append(rel_posix)
        remote_store[rel_posix] = hashlib.sha256(local_p.read_bytes()).hexdigest()

    # Pass 1: uploads both files to wave5_m1_16sym_npz/ and verifies remote SHA-256
    with patch.object(cr, "probe_x13_worker", return_value=_healthy_x13_full()):
        r1 = cr.sync_wave5_16sym_npz_incremental(
            npz_dir=npz_dir,
            query_remote_hashes_fn=_query,
            upload_fn=_upload,
        )
    _check(r1["ok"] is True and r1["status"] == "SYNCED_VERIFIED", f"Pass 1 failed: {r1}")
    _check(r1["verified_count"] == 2 and len(r1["uploaded_files"]) == 2, f"Expected 2 uploads: {r1}")
    _check(all(u.startswith("wave5_m1_16sym_npz/") for u in r1["uploaded_files"]), "Wrong remote subdir")

    # Pass 2: identical SHAs -> 0 bytes uploaded!
    uploads.clear()
    with patch.object(cr, "probe_x13_worker", return_value=_healthy_x13_full()):
        r2 = cr.sync_wave5_16sym_npz_incremental(
            npz_dir=npz_dir,
            query_remote_hashes_fn=_query,
            upload_fn=_upload,
        )
    _check(r2["ok"] is True and r2["status"] == "ALREADY_UP_TO_DATE", f"Pass 2 failed: {r2}")
    _check(r2["bytes_uploaded"] == 0 and uploads == [] and r2["verified_count"] == 2, "Must skip identical files")

    # Pass 3: X13 on battery -> silent fallback (never uploads on battery)
    with patch.object(cr, "probe_x13_worker", return_value=_healthy_x13_full(ac_online=False, battery_status_code=1)):
        r3 = cr.sync_wave5_16sym_npz_incremental(npz_dir=npz_dir)
    _check(r3["ok"] is True and r3["fallback_used"] is True and r3["status"] == "FALLBACK_DEV_PC_LOCAL", f"Bat: {r3}")


@pytest.mark.local_cache
def test_real_16sym_sealed_npz_plan_zero_pickle_and_pre2025() -> None:
    plan = cr.collect_wave5_16sym_npz_sync_plan(root=REPO_ROOT, verify_contents=True)
    _check(plan["total_files"] == 16, f"Expected 16 sealed NPZ files, got {plan['total_files']}")
    _check(plan["zero_pickle_verified"] is True, "Zero-pickle verification must be True")
    _check(plan["total_bytes"] > 400_000_000, f"Unexpected total_bytes: {plan['total_bytes']}")
    for entry in plan["entries"]:
        _check(entry["max_ts"] < cr.DEV_CUTOFF_SEC, f"Holdout leak in {entry['filename']}: {entry['max_ts']}")
        _check(entry["rel_path"].startswith("wave5_m1_16sym_npz/"), f"Bad rel_path: {entry['rel_path']}")
        cr.assert_dev_only_path(entry["rel_path"])
