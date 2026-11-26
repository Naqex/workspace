"""20 Negative Adversarial Mutation Tests — proving EVERY Naqex defense fails closed under BOTH normal & `python -O`.

All 20 mutants are independent, self-contained, zero-local-cache, read-only (`OrderSend = 0`, `Holdout = 0`),
and use explicit `_check()` (never stripped under `python -O` / `python -OO`).
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pytest
from pydantic import ValidationError

AI_ENGINES = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ENGINES.parents[1]
for _p in (AI_ENGINES, REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import hot_m1_cache as hcache  # noqa: E402
import pass5_usdjpy_tokyo as clock  # noqa: E402
from ops_cloud import compute_router  # noqa: E402
from quant_core.causality import (  # noqa: E402
    CausalityViolationError,
    assert_prefix_invariance_numpy,
    assert_prefix_invariance_series,
)
from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_START_UTC_TS,
    HoldoutLockError,
    enforce_pre_holdout_dates,
    enforce_pre_holdout_ts,
)
from quant_core.io_utils import atomic_write_json  # noqa: E402
from quant_core.prop_sim import STAGE_DEAD, PropSimParams, simulate_single_path  # noqa: E402
from quant_core.red_news import MAX_BLACKOUT_SEC, load_calendar_events  # noqa: E402
from quant_core.schemas import FxRatesConfig  # noqa: E402
from quant_core.tca import parse_exec_audit_row, validate_tca_post_reconcile  # noqa: E402
from quant_factory import daily_statement_reconciler as dsr  # noqa: E402
from quant_factory import prop_engine, red_team_auditor  # noqa: E402
from quant_factory import robustness_gate as rg  # noqa: E402
from quant_factory.experiment_ledger import ExperimentLedger  # noqa: E402
from quant_factory.research_council import (  # noqa: E402
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

from tooling.check_architecture import (  # noqa: E402
    check_arch_01_hot_path_scipy,
    check_arch_02_holdout_asserts,
)
from tooling.run_registry.store import JournalCorruptionError  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Fail-closed check immune to `python -O` assert stripping."""
    if not cond:
        raise AssertionError(msg)


def _run_python_o_snippet(code: str) -> None:
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    _check(proc.returncode == 0, f"python -O probe failed (rc={proc.returncode}):\n{proc.stdout}\n{proc.stderr}")


# ------------------------------------------------------------------------------
# Mutant (1): `-O` Holdout date `2025-01-01`
# ------------------------------------------------------------------------------


def test_mutant_01_python_o_holdout_date_2025_01_01() -> None:
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_dates(["2024-12-31", "2025-01-01"], context="mut01")
    _run_python_o_snippet(
        "import sys; sys.path.insert(0, 'tooling/ai-engines'); "
        "assert False; "  # proves -O stripped asserts!
        "from quant_core.holdout_guard import HoldoutLockError, enforce_pre_holdout_dates\n"
        "try:\n"
        "    enforce_pre_holdout_dates(['2025-01-01'], context='mut01_o')\n"
        "except HoldoutLockError:\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(99)\n"
    )


# ------------------------------------------------------------------------------
# Mutant (2): `-O` Holdout tz-shifted `2024-12-31T23:59:59-05:00`
# ------------------------------------------------------------------------------


def test_mutant_02_python_o_holdout_tz_shifted_2024_12_31_minus_0500() -> None:
    tz_shifted = "2024-12-31T23:59:59-05:00"  # = 2025-01-01T04:59:59Z
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_dates([tz_shifted], context="mut02")
    _run_python_o_snippet(
        "import sys; sys.path.insert(0, 'tooling/ai-engines'); "
        "assert False; "
        "from quant_core.holdout_guard import HoldoutLockError, enforce_pre_holdout_dates\n"
        "try:\n"
        "    enforce_pre_holdout_dates('2024-12-31T23:59:59-05:00', context='mut02_o')\n"
        "except HoldoutLockError:\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(99)\n"
    )


# ------------------------------------------------------------------------------
# Mutant (3): `-O` Holdout `1e20` float64 overflow ts
# ------------------------------------------------------------------------------


