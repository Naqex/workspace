"""Wave 0B (Total Offensive #4) Regression Tests: Zero-Popup AST Guard, RT2 P1-01/P1-02 & RC-6 Hygiene.

Verifies strictly on offline synthetic pre-2025 fixtures (and optional read-only Dev cache checks):
  1. AST zero-popup verifier: 0 `subprocess.run/Popen/call/check_call/check_output` calls missing
     `creationflags` across ALL `.py` files under `tooling/automation/` AND `tooling/ai-engines/ops_cloud/`,
     plus runtime `creationflags` propagation on all 7 patched modules.
  2. RT2 P1-01: `research_council.py` uses `quant_core.metrics.deflated_sharpe_ratio_empirical`
     (no legacy `1/(T-1)` proxy), matches DuckDB empirical DSR, fails closed under `strict_gates=True`
     when empirical variance is absent for `M > 1`, and blocks `dsr_empirical < 0.50` from `TIER_1`.
  3. RT2 P1-02: Pair symbols `'SYM_A/SYM_B'` (e.g. `GER40/UK100`, `CADJPY/CHFJPY`) are split and
     resolved to real aligned spread OHLC bars + spread daily returns for Random-Entry MC and
     Matched-Hold Timing Permutation, AND `sign_flip_fallback` is strictly blocked from `TIER_1`.
  4. RC-6: `frozen_9e_tapes_v2` loaders merge engine tape days into `ext_days` (preserving `2024-10-15`
     E4/E5 rows while maintaining strict `< 2025-01-01` Holdout lock), AND `apply_shield_b2_b3_guards`
     (plus parity siblings) syncs/zeroes `gross_R` on `NEWS_PRE_FLATTEN` rows instead of leaving stale values.

All checks use `_check(...)` so tests remain 100% effective under BOTH `python` AND `python -O`.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES.parents[1]
OPS_CLOUD = AI_ENGINES / "ops_cloud"
NODE_SCRIPTS = OPS_CLOUD / "node_scripts"
HEROKU_DEADMAN = OPS_CLOUD / "heroku_deadman"

for _p in (REPO_ROOT, AI_ENGINES, OPS_CLOUD, NODE_SCRIPTS, HEROKU_DEADMAN):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from experiments import flashcrash_pareto_study as fcp  # noqa: E402
from quant_core.metrics import deflated_sharpe_ratio_empirical  # noqa: E402
from quant_factory import data_store  # noqa: E402
from quant_factory.capital_optimizer import replay_cache  # noqa: E402
from quant_factory.eval_pipeline import deflated_sharpe_ratio as legacy_proxy_dsr  # noqa: E402
from quant_factory.experiment_ledger import ExperimentLedger  # noqa: E402
from quant_factory.offensive3 import m1_v103_sprint_optimizer as m1_opt  # noqa: E402
from quant_factory.offensive3.common_contract import (  # noqa: E402
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    CLUSTER_B_YEARS,
    RES_D1_YAHOO_SANCTIONED,
    TIER_NEW7,
    _build_weekday_calendar,
    save_family_candidates,
)
from quant_factory.offensive3.stage3_pipeline import (  # noqa: E402
    TIER_1_FTMO_READY,
    _build_underlying_market_daily_returns,
    _run_candidate_random_entry_mc,
    classify_candidate_tier,
    run_stage3_blind_clb,
)
from quant_factory.research_council import (  # noqa: E402
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)
from quant_factory.robustness_gate import (  # noqa: E402
    RobustnessThresholds,
    evaluate_robustness_gate,
    matched_hold_timing_permutation_p,
)

_SUBPROCESS_CALL_ATTRS: frozenset[str] = frozenset({"run", "Popen", "call", "check_call", "check_output"})


def _check(cond: bool, msg: str) -> None:
    """Explicit invariant check immune to `python -O` assert stripping."""
    if not cond:
        raise AssertionError(msg)


def _scan_subprocess_creationflags(roots: tuple[Path, ...]) -> tuple[int, int, list[str]]:
    """AST-scan all `.py` files under `roots` for subprocess spawn calls missing `creationflags`."""
    files_scanned = 0
    calls_scanned = 0
    violations: list[str] = []

    for root in roots:
        _check(root.is_dir(), f"Missing scan root: {root}")
        for py_path in sorted(root.rglob("*.py")):
            files_scanned += 1
            tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))

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

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                call_name: str | None = None
                if (
                    isinstance(fn, ast.Attribute)
                    and isinstance(fn.value, ast.Name)
                    and fn.value.id in subprocess_aliases
                    and fn.attr in _SUBPROCESS_CALL_ATTRS
                ):
                    call_name = f"{fn.value.id}.{fn.attr}"
                elif isinstance(fn, ast.Name) and fn.id in direct_spawn_names:
                    call_name = fn.id

                if call_name is not None:
                    calls_scanned += 1
                    has_cf = any(kw.arg == "creationflags" for kw in node.keywords)
                    if not has_cf:
                        rel = py_path.relative_to(REPO_ROOT).as_posix()
                        violations.append(f"{rel}:{node.lineno} ({call_name})")

    return files_scanned, calls_scanned, violations


def _load_module_by_path(mod_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(mod_name, path)
    _check(spec is not None and spec.loader is not None, f"Cannot load module spec: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _make_synthetic_d1_asset(
    symbol: str,
    *,
    years: tuple[int, ...] = ALL_DEV_YEARS,
    drift_per_day: float = 0.0,
    vol_per_day: float = 0.006,
    base_price: float = 100.0,
    seed: int = 42,
) -> dict[str, Any]:
    dates = _build_weekday_calendar(years)
    n = len(dates)
    rng = np.random.default_rng(seed)
    ts = np.array(
        [int(datetime.fromisoformat(f"{d}T00:00:00+00:00").timestamp()) for d in dates],
        dtype=np.int64,
    )
    rets = drift_per_day + rng.normal(0.0, vol_per_day, size=n)
    o = base_price * np.exp(np.cumsum(rets))
    c = o * (1.0 + rng.normal(0.0, vol_per_day * 0.5, size=n))
    h = np.maximum(o, c) * (1.0 + abs(vol_per_day) * 0.6)
    lo = np.minimum(o, c) * (1.0 - abs(vol_per_day) * 0.6)
    wds = np.array([date.fromisoformat(d).weekday() for d in dates], dtype=np.int32)
    yrs = np.array([int(d[:4]) for d in dates], dtype=np.int32)
    return {
        "symbol": symbol,
        "data_resolution": RES_D1_YAHOO_SANCTIONED,
        "blindness_tier": TIER_NEW7,
        "m1": None,
        "d1": {
            "times_sec": ts,
            "dates": dates,
            "years": yrs,
            "weekdays": wds,
            "open": o,
            "high": h,
            "low": lo,
            "close": c,
        },
    }


# ---------------------------------------------------------------------------
# 1. Zero-Popup Windows `CREATE_NO_WINDOW` AST Verifier + Runtime Checks
# ---------------------------------------------------------------------------


def test_01_ast_zero_missing_creationflags_and_arch02_zero_asserts() -> None:
    """AST scan MUST prove 0 subprocess calls lack `creationflags` across automation & ops_cloud."""
    scan_roots = (
        REPO_ROOT / "tooling" / "automation",
        REPO_ROOT / "tooling" / "ai-engines" / "ops_cloud",
    )
    files_scanned, calls_scanned, violations = _scan_subprocess_creationflags(scan_roots)
    _check(files_scanned >= 15, f"Expected >= 15 python files scanned, got {files_scanned}")
    _check(calls_scanned >= 30, f"Expected >= 30 subprocess calls scanned, got {calls_scanned}")
    _check(not violations, f"Subprocess calls missing creationflags: {violations}")

    # Verify [ARCH-02]: zero bare `assert` statements in edited quant files
    quant_files = (
        AI_ENGINES / "quant_factory" / "research_council.py",
        AI_ENGINES / "quant_factory" / "robustness_gate.py",
        AI_ENGINES / "quant_factory" / "data_store.py",
        AI_ENGINES / "quant_factory" / "offensive3" / "stage3_pipeline.py",
        AI_ENGINES / "quant_factory" / "offensive3" / "m1_v103_sprint_optimizer.py",
    )
    for qf in quant_files:
        tree = ast.parse(qf.read_text(encoding="utf-8"), filename=str(qf))
        bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        _check(not bare_asserts, f"[ARCH-02] Bare assert found in {qf.name} lines {bare_asserts}")


def test_02_runtime_creationflags_passed_in_all_7_patched_modules() -> None:
    """Verify every patched module actually forwards `creationflags=_NO_WINDOW_FLAGS` at runtime."""
    import ftmo_pre_checkout_guard
    import nfp_cpi_quote_collector
    import node_ctl
    import node_maint_check
    import node_status
    import pc_heartbeat_sender

    from tooling.automation import auto_research_radar as radar

    expected_cf = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    seen_flags: list[tuple[str, int]] = []

    class _FakeProc:
        def __init__(self, stdout: str = "") -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def _recorder(label: str, stdout: str = ""):
        def _fake_run(*_args: Any, **kwargs: Any) -> _FakeProc:
            _check("creationflags" in kwargs, f"{label}: missing creationflags kwarg")
            seen_flags.append((label, int(kwargs["creationflags"])))
            return _FakeProc(stdout)

        return _fake_run

    # 1. node_ctl: resolve_ssh_host, _run_ssh_with_fallback, deploy_scripts (3 calls)
    with patch.object(node_ctl.subprocess, "run", side_effect=_recorder("node_ctl.resolve", "OK\n")):
        _check(node_ctl.resolve_ssh_host(hosts=("naqex-node1",)) == "naqex-node1", "resolve failed")
    with patch.object(node_ctl.subprocess, "run", side_effect=_recorder("node_ctl.ssh", '{"ok": true}')):
        res = node_ctl.run_remote_probe("status", host="naqex-node1")
        _check(res["ok"] is True, "run_remote_probe failed")
    with patch.object(node_ctl.subprocess, "run", side_effect=_recorder("node_ctl.scp", "")):
        dep = node_ctl.deploy_scripts(host="naqex-node1")
        _check(dep["ok"] is True and len(dep["deployed"]) == len(node_ctl.SCRIPT_MAP), "deploy_scripts failed")

    # 2. auto_research_radar: _fetch_github_releases_live
    gh_json = json.dumps(
        [{"tag_name": "v1.0", "name": "v1.0", "html_url": "https://github.com/astral-sh/ruff/releases/tag/v1.0"}]
    )
    with patch.object(radar.subprocess, "run", side_effect=_recorder("radar.gh", gh_json)):
        items = radar._fetch_github_releases_live("astral-sh/ruff", max_results=1, timeout_sec=5.0)
        _check(len(items) == 1, "radar gh releases failed")

    # 3. ftmo_pre_checkout_guard: probe_node1_network_readonly
    geo_json = json.dumps(
        {"geo_lookup_ok": True, "country_code": "VN", "is_cgnat": False, "double_nat_suspected": False}
    )
    with patch.object(ftmo_pre_checkout_guard.subprocess, "run", side_effect=_recorder("guard.ssh", geo_json)):
        net = ftmo_pre_checkout_guard.probe_node1_network_readonly(host="naqex-node1")
        _check(net["non_us_verified"] is True, "pre_checkout_guard probe failed")

    # 4. nfp_cpi_quote_collector: measure_ntp_offset_ms
    ntp_rec = _recorder("nfp.ntp", "12:00:00, +0.0123s\n")
    with patch.object(nfp_cpi_quote_collector.subprocess, "run", side_effect=ntp_rec):
        ntp = nfp_cpi_quote_collector.measure_ntp_offset_ms()
        _check(ntp["ok"] is True, "measure_ntp_offset_ms failed")

    # 5. pc_heartbeat_sender: is_mt5_process_running (simulate win32)
    hb_rec = _recorder("hb.tasklist", "terminal64.exe 1234")
    with (
        patch.object(pc_heartbeat_sender.sys, "platform", "win32"),
        patch.object(pc_heartbeat_sender.subprocess, "run", side_effect=hb_rec),
    ):
        _check(pc_heartbeat_sender.is_mt5_process_running() is True, "heartbeat tasklist check failed")

    # 6. node_status: _run
    with patch.object(node_status.subprocess, "run", side_effect=_recorder("node_status._run", "ok")):
        rc, out_s, _ = node_status._run(["echo", "ok"])
        _check(rc == 0 and out_s == "ok", "node_status._run failed")

    # 7. node_maint_check: run_maint_check
    maint_json = json.dumps(
        {
            "wu_reboot_required": False,
            "cbs_reboot_pending": False,
            "au_policy": {"NoAutoUpdate": 1, "NoAutoReboot": 1},
            "auto_admin_logon": "1",
            "update_orchestrator_reboot": [],
            "disk_idle_ac": "Current AC Power Setting Index: 0x00000000",
        }
    )
    with patch.object(node_maint_check.subprocess, "run", side_effect=_recorder("node_maint.ps", maint_json)):
        mc = node_maint_check.run_maint_check()
        _check(mc["ok"] is True, "node_maint_check failed")

    _check(len(seen_flags) >= 9, f"Expected >= 9 recorded subprocess calls, got {len(seen_flags)}")
    for label, cf in seen_flags:
        _check(cf == expected_cf, f"{label}: creationflags={cf} != expected={expected_cf}")


# ---------------------------------------------------------------------------
# 2. Wave 3 RT2 P1-01: Empirical DSR in `research_council.py`
# ---------------------------------------------------------------------------


def test_03_p1_01_research_council_uses_empirical_dsr_not_legacy_proxy(tmp_path: Path) -> None:
    """Verify `research_council.py` eliminates legacy `1/(T-1)` DSR proxy & matches empirical DSR."""
    rc_path = AI_ENGINES / "quant_factory" / "research_council.py"
    rc_src = rc_path.read_text(encoding="utf-8")
    tree = ast.parse(rc_src, filename=str(rc_path))

    # AST proof: `deflated_sharpe_ratio_empirical` imported from `quant_core.metrics`; legacy proxy absent!
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)
    _check("deflated_sharpe_ratio_empirical" in imported_names, "Missing deflated_sharpe_ratio_empirical import")
    _check("deflated_sharpe_ratio" not in imported_names, "Legacy 1/(T-1) deflated_sharpe_ratio still imported!")

    # Construct exact RT2 P1-01 divergence fixture:
    # T = 1043 days, annualized SR ≈ 1.325 (like F01_US100_NY30_STOP_COIL), M = 142 trials.
    # Legacy 1/(T-1) proxy assumes std_daily = 1/sqrt(1042) ≈ 0.03098 -> DSR >= 0.50 (FALSE PASS!),
    # while wide empirical cross-sectional trial_sharpes (std_daily ≈ 0.042) -> DSR < 0.50 (TRUE FAIL!).
    rng = np.random.default_rng(20261127)
    n_days = 1043
    raw = rng.normal(0.0, 1.0, size=n_days)
    raw = (raw - float(np.mean(raw))) / float(np.std(raw, ddof=1))
    target_daily_sr = 1.3255 / np.sqrt(252.0)
    ret_b = 0.005 * (raw + target_daily_sr)
    ret_a = ret_b.copy()
    inc = rng.normal(0.0, 0.004, size=n_days)
    dates_b = [(date(2021, 1, 4) + timedelta(days=i)).isoformat() for i in range(n_days)]
    _check(dates_b[-1] < "2025-01-01", "Fixture dates must remain strictly pre-2025")

    # Cross-sectional annualized Sharpes with empirical std_daily ≈ 0.042 (> 1/sqrt(1042) ≈ 0.031)
    trial_sh_rng = np.random.default_rng(77)
    trial_sharpes = list(trial_sh_rng.normal(0.0, 0.67, size=141))
    cand_sr_ann = float((np.mean(ret_b) / np.std(ret_b, ddof=1)) * np.sqrt(252.0))
    trial_sharpes.append(cand_sr_ann)

    legacy_val = float(legacy_proxy_dsr(ret_b, n_trials=142, annualization=252.0)["dsr"])
    emp_ref = deflated_sharpe_ratio_empirical(
        ret_b,
        trial_sharpes=trial_sharpes,
        n_trials=142,
        annualization_days=252,
        sharpes_are_annualized=True,
    )
    _check(legacy_val >= 0.50, f"Fixture must reproduce legacy proxy >= 0.50, got {legacy_val}")
    _check(emp_ref.dsr < 0.50, f"Fixture must reproduce empirical DSR < 0.50, got {emp_ref.dsr}")

    card = propose_hypothesis(
        hypothesis_id="F01_PROXY_DIVERGENCE",
        title="Empirical DSR Divergence Audit",
        asset_universe=["US100"],
        timeframe="M1",
        counterparty_mechanism="FAM_P101",
        economic_rationale="Testing empirical cross-sectional Sharpe variance in Research Council G2.",
        causal_invariants=["shift=1_causal", "holdout_rows_analysed=0"],
        n_trials_cumulative=142,
        kill_criteria=KillCriteria(max_bh_q=0.10, min_dsr=0.50, min_cluster_b_sharpe=0.40),
    )
    good_rb = {"verdict": "PASS_ROBUST", "passed": True, "failed_pillars": [], "ranking_score_worst_year_p10_r": 2.0}

    # (A) Via EvidenceBundle.trial_sharpes -> MUST match emp_ref.dsr and FAIL G2!
    ev_ts = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0001,
        family_p_values=(0.0001,),
        candidate_index_in_family=0,
        cost_1x_net=18.0,
        cost_2x_net=16.0,
        n_trades_cluster_b=216,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_b,
        incumbent_dates=dates_b,
        robustness_report=good_rb,
        pbo_value=0.16,
        trial_sharpes=tuple(trial_sharpes),
        trial_sharpes_are_annualized=True,
    )
    v_ts = critique_proposal(card, ev_ts, strict_gates=True)
    g2_ts = v_ts["gates"]["G2_dsr_and_sharpe"]
    _check(g2_ts["passed"] is False, f"G2 MUST fail under empirical DSR < 0.50, got {g2_ts}")
    _check(g2_ts["empirical_variance_used"] is True, "Expected empirical_variance_used=True")
    _check(g2_ts["dsr_mode"] == "empirical_trial_sharpes", f"Unexpected dsr_mode: {g2_ts['dsr_mode']}")
    _check(abs(float(g2_ts["dsr_b"]) - float(emp_ref.dsr)) < 2e-4, f"DSR mismatch: {g2_ts['dsr_b']} vs {emp_ref.dsr}")

    # (B) Via ExperimentLedger DuckDB (WITHOUT passing trial_sharpes on EvidenceBundle!) -> reads DuckDB sharpes!
    led = ExperimentLedger(duckdb_path=tmp_path / "p101.duckdb", registry_path=tmp_path / "p101.sqlite3")
    try:
        for i, sh_val in enumerate(trial_sharpes[:-1]):
            led.record_experiment(
                run_id=f"p101-{i:03d}",
                git_sha="abc1234",
                data_sha="a" * 64,
                strategy_id=f"OTHER_{i:03d}",
                family_id="FAM_P101",
                p_value=0.80,
                sharpe=float(sh_val),
            )
        led.record_experiment(
            run_id="p101-cand",
            git_sha="abc1234",
            data_sha="a" * 64,
            strategy_id="F01_PROXY_DIVERGENCE",
            family_id="FAM_P101",
            p_value=0.0001,
            sharpe=float(cand_sr_ann),
        )
        ev_led = EvidenceBundle(
            cluster_a_returns=ret_a,
            cluster_b_returns=ret_b,
            p_value_raw=0.0001,
            family_p_values=(0.0001,),
            candidate_index_in_family=0,
            cost_1x_net=18.0,
            cost_2x_net=16.0,
            n_trades_cluster_b=216,
            incumbent_daily_returns=inc,
            cluster_b_dates=dates_b,
            incumbent_dates=dates_b,
            robustness_report=good_rb,
            pbo_value=0.16,
        )
        v_led = critique_proposal(card, ev_led, ledger=led, family_id="FAM_P101", strict_gates=True)
        g2_led = v_led["gates"]["G2_dsr_and_sharpe"]
        _check(g2_led["passed"] is False, f"Ledger G2 must fail under empirical DSR < 0.50: {g2_led}")
        _check(g2_led["dsr_mode"] == "empirical_ledger_sharpes", f"Expected ledger sharpes mode, got {g2_led}")
        _check(abs(float(g2_led["dsr_b"]) - float(emp_ref.dsr)) < 2e-4, "Ledger DSR must match empirical DSR")
    finally:
        led.close()

    # (C) Strict fail-closed when M > 1 and NO empirical variance source is provided
    ev_no_var = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0001,
        family_p_values=(0.0001,),
        candidate_index_in_family=0,
        cost_1x_net=18.0,
        cost_2x_net=16.0,
        n_trades_cluster_b=216,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_b,
        incumbent_dates=dates_b,
        robustness_report=good_rb,
        pbo_value=0.16,
    )
    v_strict_missing = critique_proposal(card, ev_no_var, strict_gates=True)
    _check(
        v_strict_missing["verdict"] == "REJECT_KILLED",
        "Missing empirical variance under strict_gates must hard kill",
    )
    _check(
        v_strict_missing["gates"]["G2_dsr_and_sharpe"]["dsr_mode"] == "missing_empirical_variance_fail_closed",
        f"Unexpected mode: {v_strict_missing['gates']['G2_dsr_and_sharpe']}",
    )

    # (D) Zero-trade degenerate returns fail G2 cleanly (zero crash)
    ev_zero = EvidenceBundle(
        cluster_a_returns=np.zeros(100, dtype=np.float64),
        cluster_b_returns=np.zeros(100, dtype=np.float64),
        p_value_raw=1.0,
        family_p_values=(1.0,),
        candidate_index_in_family=0,
        cost_1x_net=0.0,
        cost_2x_net=0.0,
        n_trades_cluster_b=0,
        incumbent_daily_returns=inc[:100],
        cluster_b_dates=dates_b[:100],
        incumbent_dates=dates_b[:100],
        robustness_report=good_rb,
        pbo_value=0.20,
    )
    v_zero = critique_proposal(card, ev_zero, strict_gates=True)
    _check(v_zero["verdict"] == "REJECT_KILLED", "Zero-trade candidate must be REJECT_KILLED")
    _check(v_zero["gates"]["G2_dsr_and_sharpe"]["dsr_b"] == 0.0, "Zero-var DSR must be 0.0")


# ---------------------------------------------------------------------------
# 3. Wave 3 RT2 P1-02: Pair `'SYM_A/SYM_B'` Resolution & Block `sign_flip_fallback`
# ---------------------------------------------------------------------------


def test_04_p1_02_pair_symbols_spread_mc_timing_and_sign_flip_fallback_blocked(tmp_path: Path) -> None:
    """Verify `'SYM_A/SYM_B'` pair lookup builds real spread MC & timing null, and blocks `sign_flip_fallback`."""
    universe = {
        "assets": {
            "GER40": _make_synthetic_d1_asset(
                "GER40", years=ALL_DEV_YEARS, vol_per_day=0.007, base_price=15000.0, seed=31
            ),
            "UK100": _make_synthetic_d1_asset(
                "UK100", years=ALL_DEV_YEARS, vol_per_day=0.006, base_price=7500.0, seed=32
            ),
            "CADJPY": _make_synthetic_d1_asset(
                "CADJPY", years=ALL_DEV_YEARS, vol_per_day=0.006, base_price=105.0, seed=33
            ),
            "CHFJPY": _make_synthetic_d1_asset(
                "CHFJPY", years=ALL_DEV_YEARS, vol_per_day=0.006, base_price=160.0, seed=34
            ),
        }
    }
    cal_clb = _build_weekday_calendar(CLUSTER_B_YEARS)

    # 1. `_build_underlying_market_daily_returns` splits 'GER40/UK100' into exact spread returns (ret_A - ret_B)
    spread_ret = _build_underlying_market_daily_returns(["GER40/UK100"], universe, cal_clb)
    vals = np.array([spread_ret[d] for d in cal_clb], dtype=np.float64)
    nonzero_frac = float(np.mean(np.abs(vals) > 1e-12))
    _check(nonzero_frac > 0.90, f"Pair spread returns must be non-zero (>90% days), got {nonzero_frac:.3f}")

    # Verify exact spread formula on a sample date
    d_a = universe["assets"]["GER40"]["d1"]
    d_b = universe["assets"]["UK100"]["d1"]
    idx_check = d_a["dates"].index("2023-06-15")
    exp_ra = (d_a["close"][idx_check] / d_a["close"][idx_check - 1]) - 1.0
    exp_rb = (d_b["close"][idx_check] / d_b["close"][idx_check - 1]) - 1.0
    _check(
        abs(spread_ret["2023-06-15"] - (exp_ra - exp_rb)) < 1e-12,
        "Pair daily spread return must equal ret_A - ret_B",
    )

    # 2. F11-schema pair trades (`symbol='SYM_A/SYM_B'`, `spread_dir`, `entry_price_a/b`, NO `side` key!)
    n_tr = 70
    step = (len(cal_clb) - 10) // n_tr
    f11_trades_single: list[dict[str, Any]] = []
    f11_trades_multi: list[dict[str, Any]] = []
    for i in range(n_tr):
        ei = i * step
        xi = ei + 4
        ed, xd = cal_clb[ei], cal_clb[xi]
        ets = int(datetime.fromisoformat(f"{ed}T00:00:00+00:00").timestamp())
        xts = int(datetime.fromisoformat(f"{xd}T00:00:00+00:00").timestamp())
        r1 = 1.25 if (i % 2 == 0) else -0.35
        sdir = 1 if (i % 4 < 2) else -1
        base_tr = {
            "symbol": "GER40/UK100",
            "leg_a": "GER40",
            "leg_b": "UK100",
            "spread_dir": sdir,
            "entry_date": ed,
            "exit_date": xd,
            "entry_ts": ets,
            "exit_ts": xts,
            "entry_price_a": 15000.0,
            "sl_price_a": 14800.0,
            "entry_price_b": 7500.0,
            "sl_price_b": 7400.0,
            "hold_bars": 4,
            "swap_real_R": -0.02,
            "swap_zero_pos_R": -0.02,
            "net_R": r1,
            "net_R_1x": r1,
            "friction_over_sl_1x": 0.03,
        }
        f11_trades_single.append(base_tr)
        if i % 2 == 1:
            f11_trades_multi.append({**base_tr, "symbol": "CADJPY/CHFJPY", "leg_a": "CADJPY", "leg_b": "CHFJPY"})
        else:
            f11_trades_multi.append(base_tr)

    # Single-pair MC -> real_market_bars_swing (NEVER None / sign_flip_fallback!)
    mc_single, sw_single = _run_candidate_random_entry_mc(
        trades=f11_trades_single,
        is_swing=True,
        universe=universe,
        m5_cache={},
        clb_year_set=set(CLUSTER_B_YEARS),
        draws=200,
        seed=101,
    )
    _check(mc_single is not None, "Single-pair F11 MC must NOT return None")
    _check(mc_single["mc_mode"] == "real_market_bars_swing", f"Unexpected single-pair mc_mode: {mc_single}")
    _check(sw_single > 0.0, f"Expected positive swap_drag_per_day_r for swing pair, got {sw_single}")

    # Multi-pair basket MC -> real_market_bars_swing_multi_asset (NEVER None / sign_flip_fallback!)
    mc_multi, _ = _run_candidate_random_entry_mc(
        trades=f11_trades_multi,
        is_swing=True,
        universe=universe,
        m5_cache={},
        clb_year_set=set(CLUSTER_B_YEARS),
        draws=200,
        seed=202,
    )
    _check(mc_multi is not None, "Multi-pair F11 MC must NOT return None")
    _check(
        mc_multi["mc_mode"] == "real_market_bars_swing_multi_asset",
        f"Unexpected multi-pair mc_mode: {mc_multi}",
    )

    # Timing permutation on spread_ret -> matched_hold_market_timing (NOT active_trade_sign_permutation!)
    timing_res = matched_hold_timing_permutation_p(
        spread_ret,
        [tr["exit_date"] for tr in f11_trades_single],
        [tr["net_R_1x"] for tr in f11_trades_single],
        draws=1000,
        seed=303,
        hold_bars=[tr["hold_bars"] for tr in f11_trades_single],
        trade_sides=[tr["spread_dir"] for tr in f11_trades_single],
    )
    _check(
        timing_res["null_mode"] == "matched_hold_market_timing",
        f"Expected matched_hold_market_timing for F11 pair, got {timing_res['null_mode']}",
    )

    # 3. `sign_flip_fallback` MUST be blocked from `PASS_ROBUST` (when allow_sign_flip_fallback=False) AND from TIER_1!
    rb_blocked = evaluate_robustness_gate(
        strategy_id="SYN_FALLBACK",
        trade_r=np.array([1.2 if i % 2 == 0 else -0.3 for i in range(60)], dtype=np.float64),
        trade_sides=np.array([1 if i % 4 < 2 else -1 for i in range(60)], dtype=np.int64),
        trade_days=cal_clb[:60],
        mc_result=None,
        closes=None,
        thresholds=RobustnessThresholds(mc_draws=200, allow_sign_flip_fallback=False),
        seed=404,
    )
    r1_mc = rb_blocked["pillars"]["R1_random_entry_mc"]
    _check(r1_mc["mc_mode"] == "sign_flip_fallback", "Expected sign_flip_fallback")
    _check(r1_mc["passed"] is False, "sign_flip_fallback must fail R1 when blocked")
    _check(r1_mc.get("fallback_blocked") is True, "Missing fallback_blocked flag")
    _check(rb_blocked["passed"] is False, "RobustnessGate must not pass when sign_flip_fallback is blocked")

    # Even if a caller artificially passed PASS_ROBUST with sign_flip_fallback, classifier blocks TIER_1!
    tier1_base: dict[str, Any] = {
        "is_primary": True,
        "is_swing": True,
        "min_trades_cluster_b": 30,
        "data_resolution": RES_D1_YAHOO_SANCTIONED,
        "bh_q_primary": 0.01,
        "bh_q_exploratory": 0.02,
        "dsr_empirical": 0.85,
        "robustness_gate": {
            "verdict": "PASS_ROBUST",
            "pillars": {
                "R1_random_entry_mc": {
                    "mc_mode": "sign_flip_fallback",
                    "beat_rate_unbiased": 0.99,
                    "beat_rate_same_side": 0.99,
                },
                "R3_top5_outlier_trim": {"trimmed_winners_pf": 1.5, "trimmed_winners_sum_r": 20.0},
            },
        },
        "net_r_1x": 25.0,
        "net_r_2x": 20.0,
        "net_r_zero_pos_swap": 18.0,
        "fade_net_r_1x": -15.0,
        "cost_breakeven_mult": 5.0,
        "n_trades_clb": 70,
        "research_council": {
            "verdict": "APPROVE_FOR_INCUBATION",
            "gates": {
                "G2_dsr_and_sharpe": {"passed": True},
                "G4_orthogonality": {"passed": True, "corr_all": 0.02, "corr_tail_5pct": 0.05},
                "G7_pbo_cscv": {"passed": True, "pbo": 0.20},
            },
        },
        "timing_permutation": {"passed": True, "p_value": 0.005},
        "prop_max_dd_pct_at_risk": 3.0,
        "prop_worst_1d_pct_at_risk": 1.0,
        "peak_margin_util_frac": 0.20,
        "margin_breached": False,
        "crisis_stress_2018_2024": {"passed": True},
    }
    cls_fb = classify_candidate_tier(tier1_base)
    _check(cls_fb["tier"] != TIER_1_FTMO_READY, f"sign_flip_fallback MUST NEVER reach TIER_1: {cls_fb}")
    _check(
        "PROP_MC_SIGN_FLIP_FALLBACK_BLOCKED" in cls_fb["failed_prop_gates"],
        f"Expected PROP_MC_SIGN_FLIP_FALLBACK_BLOCKED, got {cls_fb['failed_prop_gates']}",
    )

    # Also verify P1-01 classifier check: dsr_empirical < 0.50 blocked from TIER_1 even with real_market_bars!
    tier1_low_dsr = json.loads(json.dumps(tier1_base))
    tier1_low_dsr["robustness_gate"]["pillars"]["R1_random_entry_mc"]["mc_mode"] = "real_market_bars_swing"
    tier1_low_dsr["dsr_empirical"] = 0.374
    cls_low_dsr = classify_candidate_tier(tier1_low_dsr)
    _check(cls_low_dsr["tier"] != TIER_1_FTMO_READY, "dsr_empirical < 0.50 must not reach TIER_1")
    _check("PROP_DSR_EMPIRICAL_LT_050" in cls_low_dsr["failed_prop_gates"], "Missing PROP_DSR_EMPIRICAL_LT_050")

    # 4. E2E Stage-3 synthetic run for F11_PAIRS_STATARB proving zero sign_flip_fallback & empirical DSR!
    class _SynthF11Mod:
        FAMILY_ID = "F11_PAIRS_STATARB"

        @staticmethod
        def evaluate_candidate(spec: dict[str, Any], _univ: Any, years: tuple[int, ...]) -> dict[str, Any]:
            cal = _build_weekday_calendar(tuple(years))
            n_t = 70 if tuple(years) == CLUSTER_B_YEARS else 40
            st = max(1, (len(cal) - 6) // n_t)
            trs: list[dict[str, Any]] = []
            d1x = {d: 0.0 for d in cal}
            d15 = {d: 0.0 for d in cal}
            d2x = {d: 0.0 for d in cal}
            dz = {d: 0.0 for d in cal}
            df = {d: 0.0 for d in cal}
            is_dead = bool(spec.get("dead"))
            rng_m = np.random.default_rng(int(spec["seed"]))
            for k in range(n_t):
                ei = k * st
                xi = ei + 4
                ed, xd = cal[ei], cal[xi]
                r1 = float(rng_m.normal(-0.05, 0.9)) if is_dead else (1.25 if k % 2 == 0 else -0.35)
                sdir = 1 if k % 4 < 2 else -1
                d1x[xd] += r1
                d15[xd] += r1 - 0.015
                d2x[xd] += r1 - 0.03
                dz[xd] += r1
                df[xd] += -r1 - 0.15
                trs.append(
                    {
                        "symbol": "GER40/UK100",
                        "leg_a": "GER40",
                        "leg_b": "UK100",
                        "spread_dir": sdir,
                        "entry_date": ed,
                        "exit_date": xd,
                        "entry_ts": int(datetime.fromisoformat(f"{ed}T00:00:00+00:00").timestamp()),
                        "exit_ts": int(datetime.fromisoformat(f"{xd}T00:00:00+00:00").timestamp()),
                        "entry_price_a": 15000.0,
                        "sl_price_a": 14800.0,
                        "entry_price_b": 7500.0,
                        "sl_price_b": 7400.0,
                        "hold_bars": 4,
                        "swap_real_R": -0.02,
                        "swap_zero_pos_R": -0.02,
                        "net_R": r1,
                        "net_R_1x": r1,
                        "friction_over_sl_1x": 0.03,
                        "margin_util_frac": 0.15,
                    }
                )
            return {
                "trades": trs,
                "daily_pnl_1x": d1x,
                "daily_pnl_15x": d15,
                "daily_pnl_2x": d2x,
                "daily_pnl_zero_pos_swap": dz,
                "fade_daily_pnl_1x": df,
                "data_resolution": RES_D1_YAHOO_SANCTIONED,
                "blindness_tier": TIER_NEW7,
            }

    cdir = tmp_path / "f11_cands"
    rat = "European DAX vs FTSE relative-value mean reversion driven by institutional index arbitrage."
    save_family_candidates(
        "F11_PAIRS_STATARB",
        {
            "primary": [
                {
                    "candidate_id": "F11_PAIR_GOOD",
                    "tier": "PRIMARY",
                    "prop_track": "FTMO_SWING",
                    "symbol": "GER40/UK100",
                    "pairs": [["GER40", "UK100"]],
                    "dead": False,
                    "seed": 1,
                    "economic_rationale": rat,
                    "counterparty_mechanism": "Index arbitrage rebalancing",
                },
                {
                    "candidate_id": "F11_PAIR_NOISE",
                    "tier": "PRIMARY",
                    "prop_track": "FTMO_SWING",
                    "symbol": "GER40/UK100",
                    "pairs": [["GER40", "UK100"]],
                    "dead": True,
                    "seed": 2,
                    "economic_rationale": rat,
                    "counterparty_mechanism": "Noise pair control",
                },
            ],
            "exploratory": [],
        },
        {"discovery_years": list(CLUSTER_A_YEARS), "primary_cap": 15},
        candidates_dir=cdir,
    )
    rng_inc = np.random.default_rng(999)
    inc_daily = {d: float(v) for d, v in zip(cal_clb, rng_inc.normal(0.0003, 0.004, size=len(cal_clb)), strict=True)}
    stage3_res = run_stage3_blind_clb(
        candidates_dir=cdir,
        family_modules={"F11_PAIRS_STATARB": _SynthF11Mod},
        universe=universe,
        incumbent_daily_returns=inc_daily,
        duckdb_path=tmp_path / "f11.duckdb",
        registry_path=tmp_path / "f11.sqlite3",
        full_results_path=tmp_path / "f11_full.json",
        tracked_funnel_path=tmp_path / "f11_funnel.json",
        sign_flip_draws=5000,
        timing_perm_draws=500,
        mc_draws=200,
        pbo_n_slices=8,
        seed=20261127,
    )
    for crec in stage3_res["candidates"]:
        mc_p = crec["robustness_gate"]["pillars"]["R1_random_entry_mc"]
        _check(mc_p["mc_mode"] == "real_market_bars_swing", f"F11 degraded to {mc_p['mc_mode']}")
        _check(
            crec["timing_permutation"]["null_mode"] == "matched_hold_market_timing",
            f"F11 timing degraded to {crec['timing_permutation']['null_mode']}",
        )
        g2 = crec["research_council"]["gates"]["G2_dsr_and_sharpe"]
        _check(g2["empirical_variance_used"] is True, f"Stage3 G2 did not use empirical variance: {g2}")
        _check(abs(float(crec["dsr_council"]) - float(crec["dsr_empirical"])) < 2e-4, "dsr_council != dsr_empirical")


# ---------------------------------------------------------------------------
# 4. RC-6: `ext_days` Includes `2024-10-15` & `NEWS_PRE_FLATTEN` Syncs `gross_R`
# ---------------------------------------------------------------------------


def test_05_rc6_ext_days_2024_10_15_and_news_pre_flatten_gross_r_synced(tmp_path: Path) -> None:
    """Verify RC-6(a) `ext_days` preserves `2024-10-15` E4/E5 rows & RC-6(b) `NEWS_PRE_FLATTEN` syncs `gross_R`."""
    # (A) Synthetic frozen_9e_tapes_v2 where meta["ext_days"] OMITS 2024-10-15 while E4 & E5 contain 2024-10-15!
    day_normal = "2024-10-14"
    day_omitted = "2024-10-15"
    t_norm = int(datetime(2024, 10, 14, 14, 0, tzinfo=UTC).timestamp())
    t_omit = int(datetime(2024, 10, 15, 14, 0, tzinfo=UTC).timestamp())

    st_norm = np.array([t_norm, t_norm + 60], dtype=np.int64)
    st_omit = np.array([t_omit, t_omit + 60], dtype=np.int64)
    mk = np.array([[0.0, 20.0, -10.0, 15.0], [15.0, 40.0, 10.0, 30.0]], dtype=np.float64)

    arrays: dict[str, np.ndarray] = {}
    tapes_meta: dict[str, Any] = {}
    for eng in m1_opt.CORE7_IDS:
        sym = m1_opt.ENGINE_ASSET_MAP[eng]
        if eng in ("E4_US100_SESS40", "E5_US100_RS1130"):
            arrays[f"{eng}__stamps"] = np.concatenate([st_norm, st_omit])
            arrays[f"{eng}__marks"] = np.concatenate([mk, mk], axis=0)
            arrays[f"{eng}__offsets"] = np.array([0, 2, 4], dtype=np.int64)
            tapes_meta[eng] = {
                "days": [day_normal, day_omitted],
                "rows": {
                    day_normal: {
                        "day": day_normal,
                        "asset": sym,
                        "side": 1,
                        "entry": t_norm,
                        "exit": t_norm + 120,
                        "entry_price": 20100.0,
                        "stop_risk_with_cost_usd": 200.0,
                        "net_usd_per_lot": 30.0,
                        "net_R": 0.15,
                    },
                    day_omitted: {
                        "day": day_omitted,
                        "asset": sym,
                        "side": -1,
                        "entry": t_omit,
                        "exit": t_omit + 120,
                        "entry_price": 20200.0,
                        "stop_risk_with_cost_usd": 200.0,
                        "net_usd_per_lot": 30.0,
                        "net_R": 0.15,
                    },
                },
            }
        else:
            arrays[f"{eng}__stamps"] = st_norm
            arrays[f"{eng}__marks"] = mk
            arrays[f"{eng}__offsets"] = np.array([0, 2], dtype=np.int64)
            tapes_meta[eng] = {
                "days": [day_normal],
                "rows": {
                    day_normal: {
                        "day": day_normal, "asset": sym, "side": 1, "entry": t_norm, "exit": t_norm + 120,
                        "entry_price": 150.0, "stop_risk_with_cost_usd": 200.0, "net_usd_per_lot": 30.0, "net_R": 0.15,
                    }
                },
            }

    npz_path = tmp_path / "frozen_9e_tapes_v2.npz"
    np.savez(npz_path, allow_pickle=False, **arrays)
    sha = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    meta = {
        "schema": "naqex-frozen-tapes-v2",
        "binding_sha256": "rc6_binding_sha",
        "npz_sha256": sha,
        "ext_days": [day_normal],  # Deliberately OMITS 2024-10-15!
        "strict_cluster_a_days": [],
        "tapes": tapes_meta,
    }
    (tmp_path / "frozen_9e_tapes_v2.json").write_text(json.dumps(meta), encoding="utf-8")

    # 1. m1_v103_sprint_optimizer.load_frozen_tapes_direct MUST include 2024-10-15 & preserve E4/E5 in prealign!
    loaded_m1 = m1_opt.load_frozen_tapes_direct(tmp_path)
    _check(day_omitted in loaded_m1["ext_days"], f"RC-6(a): 2024-10-15 omitted by m1_opt: {loaded_m1['ext_days']}")
    pre_days = m1_opt.prealign_days_for_tapes(loaded_m1["ext_days"], loaded_m1["tapes"])
    pre_by_day = {d["day"]: [m["eng"] for m in d["cands"]] for d in pre_days}
    _check(
        set(pre_by_day.get(day_omitted, [])) == {"E4_US100_SESS40", "E5_US100_RS1130"},
        f"RC-6(a): E4/E5 dropped on 2024-10-15: {pre_by_day}",
    )

    # 2. flashcrash_pareto_study.load_frozen_tapes_direct MUST include 2024-10-15!
    loaded_fcp = fcp.load_frozen_tapes_direct(tmp_path)
    _check(day_omitted in loaded_fcp["ext_days"], f"RC-6(a): 2024-10-15 omitted by fcp: {loaded_fcp['ext_days']}")

    # 3. data_store._merge_ext_days_with_tapes includes 2024-10-15 & enforces Holdout lock on 2025-01-01
    merged_ds = data_store._merge_ext_days_with_tapes([day_normal], loaded_m1["tapes"])
    _check(day_omitted in merged_ds, "data_store._merge_ext_days_with_tapes missed 2024-10-15")
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        data_store.assert_dev_series_strictly_pre_holdout([*merged_ds, "2025-01-01"])

    # 4. Optional live-cache verification if `.runtime/hot-m1-cache/_derived/frozen_9e_tapes_v2.json` is present locally
    real_derived = REPO_ROOT / ".runtime" / "hot-m1-cache" / "_derived"
    if (real_derived / "frozen_9e_tapes_v2.json").is_file() and (real_derived / "frozen_9e_tapes_v2.npz").is_file():
        real_loaded = m1_opt.load_frozen_tapes_direct(real_derived)
        _check("2024-10-15" in real_loaded["ext_days"], "Real frozen_9e_tapes_v2 loader missed 2024-10-15!")
        _check(real_loaded["max_day"] < "2025-01-01", "Holdout leak in real loaded ext_days")
        _check(real_loaded["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")

    # (B) RC-6(b): `apply_shield_b2_b3_guards` & parity siblings MUST sync/zero `gross_R` on `NEWS_PRE_FLATTEN`!
    t0 = int(datetime(2024, 10, 4, 11, 0, tzinfo=UTC).timestamp())
    news_ts = t0 + 1800  # 30m after entry; news_pad=600 -> t_cut = t0 + 1200 (20m after entry)
    stamps_flat = np.array([t0 + 60 * i for i in range(40)], dtype=np.int64)

    # Case 1: Trade is flat (0.0 USD) at pre-flatten bar k=20, but originally ended at +3.85 gross_R!
    marks_zero = np.zeros((40, 4), dtype=np.float64)
    marks_zero[20] = [0.0, 5.0, -5.0, 0.0]
    marks_zero[-1] = [740.0, 770.0, 730.0, 740.0]

    # Case 2: Trade is at +40.0 USD (+0.20R) at pre-flatten bar k=20, but originally ended at -1.05 gross_R!
    marks_pos = np.zeros((40, 4), dtype=np.float64)
    marks_pos[20] = [30.0, 50.0, 25.0, 40.0]
    marks_pos[-1] = [-200.0, -190.0, -210.0, -200.0]

    row_zero_in = {
        "day": "2024-10-04",
        "asset": "USDJPY",
        "side": 1,
        "entry": t0,
        "exit": t0 + 40 * 60,
        "entry_price": 146.5,
        "stop_risk_with_cost_usd": 200.0,
        "initial_risk_usd": 190.0,
        "net_usd_per_lot": 740.0,
        "net_R": 3.70,
        "gross_R": 3.85,  # Stale end-of-day gross_R that MUST NOT survive NEWS_PRE_FLATTEN!
        "reason": "HARD_FLAT",
        "at_open": True,
    }
    row_pos_in = {**row_zero_in, "day": "2024-10-05", "net_usd_per_lot": -200.0, "net_R": -1.00, "gross_R": -1.05}

    tapes_rc6 = {
        "E1_USDJPY_TOKYO": {
            "2024-10-04": (row_zero_in, stamps_flat, marks_zero),
            "2024-10-05": (row_pos_in, stamps_flat, marks_pos),
        }
    }
    red_cal_3 = {
        "2024-10-04": [(news_ts, "USD", 600)],
        "2024-10-05": [(news_ts, "USD", 600)],
    }
    red_cal_2 = {
        "2024-10-04": [(news_ts, "USD")],
        "2024-10-05": [(news_ts, "USD")],
    }

    # Check m1_v103_sprint_optimizer.apply_shield_b2_b3_guards
    out_m1, st_m1 = m1_opt.apply_shield_b2_b3_guards(
        tapes_rc6, red_news_cal=red_cal_3, news_pad_sec=600, engines=("E1_USDJPY_TOKYO",)
    )
    _check(st_m1["flattened_pre_news"] == 2, f"Expected 2 pre-flattened rows, got {st_m1}")
    r_z = out_m1["E1_USDJPY_TOKYO"]["2024-10-04"][0]
    r_p = out_m1["E1_USDJPY_TOKYO"]["2024-10-05"][0]
    _check(r_z["reason"] == "NEWS_PRE_FLATTEN", "Expected NEWS_PRE_FLATTEN on 2024-10-04")
    _check(abs(float(r_z["net_R"]) - 0.0) < 1e-12, f"Expected net_R=0.0, got {r_z['net_R']}")
    _check(abs(float(r_z["gross_R"]) - 0.0) < 1e-12, f"RC-6(b): stale gross_R not zeroed: {r_z['gross_R']}")
    _check(abs(float(r_p["net_R"]) - 0.20) < 1e-12, f"Expected net_R=0.20, got {r_p['net_R']}")
    _check(abs(float(r_p["gross_R"]) - 0.20) < 1e-12, f"RC-6(b): stale gross_R not synced to 0.20: {r_p['gross_R']}")

    # Check flashcrash_pareto_study.apply_red_news_and_spread_guard
    out_fcp, st_fcp = fcp.apply_red_news_and_spread_guard(
        tapes_rc6, red_news_cal=red_cal_3, news_pad_sec=600, engines=("E1_USDJPY_TOKYO",)
    )
    _check(st_fcp["flattened_pre_news"] == 2, f"fcp expected 2 flattened, got {st_fcp}")
    _check(abs(float(out_fcp["E1_USDJPY_TOKYO"]["2024-10-04"][0]["gross_R"]) - 0.0) < 1e-12, "fcp gross_R not zeroed")
    _check(abs(float(out_fcp["E1_USDJPY_TOKYO"]["2024-10-05"][0]["gross_R"]) - 0.20) < 1e-12, "fcp gross_R not synced")

    # Check capital_optimizer.replay_cache._apply_red_news_guard_to_tape
    out_rc, st_rc = replay_cache._apply_red_news_guard_to_tape(
        tapes_rc6["E1_USDJPY_TOKYO"], red_cal_2, mode="FLATTEN_5M", pad_sec=600
    )
    _check(st_rc["flattened_pre_news"] == 2, f"replay_cache expected 2 flattened, got {st_rc}")
    _check(abs(float(out_rc["2024-10-04"][0]["gross_R"]) - 0.0) < 1e-12, "replay_cache gross_R not zeroed")
    _check(abs(float(out_rc["2024-10-05"][0]["gross_R"]) - 0.20) < 1e-12, "replay_cache gross_R not synced")