def test_mutant_03_python_o_holdout_float64_overflow_1e20() -> None:
    overflow = np.array([1e20], dtype=np.float64)
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_ts(overflow, stop_ts=HOLDOUT_START_UTC_TS, context="mut03")
    _run_python_o_snippet(
        "import sys, numpy as np; sys.path.insert(0, 'tooling/ai-engines'); "
        "assert False; "
        "from quant_core.holdout_guard import HOLDOUT_START_UTC_TS, HoldoutLockError, enforce_pre_holdout_ts\n"
        "try:\n"
        "    enforce_pre_holdout_ts(np.array([1e20], dtype=np.float64), stop_ts=HOLDOUT_START_UTC_TS)\n"
        "except HoldoutLockError:\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(99)\n"
    )


# ------------------------------------------------------------------------------
# Mutant (4): `-O` Holdout corrupt lock / SHA mismatch
# ------------------------------------------------------------------------------


def test_mutant_04_python_o_holdout_corrupt_lock_and_sha_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # (a) Corrupt JSON manifest -> HoldoutLockError
    bad_cache = tmp_path / "corrupt-cache"
    bad_cache.mkdir()
    (bad_cache / "manifest.json").write_text("{corrupt-json", encoding="utf-8")
    with pytest.raises(HoldoutLockError):
        hcache.load_asset("USDJPY", cache_dir=bad_cache)

    # (b) Lock SHA mismatch -> HoldoutLockError
    (bad_cache / "manifest.json").write_text(
        json.dumps({"holdout_rows": 0, "holdout_lock_sha256": "0" * 64, "assets": {}}),
        encoding="utf-8",
    )
    with pytest.raises(HoldoutLockError):
        hcache.load_asset("USDJPY", cache_dir=bad_cache)

    # (c) Parquet SHA mismatch -> HoldoutLockError
    (bad_cache / "usdjpy").mkdir()
    (bad_cache / "usdjpy" / "USDJPY-2018.parquet").write_bytes(b"tampered-parquet")
    (bad_cache / "manifest.json").write_text(
        json.dumps(
            {
                "holdout_rows": 0,
                "holdout_lock_sha256": clock.LOCK_SHA,
                "assets": {
                    "USDJPY": {
                        "dir": "usdjpy",
                        "native_Ask": True,
                        "scale": 1000,
                        "years": {
                            str(y): {"parquet": "USDJPY-2018.parquet", "parquet_sha256": "f" * 64}
                            for y in clock.YEAR
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(HoldoutLockError):
        hcache.load_asset("USDJPY", cache_dir=bad_cache, verify_sha=True)

    # (d) Tampered holdout lock in robustness_gate -> HoldoutLockError
    monkeypatch.setattr(rg, "assert_holdout_locked", lambda: (_ for _ in ()).throw(ValueError("SHA mismatch")))
    with pytest.raises(HoldoutLockError):
        rg._enforce_holdout_lock_sealed()

    # (e) Confirm directly under `python -O` subprocess
    _run_python_o_snippet(
        f"import pathlib, sys; sys.path.insert(0, 'tooling/ai-engines'); "
        f"assert False; "
        f"import hot_m1_cache as hcache; "
        f"from quant_core.holdout_guard import HoldoutLockError\n"
        f"try:\n"
        f"    hcache.load_asset('USDJPY', cache_dir=pathlib.Path({str(bad_cache)!r}), verify_sha=True)\n"
        f"except HoldoutLockError:\n"
        f"    raise SystemExit(0)\n"
        f"raise SystemExit(99)\n"
    )


# ------------------------------------------------------------------------------
# Mutant (5): NumPy `shift(-1)` lookahead caught
# ------------------------------------------------------------------------------


def test_mutant_05_numpy_shift_minus_one_lookahead_caught() -> None:
    rng = np.random.default_rng(505)
    n = 60
    t0 = 1_700_000_000
    times = np.array([t0 + i * 60 for i in range(n)], dtype=np.int64)
    bo = 150.0 + np.cumsum(rng.normal(0.0, 0.15, size=n))
    bc = bo + rng.normal(0.0, 0.08, size=n)
    bh = np.maximum(bo, bc) + 0.05
    bl = np.minimum(bo, bc) - 0.05
    quotes = np.column_stack([bo, bh, bl, bc, bo + 0.01, bh + 0.01, bl + 0.01, bc + 0.01]).astype(np.float64)

    def shift_m1_signal(_ts: np.ndarray, q: np.ndarray) -> np.ndarray:
        out = np.empty(q.shape[0], dtype=np.float64)
        out[:-1] = q[1:, 3] - q[:-1, 3]
        out[-1] = 0.0
        return out

    with pytest.raises(CausalityViolationError):
        assert_prefix_invariance_numpy(shift_m1_signal, times, quotes, [15, 30, 45])


# ------------------------------------------------------------------------------
# Mutant (6): 1D full-sample scaling lookahead caught
# ------------------------------------------------------------------------------


def test_mutant_06_1d_full_sample_scaling_lookahead_caught() -> None:
    rng = np.random.default_rng(606)
    vals = rng.normal(0.0, 1.0, size=80)

    def leaky_full_sample_zscore(v: np.ndarray) -> np.ndarray:
        sd = float(np.std(v))
        return (v - float(np.mean(v))) / (sd if sd > 1e-12 else 1.0)

    with pytest.raises(CausalityViolationError):
        assert_prefix_invariance_series(leaky_full_sample_zscore, vals, [20, 40, 60])


# ------------------------------------------------------------------------------
# Mutant (7): `prop_engine` raw `-5.2%` breaches despite `ea_daily_stop=4.5%`
# ------------------------------------------------------------------------------


def test_mutant_07_prop_engine_raw_52pct_breaches_despite_ea_stop_45pct() -> None:
    nets = np.array([-520.0, 400.0, 400.0, 400.0, 400.0], dtype=np.float64)
    dds = np.array([520.0, 10.0, 10.0, 10.0, 10.0], dtype=np.float64)
    flg = np.ones(5, dtype=np.int8)
    idx = np.array([[0, 1, 2, 3, 4]], dtype=np.int32)

    pdays, _, _, _, _, br1, _, _ = prop_engine._simulate_lifecycle_numba(
        idx,
        nets, dds, flg,
        nets, dds, flg,
        2, 10000.0, 98.61, 1.0,
        0.10, 0.05, 0.05, 0.10,
        False, 4, 0.0,
        1.0, 0.80, 10, 0,
        np.array([1.0], dtype=np.float64),
        1.0, 1.0, 1.0,
        0.99, 1.0, 0.99, 1.0,
        0.045,  # ea_daily_stop = 4.5% MUST NOT mask raw -5.2% daily breach!
    )
    _check(int(br1[0]) == 1, "prop_engine failed to catch raw -5.2% breach under ea_daily_stop=4.5%")
    _check(int(pdays[0]) == -1, "Breached path with 0 retries must not pass")

    # Cross-check canonical quant_core.prop_sim SSOT identically
    sim_res = simulate_single_path(
        nets,
        dds,
        flg,
        PropSimParams(
            steps=2,
            capital_usd=10000.0,
            fee_usd=98.61,
            daily_loss_limit_frac=0.05,
            static_loss_limit_frac=0.10,
            max_retries=0,
            p1_mult=1.0,
            p2_mult=1.0,
            funded_mult=1.0,
            ea_daily_stop_frac=0.045,
        ),
    )
    _check(sim_res["breached_p1"] is True and sim_res["final_stage"] == STAGE_DEAD, "prop_sim missed raw -5.2% breach")


# ------------------------------------------------------------------------------
# Mutant (8): `prop_engine` day-10 blowup stays dead through day 252 (0 Infinite Mulligan)
# ------------------------------------------------------------------------------


def test_mutant_08_prop_engine_day10_blowup_stays_dead_through_day_252() -> None:
    horizon = 260
    nets = np.full(horizon, 300.0, dtype=np.float64)
    dds = np.full(horizon, 10.0, dtype=np.float64)
    # Keep days 0..8 modest so account doesn't pass before day-10 blowup (index 9)
    nets[:9] = 20.0
    nets[9] = -580.0
    dds[9] = 580.0
    flg = np.ones(horizon, dtype=np.int8)
    idx = np.arange(horizon, dtype=np.int32).reshape(1, horizon)
    fee = 101.08

    pdays, pay1, cf12, cf24, _, br1, _, tix = prop_engine._simulate_lifecycle_numba(
        idx,
        nets, dds, flg,
        nets, dds, flg,
        2, 10000.0, fee, 1.0,
        0.10, 0.05, 0.05, 0.10,
        False, 4, 0.0,
        1.0, 0.80, 10, 0,  # max_retries=0 -> single ticket
        np.array([1.0], dtype=np.float64),
        1.0, 1.0, 1.0,
        0.99, 1.0, 0.99, 1.0,
        0.035,
    )
    _check(int(br1[0]) == 1 and int(tix[0]) == 1, "Day-10 blowup must breach ticket 1")
    _check(int(pdays[0]) == -1 and int(pay1[0]) == -1, "Infinite Mulligan detected: dead path passed/paid out")
    _check(abs(float(cf12[0]) - (-fee)) < 1e-6, f"cf12 at day 252 expected {-fee}, got {float(cf12[0])}")
    _check(abs(float(cf24[0]) - (-fee)) < 1e-6, f"cf24 expected {-fee}, got {float(cf24[0])}")


# ------------------------------------------------------------------------------
# Mutant (9): `red_team_auditor` shock NOT clamped `< 5%`
# ------------------------------------------------------------------------------


def test_mutant_09_red_team_auditor_shock_not_clamped_below_5pct() -> None:
    sym_map = {"USDJPY": 1.25, "US100": 1.00, "GBPUSD": 0.75, "EURJPY": 0.50}
    r_list = [0.75, 0.59, 0.50, 0.50, 0.50, 0.50, 0.16]
    row = red_team_auditor.compute_simultaneous_shock_row(
        "P1_Sprint_Test (4.00x)",
        r_list,
        sym_map,
        mult=4.00,
        symcap_pct=2.00,
        kill_daily_pct=4.20,
    )
    _check(row["all_engines_symcap_pct"] > 5.0, "SYMCAP simultaneous exposure must exceed 5%")
    _check(
        row["simultaneous_gap_through_pct"] > row["all_engines_symcap_pct"],
        "Simultaneous gap-through shock must include gap slippage and NOT be clamped below 5%",
    )
    _check(row["guarded_with_killswitch_pct"] >= 5.0, "guarded_with_killswitch_pct must NOT be tautologically < 5%")
    _check(row["ftmo_5pct_safe_with_guard"] is False, "Must flag ftmo_5pct_safe_with_guard=False")


# ------------------------------------------------------------------------------
# Mutant (10): `red_news` duplicate / ambiguous / max-blackout poison blocked
# ------------------------------------------------------------------------------


def test_mutant_10_red_news_duplicate_ambiguous_and_max_blackout_blocked(tmp_path: Path) -> None:
    ev = {"utc_ts": 1700000000, "utc_iso": "2023-11-14T22:13:20Z", "ccy": "USD", "event": "US_CPI"}

    # (a) Duplicate event rejected
    p_dup = tmp_path / "dup.json"
    p_dup.write_text(json.dumps({"events": [ev, ev]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_calendar_events(p_dup)

    # (b) Ambiguous dual-schema JSON rejected
    p_amb = tmp_path / "amb.json"
    p_amb.write_text(json.dumps({"events": [ev], "events_by_day": {"2023-11-14": [ev]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Ambiguous dual-schema"):
        load_calendar_events(p_amb)

    # (c) Exceeding MAX_BLACKOUT_SEC (86400s) rejected
    p_max = tmp_path / "max_b.json"
    p_max.write_text(
        json.dumps({"events": [{**ev, "blackout_sec": MAX_BLACKOUT_SEC + 1}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="upper bound"):
        load_calendar_events(p_max)


# ------------------------------------------------------------------------------
# Mutant (11): `schemas` `NaN` / raw-int-`0` / future-`2099` rejected
# ------------------------------------------------------------------------------


def test_mutant_11_schemas_nan_raw_int_zero_and_future_2099_rejected() -> None:
    now_iso = (datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    valid: dict[str, Any] = {
        "usd_vnd": 25765.94,
        "eur_usd": 1.08,
        "eur_vnd": 25765.94 * 1.08,
        "verified_utc": now_iso,
        "source": "mut11",
    }
    with pytest.raises(ValidationError):
        FxRatesConfig.model_validate({**valid, "usd_vnd": float("nan")})
    with pytest.raises(ValidationError):
        FxRatesConfig.model_validate({**valid, "verified_utc": 0})
    with pytest.raises(ValidationError):
        FxRatesConfig.model_validate({**valid, "verified_utc": "2099-01-01T00:00:00Z"})


# ------------------------------------------------------------------------------
# Mutant (12): `compute_router` `touches_holdout=True` blocked (`ok=False` / exit `2`)
# ------------------------------------------------------------------------------


def test_mutant_12_compute_router_touches_holdout_blocked_exit_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = tmp_path / "should_not_exist.txt"
    entry = tmp_path / "dev_dummy.py"
    entry.write_text(f"import pathlib; pathlib.Path({str(sentinel)!r}).write_text('RAN')\n", encoding="utf-8")

    fake_dev = {
        "idle_sec": 100.0,
        "in_overnight_window_ict": False,
        "gpu_util_pct": 0,
        "fullscreen_busy": False,
        "cpu_util_pct": 10.0,
        "free_ram_gb": 16.0,
        "ntp_offset_ms": 10.0,
        "ntp_ok": True,
        "mode": "MODE_A_OWNER_ACTIVE",
    }
    fake_x13 = {
        "ssh_alias": "<X13_WORKER>",
        "transport": "LAN",
        "probe_ms": 50.0,
        "reachable": True,
        "ac_online": True,
        "ac_line_status": 1,
        "battery_status_code": 2,
        "battery_pct": 100,
        "cpu_util_pct": 5.0,
        "free_ram_gb": 10.0,
        "disk_free_gb": 100.0,
        "venv_ok": True,
        "active_job_lock": None,
        "ntp_offset_ms": 20.0,
        "forbidden_files": 0,
        "eligible": True,
        "ineligible_reasons": [],
    }
    monkeypatch.setattr(compute_router, "probe_dev_pc", lambda: fake_dev)
    monkeypatch.setattr(compute_router, "probe_x13_worker", lambda **kw: fake_x13)

    res = compute_router.dispatch_job(
        "mut12_job",
        entry,
        touches_holdout=True,
        dest_dir=tmp_path / "out",
    )
    _check(res["ok"] is False, "touches_holdout=True must return ok=False")
    _check(res.get("blocked_reason") == "TIER_3_ASK_OWNER_APPROVAL_REQUIRED", "Missing Tier-3 block reason")
    _check(not sentinel.exists(), "Blocked touches_holdout job MUST NEVER execute entry script")

    rc_route = compute_router.main(["route", "--touches-holdout"])
    _check(rc_route == 2, f"CLI route --touches-holdout must exit 2, got {rc_route}")

    rc_disp = compute_router.main(
        [
            "dispatch",
            "--job-id",
            "mut12_cli",
            "--entry",
            str(entry),
            "--touches-holdout",
            "--dest",
            str(tmp_path / "o2"),
        ]
    )
    _check(rc_disp == 2, f"CLI dispatch --touches-holdout must exit 2, got {rc_disp}")
    _check(not sentinel.exists(), "Blocked CLI dispatch MUST NEVER execute entry script")


# ------------------------------------------------------------------------------
# Mutant (13): `compute_router` `BatteryStatus==1` / `NaN` / `forbidden_files>0` fails closed
# ------------------------------------------------------------------------------


def test_mutant_13_compute_router_battery_nan_and_forbidden_files_fail_closed() -> None:
    clean_x13: dict[str, Any] = {
        "reachable": True,
        "ac_online": True,
        "ac_line_status": 1,
        "battery_status_code": 2,
        "cpu_util_pct": 10.0,
        "free_ram_gb": 10.0,
        "disk_free_gb": 100.0,
        "venv_ok": True,
        "active_job_lock": None,
        "ntp_offset_ms": 25.0,
        "forbidden_files": 0,
    }
    ok_clean, reasons_clean = compute_router.evaluate_x13_eligibility(clean_x13)
    _check(ok_clean is True and not reasons_clean, f"Baseline clean X13 must pass: {reasons_clean}")

    for label, override in (
        ("BatteryStatus==1", {"battery_status_code": 1}),
        ("cpu NaN", {"cpu_util_pct": float("nan")}),
        ("ram NaN", {"free_ram_gb": float("nan")}),
        ("ntp NaN", {"ntp_offset_ms": float("nan")}),
        ("forbidden_files>0", {"forbidden_files": 1}),
    ):
        ok, reasons = compute_router.evaluate_x13_eligibility({**clean_x13, **override})
        _check(ok is False and len(reasons) >= 1, f"{label} must fail closed, got ok={ok}, reasons={reasons}")


# ------------------------------------------------------------------------------
# Mutant (14): `tca` blank / `None` / `"NaN"` `swap_usd` fails closed
# ------------------------------------------------------------------------------


def test_mutant_14_tca_blank_none_and_nan_swap_fail_closed() -> None:
    base = {
        "utc_ts": 1700000100,
        "magic": 20261122,
        "symbol": "GBPUSD",
        "side": "SELL",
        "event_type": "EXIT",
        "signal_price": 1.25,
        "fill_price": 1.2501,
    }
    row_blank = parse_exec_audit_row({**base, "swap_usd": ""})
    row_none = parse_exec_audit_row({**base, "swap_usd": None})
    _check(row_blank["swap_usd"] is None and row_none["swap_usd"] is None, "Blank/None swap_usd must NOT become 0.0")

    with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
        validate_tca_post_reconcile([row_blank], require_zero_swap=True)
    with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
        validate_tca_post_reconcile([row_none], require_zero_swap=True)
    with pytest.raises(ValueError):
        parse_exec_audit_row({**base, "swap_usd": "NaN"})
    with pytest.raises(ValueError):
        validate_tca_post_reconcile([{**base, "swap_usd": "NaN"}], require_zero_swap=True)


# ------------------------------------------------------------------------------
# Mutant (15): `tca`/`daily_statement_reconciler` `FILL_UNRESOLVED` & broker `-1.50` swap override fail closed
# ------------------------------------------------------------------------------


def test_mutant_15_daily_statement_reconciler_unresolved_and_broker_swap_override(tmp_path: Path) -> None:
    # (a) FILL_UNRESOLVED row in audit CSV -> FAIL_CLOSED
    audit_unres = tmp_path / "audit_unres.csv"
    audit_unres.write_text(
        "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,lots,pnl_usd,swap_usd,commission_usd,deal_id,account_login\n"
        "1700000100,20261122,USDJPY,BUY,FILL_UNRESOLVED,150.0,0.0,0.10,,0.0,0.0,D1,990001\n",
        encoding="utf-8",
    )
    stmt_empty = tmp_path / "stmt_empty.csv"
    stmt_empty.write_text(
        "account_login,deal_id,order_id,position_id,magic,symbol,side,direction,volume,price,pnl_usd,swap_usd,commission_usd,utc_ts\n",
        encoding="utf-8",
    )
    rep_unres = dsr.reconcile_daily_statement(
        audit_csv=audit_unres,
        statement_path=stmt_empty,
        expected_login=990001,
    )
    _check(rep_unres["passed"] is False and rep_unres["status"] == "FAIL_CLOSED", "FILL_UNRESOLVED must FAIL_CLOSED")
    _check(any("FILL_UNRESOLVED" in r for r in rep_unres["fail_reasons"]), "Missing FILL_UNRESOLVED reason")

    # (b) Audit claims swap_usd=0.00 while broker statement reports swap_usd=-1.50 -> broker wins & FAIL_CLOSED!
    audit_swap = tmp_path / "audit_swap.csv"
    audit_swap.write_text(
        "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,lots,pnl_usd,swap_usd,commission_usd,deal_id,account_login\n"
        "1700000200,20261122,USDJPY,BUY,EXIT,150.0,150.10,0.10,6.66,0.00,-0.50,D2,990001\n",
        encoding="utf-8",
    )
    stmt_swap = tmp_path / "stmt_swap.csv"
    stmt_swap.write_text(
        "account_login,deal_id,order_id,position_id,magic,symbol,side,direction,volume,price,pnl_usd,swap_usd,commission_usd,utc_ts\n"
        "990001,D2,O2,P2,20261122,USDJPY,BUY,OUT,0.10,150.10,6.66,-1.50,-0.50,1700000200\n",
        encoding="utf-8",
    )
    rep_swap = dsr.reconcile_daily_statement(
        audit_csv=audit_swap,
        statement_path=stmt_swap,
        expected_login=990001,
        require_zero_swap=True,
    )
    _check(rep_swap["passed"] is False and rep_swap["status"] == "FAIL_CLOSED", "Broker -1.50 swap must FAIL_CLOSED")
    _check(rep_swap["summary"]["nonzero_swap_count"] == 1, "Must adopt authoritative broker -1.50 swap")
    _check(abs(float(rep_swap["summary"]["total_swap_usd"]) - (-1.50)) < 1e-6, "total_swap_usd must equal -1.50")
    _check(rep_swap["post_reconcile_gate"]["passed"] is False, "post_reconcile_gate must fail on -1.50 swap")


# ------------------------------------------------------------------------------
# Mutant (16): `experiment_ledger` SQLite tamper -> `JournalCorruptionError`
# ------------------------------------------------------------------------------


def test_mutant_16_experiment_ledger_sqlite_tamper_raises_journal_corruption(tmp_path: Path) -> None:
    db_path = tmp_path / "exp.duckdb"
    reg_path = tmp_path / "reg.sqlite3"
    ledger = ExperimentLedger(duckdb_path=db_path, registry_path=reg_path)
    ledger.record_experiment(
        run_id="mut16-run-01",
        git_sha="abc1234",
        data_sha="a" * 64,
        strategy_id="STRAT_16",
        family_id="FAM_16",
        p_value=0.45,
        sharpe=0.5,
    )
    _check(ledger.verify_integrity()["verified"] is True, "Clean ledger must verify")

    # Tamper directly with SQLite run_events payload bypassing hash chain
    con = sqlite3.connect(str(reg_path))
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        ev_tbl = next(t for t in tables if "event" in t.lower())
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({ev_tbl})").fetchall()]
        payload_col = next(c for c in cols if "payload" in c.lower())
        con.execute(f"UPDATE {ev_tbl} SET {payload_col} = replace({payload_col}, '0.45', '0.0001')")
        con.commit()
    finally:
        con.close()

    with pytest.raises(JournalCorruptionError):
        ledger.verify_integrity()


# ------------------------------------------------------------------------------
# Mutant (17): `experiment_ledger` DuckDB `UPDATE` tamper -> `JournalCorruptionError`
# ------------------------------------------------------------------------------


def test_mutant_17_experiment_ledger_duckdb_update_tamper_raises_journal_corruption(tmp_path: Path) -> None:
    db_path = tmp_path / "exp.duckdb"
    reg_path = tmp_path / "reg.sqlite3"
    ledger = ExperimentLedger(duckdb_path=db_path, registry_path=reg_path)
    ledger.record_experiment(
        run_id="mut17-run-01",
        git_sha="abc1234",
        data_sha="b" * 64,
        strategy_id="STRAT_17",
        family_id="FAM_17",
        p_value=0.72,
        sharpe=0.25,
    )
    _check(ledger.verify_integrity()["verified"] is True, "Clean ledger must verify")

    con = duckdb.connect(str(db_path))
    try:
        con.execute("UPDATE experiments SET p_value = 0.0001 WHERE run_id = 'mut17-run-01'")
    finally:
        con.close()

    with pytest.raises(JournalCorruptionError, match="LEDGER_CONTENT_TAMPERED"):
        ledger.verify_integrity()


# ------------------------------------------------------------------------------
# Mutant (18): `research_council` p-hacking `M=1` & cross-strategy p-value hijack rejected
# ------------------------------------------------------------------------------


def test_mutant_18_research_council_phacking_m1_and_pvalue_hijack_rejected(tmp_path: Path) -> None:
    ledger = ExperimentLedger(duckdb_path=tmp_path / "rc.duckdb", registry_path=tmp_path / "rc.sqlite3")
    ledger.record_experiment(
        run_id="rc-winner",
        git_sha="abc1234",
        data_sha="c" * 64,
        strategy_id="S_WINNER",
        family_id="FAM_RC18",
        p_value=0.0001,
        sharpe=2.2,
    )
    for i in range(18):
        ledger.record_experiment(
            run_id=f"rc-fail-{i:02d}",
            git_sha="abc1234",
            data_sha="c" * 64,
            strategy_id=f"S_FAIL_{i:02d}",
            family_id="FAM_RC18",
            p_value=0.70,
            sharpe=0.1,
        )
    ledger.record_experiment(
        run_id="rc-bad",
        git_sha="abc1234",
        data_sha="c" * 64,
        strategy_id="S_HIJACKER",
        family_id="FAM_RC18",
        p_value=0.80,
        sharpe=0.15,
    )

    rng = np.random.default_rng(1818)
    ret_a = rng.normal(0.0018, 0.004, size=200)
    ret_b = rng.normal(0.0018, 0.004, size=200)
    inc = rng.normal(0.0002, 0.004, size=200)
    dates_200 = [(date(2022, 1, 3) + timedelta(days=i)).isoformat() for i in range(200)]
    good_rb = {"verdict": "PASS_ROBUST", "passed": True, "failed_pillars": [], "ranking_score_worst_year_p10_r": 2.0}

    # (a) Self-reporting M=1 on a new candidate in a 20-trial family -> ledger forces M=21 -> REJECT_KILLED
    card_m1 = propose_hypothesis(
        hypothesis_id="S_NEW_PHACK",
        title="Self-Reported M=1 Candidate",
        asset_universe=["USDJPY"],
        timeframe="M15",
        counterparty_mechanism="FAM_RC18",
        economic_rationale="Testing ledger override of self-reported M=1 multiple testing p-hacking.",
        causal_invariants=["Strictly causal"],
        n_trials_cumulative=1,
        kill_criteria=KillCriteria(max_bh_q=0.10, min_dsr=0.50, min_cluster_b_sharpe=0.40),
    )
    ev_m1 = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.02,
        family_p_values=(0.02,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_200,
        incumbent_dates=dates_200,
        robustness_report=good_rb,
    )
    v_m1 = critique_proposal(card_m1, ev_m1, ledger=ledger, family_id="FAM_RC18")
    _check(v_m1["effective_n_trials"] == 21, f"Expected M=21, got {v_m1['effective_n_trials']}")
    _check(v_m1["verdict"] == "REJECT_KILLED" and "G1_bh_fdr" in v_m1["failed_gates"], "M=1 p-hack must be rejected")

    # (b) Cross-strategy p-value hijack: S_HIJACKER (logged p=0.80) claims p_value_raw=0.0001 -> blocked!
    card_hj = propose_hypothesis(
        hypothesis_id="S_HIJACKER",
        title="Cross-Strategy P-Value Hijacker",
        asset_universe=["USDJPY"],
        timeframe="M15",
        counterparty_mechanism="FAM_RC18",
        economic_rationale="Testing authoritative logged strategy_id lookup against p-value hijack.",
        causal_invariants=["Strictly causal"],
        n_trials_cumulative=1,
    )
    ev_hj = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0001,
        family_p_values=(0.0001,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_200,
        incumbent_dates=dates_200,
        robustness_report=good_rb,
    )
    v_hj = critique_proposal(card_hj, ev_hj, ledger=ledger, family_id="FAM_RC18")
    _check(v_hj["verdict"] == "REJECT_KILLED" and "G1_bh_fdr" in v_hj["failed_gates"], "Hijack must be rejected")
    _check(abs(float(v_hj["gates"]["G1_bh_fdr"]["p_raw"]) - 0.80) < 1e-4, "Must enforce logged p=0.80, not 0.0001")


# ------------------------------------------------------------------------------
# Mutant (19): `io_utils` `NaN` JSON rollback leaves 0 orphan `.tmp`
# ------------------------------------------------------------------------------


def test_mutant_19_io_utils_nan_json_rollback_zero_orphan_tmp(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_json(target, {"ok": True, "val": 42})
    original_bytes = target.read_bytes()

    with pytest.raises(ValueError):
        atomic_write_json(target, {"ok": False, "bad": float("nan")})

    _check(target.read_bytes() == original_bytes, "Existing target JSON must remain untouched after NaN rollback")
    orphans = list(tmp_path.glob("*.tmp"))
    _check(orphans == [], f"Found orphan .tmp files after NaN JSON rollback: {orphans}")


# ------------------------------------------------------------------------------
# Mutant (20): `check_architecture.py` catches planted `ARCH-02` holdout `assert` & `ARCH-01` forbidden import
# ------------------------------------------------------------------------------


def test_mutant_20_check_architecture_catches_planted_arch01_and_arch02(tmp_path: Path) -> None:
    qc_dir = tmp_path / "tooling" / "ai-engines" / "quant_core"
    qc_dir.mkdir(parents=True)
    planted = qc_dir / "planted_violation.py"
    planted.write_text(
        "import scipy.stats as st\n"
        "\n"
        "def bad_guard(day: str) -> None:\n"
        "    assert day < '2025-01-01', 'HOLDOUT'\n",
        encoding="utf-8",
        newline="\n",
    )

    v1 = check_arch_01_hot_path_scipy(tmp_path)
    v2 = check_arch_02_holdout_asserts(tmp_path)
    _check(len(v1) == 1 and v1[0].rule == "ARCH-01", f"Expected 1 ARCH-01 violation, got {v1}")
    _check(len(v2) == 1 and v2[0].rule == "ARCH-02", f"Expected 1 ARCH-02 violation, got {v2}")
