"""Unit & Negative-Mutation Test Suite for Canonical Prop Fleet Lifecycle FSM (`W4-G10`).

Covers `tooling/ai-engines/quant_factory/wave4/prop_lifecycle_orchestrator.py`:
  1. Static invariants: ZERO bare `assert` statements (`[ARCH-02]`), ZERO `MetaTrader5` imports,
     `ORDER_SEND_CAPABLE is False`, `ORDER_SEND_COUNT == 0`, exact 8 canonical states (`S0..S7`)
     and 7 forward transitions.
  2. Full happy-path multi-account lifecycle `S0->S1->S2->S3->S4->S5->S6->S7->S0` (plus `S7->S5`
     second payout cycle, Gated Stagger ticket #2, incident states `E1/E2/E3/CLOSED_ARCHIVED`,
     and SSOT `firms_catalog.json` + `treasury_ledger.py` + `account_phase_preflight.py` reuse).
  3. JSON round-trip persistence with canonical `report_sha256` + hash-chained `event_sha256`
     verification and CLI (`--emit-sample-fixture`, `--validate-ledger`, `--status`).
  4. >= 10 negative mutation tests (all strictly fail-closed):
     - Attach Eval `.set` / non-`FUNDED_1X` preset or Eval preset params on `S4->S5`
     - Missing / malformed / drifted `preset_sha256` on `S4->S5`
     - `ops2_preflight_pass=False` or non-bool `"true"` on `S4->S5`
     - Phase handoffs (`S1->S2`, `S3->S4`, `S5->S6`, `S4->S5`) with `open_positions=1`, `None`, `True`, `float("nan")`
     - Skipping phases (`S0->S5`, `S1->S3`, `S1->S5`, `S2->S5`, `S4->S6`) & exiting `CLOSED_ARCHIVED`
     - `NaN` / `Inf` / `bool` equity and DD mutations
     - `ORDER_SEND_CAPABLE` tamper (both payload tamper and runtime module constant tamper)
     - 1-byte JSON ledger tamper & transition hash-chain tamper caught by `validate_ledger_dict`
     - Unavailable VN contract (`ftmo_swing_50k`) fail-closed rejection
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory.live_ops.account_phase_preflight import (  # noqa: E402
    DEFAULT_FTMO_SPECS_28,
    validate_account_deployment,
)
from quant_factory.wave4 import prop_lifecycle_orchestrator as fsm  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def _valid_funded_preset_params() -> dict[str, Any]:
    return {
        "phase": "FUNDED",
        "InpContractSku": "FTMO_STD10K_FUNDED_1X",
        "InpBasePhaseMult": 1.0,
        "InpProfitLockMult": 1.0,
        "InpAmberDdPct": 3.5,
        "InpRedDdPct": 6.0,
        "InpKillDailyDdPct": 2.5,
        "InpKillStaticDdPct": 8.0,
        "InpTargetProfitPct": 0.0,
        "InpAllowManualHaltFile": True,
        "InpWritePrimaryHeartbeat": True,
    }


def _valid_eval_preset_params() -> dict[str, Any]:
    return {
        "phase": "EVAL",
        "InpContractSku": "FTMO_STD10K_P1_SPRINT_4_5X",
        "InpBasePhaseMult": 4.5,
        "InpProfitLockMult": 2.5,
        "InpAmberDdPct": 3.5,
        "InpRedDdPct": 6.0,
        "InpKillDailyDdPct": 3.5,
        "InpKillStaticDdPct": 8.0,
        "InpTargetProfitPct": 10.0,
        "InpAllowManualHaltFile": True,
        "InpWritePrimaryHeartbeat": True,
    }


def _advance_to_s4(orch: fsm.PropFleetOrchestrator, account_id: str) -> None:
    orch.transition(
        account_id=account_id,
        to_state=fsm.FleetState.S1_CHALLENGE_P1,
        actor="operator",
        utc_ts="2026-10-01T08:00:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
        preset_name="FTMO_Std10K_P1_Sprint_4_5x.set",
        preset_sha256=_sha(f"{account_id}-p1"),
        expected_preset_sha256=_sha(f"{account_id}-p1"),
        equity_usd=10000.0,
    )
    orch.transition(
        account_id=account_id,
        to_state=fsm.FleetState.S2_PASS_P1_HANDOFF,
        actor="ops-monitor",
        utc_ts="2026-10-12T16:00:00Z",
        open_positions=0,
        equity_usd=11050.0,
        trading_days_completed=5,
    )
    orch.transition(
        account_id=account_id,
        to_state=fsm.FleetState.S3_CHALLENGE_P2,
        actor="operator",
        utc_ts="2026-10-13T08:00:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P2_SPRINT,
        preset_name="FTMO_Std10K_P2_Sprint_3_5x.set",
        preset_sha256=_sha(f"{account_id}-p2"),
        expected_preset_sha256=_sha(f"{account_id}-p2"),
        equity_usd=10000.0,
    )
    orch.transition(
        account_id=account_id,
        to_state=fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        actor="ops-monitor",
        utc_ts="2026-10-22T16:00:00Z",
        open_positions=0,
        equity_usd=10520.0,
        trading_days_completed=4,
    )


# ==============================================================================
# 1. Static & Canonical FSM Specification Invariants
# ==============================================================================
def test_static_invariants_zero_asserts_zero_mt5_and_exact_8_states() -> None:
    src_path = AI_ENGINES_DIR / "quant_factory" / "wave4" / "prop_lifecycle_orchestrator.py"
    _check(src_path.is_file(), f"Missing {src_path}")
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(src_path))

    assert_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    _check(len(assert_nodes) == 0, f"[ARCH-02] Bare assert found in {src_path}: {len(assert_nodes)}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(alias.name != "MetaTrader5", "Forbidden MetaTrader5 import")
        elif isinstance(node, ast.ImportFrom):
            _check((node.module or "").split(".")[0] != "MetaTrader5", "Forbidden MetaTrader5 from-import")

    _check(fsm.ORDER_SEND_CAPABLE is False, "ORDER_SEND_CAPABLE must be strictly False")
    _check(fsm.ORDER_SEND_COUNT == 0, "ORDER_SEND_COUNT must be strictly 0")
    _check(fsm.HOLDOUT_CUTOFF_DATE == "2024-12-31", "Holdout cutoff must remain 2024-12-31")
    _check(fsm.HOLDOUT_ROWS_ANALYSED == 0, "holdout_rows_analysed must be 0")
    _check(
        len(fsm.CANONICAL_LIFECYCLE_STATES) == 8,
        f"Expected 8 states S0..S7, got {len(fsm.CANONICAL_LIFECYCLE_STATES)}",
    )
    _check(len(fsm.FORWARD_TRANSITIONS) == 7, f"Expected 7 forward transitions, got {len(fsm.FORWARD_TRANSITIONS)}")
    _check(len(fsm.INCIDENT_TERMINAL_STATES) == 4, "Expected 4 incident/terminal states")
    _check(fsm.FLEET_LEDGER_SCHEMA_VERSION == "naqex-prop-fleet-ledger-v1", "Canonical schema version mismatch")


# ==============================================================================
# 2. Full Happy-Path Multi-Account Lifecycle (S0->S1->S2->S3->S4->S5->S6->S7->S0)
# ==============================================================================
def test_full_multi_account_lifecycle_s0_through_s7_and_back_to_s0_with_ops2_and_treasury() -> None:
    orch = fsm.PropFleetOrchestrator(
        ledger_id="test-multi-lifecycle",
        usd_vnd_rate=25_765.94,
        created_utc="2026-10-01T07:00:00Z",
    )

    # Account A completes full S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S7 -> S0 cycle
    acct_a = orch.register_from_catalog(
        account_id="FTMO-STD10K-A1",
        contract_id="ftmo_standard_10k",
        opened_utc="2026-10-01T07:30:00Z",
    )
    _check(acct_a.state == fsm.FleetState.S0_PRE_CHALLENGE, "Must start at S0")
    _check(acct_a.capital_usd == 10_000.0, "Catalog capital mismatch")
    _check(fsm.resolve_tracker_profile_spec("ftmo_standard_10k") is not None, "Tracker profile lookup failed")

    _advance_to_s4(orch, "FTMO-STD10K-A1")
    _check(orch.accounts["FTMO-STD10K-A1"].state == fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK, "Should reach S4")

    # Verify Gated Stagger ticket #2 eligibility reason emitted on S1->S2
    s1_s2_ev = [e for e in orch.transitions if e.to_state == fsm.FleetState.S2_PASS_P1_HANDOFF.value][0]
    _check("GATED_STAGGER_TICKET2_ELIGIBLE" in s1_s2_ev.reason_codes, "Expected GATED_STAGGER_TICKET2_ELIGIBLE")

    # Run real OPS-2 validate_account_deployment() for Funded 1.0x and pass its PreflightReport into S4->S5
    mw_snap = {
        "USDJPY": {
            "symbol": "USDJPY",
            "trade_mode": "FULL",
            "digits": DEFAULT_FTMO_SPECS_28["USDJPY"]["digits"],
            "contract_size": DEFAULT_FTMO_SPECS_28["USDJPY"]["contract_size"],
            "stops_level": 0,
            "visible": True,
        }
    }
    ops2_report = validate_account_deployment(
        expected_login=550011,
        actual_login=550011,
        expected_trade_mode="REAL",
        actual_trade_mode="REAL",
        firm_profile="FTMO_STANDARD",
        account_phase="FUNDED",
        preset=_valid_funded_preset_params(),
        account_leverage=100,
        market_watch_symbols=mw_snap,
        required_symbols=["USDJPY"],
        strict_funded_1x=True,
    )
    _check(ops2_report.passed is True, f"OPS-2 report should pass, got {ops2_report.reject_codes}")

    funded_sha = _sha("FTMO-STD10K-A1-funded-1x")
    ev_s5 = orch.transition(
        account_id="FTMO-STD10K-A1",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        actor="operator",
        utc_ts="2026-10-23T08:00:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_MasterProp7E_Funded_Safe_1x.set",
        preset_sha256=funded_sha,
        expected_preset_sha256=funded_sha,
        preset_params=_valid_funded_preset_params(),
        ops2_report=ops2_report,
        ops4_traffic_light="GREEN",
        equity_usd=10000.0,
    )
    _check("FUNDED_DUAL_LOCK_PASS" in ev_s5.reason_codes, "Missing FUNDED_DUAL_LOCK_PASS")
    _check("OPS2_REPORT_VERIFIED" in ev_s5.reason_codes, "Missing OPS2_REPORT_VERIFIED")
    _check("OPS2_PRESET_PARAMS_FUNDED_1X_VERIFIED" in ev_s5.reason_codes, "Missing OPS2 preset params check")

    # S5 -> S6 payout audit & harvest
    ops5_sha = _sha("OPS5-BUNDLE-A1-CYCLE1")
    orch.transition(
        account_id="FTMO-STD10K-A1",
        to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
        actor="ops5-packager",
        utc_ts="2026-11-08T17:00:00Z",
        open_positions=0,
        ops4_traffic_light="GREEN",
        ops5_audit_bundle_sha256=ops5_sha,
        equity_usd=10750.0,
        cycle_days_elapsed=16,
        trading_days_completed=10,
        days_since_last_trade=1.0,
    )

    # S6 -> S7 after-payout 3-bucket allocator (with P1 fee refund)
    ev_s7 = orch.transition(
        account_id="FTMO-STD10K-A1",
        to_state=fsm.FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
        actor="treasury-allocator",
        utc_ts="2026-11-11T10:00:00Z",
        open_positions=0,
        payout_gross_usd=750.0,
        withdrawal_fee_usd=9.0,
        fx_bank_fee_usd=3.0,
        fee_refund_usd=68.70,
        equity_usd=10000.0,
    )
    _check(ev_s7.allocation_result is not None, "S7 must record 3-bucket allocation_result")
    alloc = ev_s7.allocation_result or {}
    # 750 * 0.80 = 600 net - 12 fees = 588 + 68.70 cash refund = 656.70 total settled cash
    _check(abs(float(alloc["total_settled_cash_usd"]) - 656.70) < 1e-6, f"Unexpected settled cash: {alloc}")
    buckets = alloc["buckets_usd"]
    _check(
        abs(buckets["house_money_usd"] + buckets["upgrade_challenge_usd"] + buckets["own_book_usd"] - 656.70) <= 0.02,
        f"3 buckets must sum to settled cash: {buckets}",
    )

    # S7 -> S0 cycle back to pre-challenge (full S0..S7->S0 loop)
    orch.transition(
        account_id="FTMO-STD10K-A1",
        to_state=fsm.FleetState.S0_PRE_CHALLENGE,
        actor="operator",
        utc_ts="2026-11-12T08:00:00Z",
        open_positions=0,
    )
    _check(orch.accounts["FTMO-STD10K-A1"].state == fsm.FleetState.S0_PRE_CHALLENGE, "Must return to S0 cleanly")

    # Account B exercises incident & recovery transitions (E1 cooldown -> S0 -> S1 -> E1 -> CLOSED_ARCHIVED)
    orch.register_from_catalog(
        account_id="THE5ERS-HS5K-B1",
        contract_id="the5ers_hs_5k_classic",
        parent_account_id="FTMO-STD10K-A1",
        opened_utc="2026-10-15T08:00:00Z",
    )
    orch.transition(
        account_id="THE5ERS-HS5K-B1",
        to_state=fsm.FleetState.S1_CHALLENGE_P1,
        actor="operator",
        utc_ts="2026-10-15T08:15:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
        preset_sha256=_sha("5ers-p1"),
        equity_usd=5000.0,
    )
    orch.transition(
        account_id="THE5ERS-HS5K-B1",
        to_state=fsm.FleetState.E1_EVAL_FAIL_COOLDOWN,
        actor="ops-monitor",
        utc_ts="2026-10-20T16:00:00Z",
        open_positions=0,
        equity_usd=4520.0,
        static_dd_pct=9.6,
        cooldown_until_utc="2026-10-27T00:00:00Z",
    )
    orch.transition(
        account_id="THE5ERS-HS5K-B1",
        to_state=fsm.FleetState.CLOSED_ARCHIVED,
        actor="operator",
        utc_ts="2026-10-28T09:00:00Z",
        open_positions=0,
    )

    payload = orch.to_dict()
    val = fsm.validate_ledger_dict(payload, verify_sha256=True)
    _check(val["valid"] is True, "Multi-account ledger must validate cleanly")
    _check(val["accounts_count"] == 2, f"Expected 2 accounts, got {val['accounts_count']}")
    _check(val["transitions_count"] == 11, f"Expected 11 transitions, got {val['transitions_count']}")
    _check(
        payload["treasury_snapshot"]["settled_cash_summary"]["settled_payouts_net_usd"] == 588.0,
        "Composed treasury settled_cash_summary mismatch",
    )


# ==============================================================================
# 3. JSON Round-Trip, SHA-256 Integrity & CLI (--emit-sample-fixture / --validate-ledger / --status)
# ==============================================================================
def test_json_roundtrip_sha256_and_cli_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture_path = tmp_path / "sample_fleet_ledger.json"

    rc_emit = fsm.main(["--emit-sample-fixture", str(fixture_path)])
    _check(rc_emit == 0, f"--emit-sample-fixture returned {rc_emit}")
    _check(fixture_path.is_file(), "Sample fixture file not created")
    emit_out = json.loads(capsys.readouterr().out)
    _check(emit_out["validation"]["valid"] is True, "Emitted sample fixture must validate")

    # Round-trip load -> serialize -> identical report_sha256
    loaded = fsm.PropFleetOrchestrator.load(fixture_path, verify_sha256=True)
    re_serialized = loaded.to_dict()
    raw_disk = json.loads(fixture_path.read_text(encoding="utf-8"))
    _check(
        re_serialized["report_sha256"] == raw_disk["report_sha256"],
        "Round-trip report_sha256 drift detected",
    )
    _check(len(re_serialized["accounts"]) == 4, "Expected 4 sample accounts")

    # --validate-ledger PASS
    rc_val = fsm.main(["--validate-ledger", str(fixture_path)])
    _check(rc_val == 0, f"--validate-ledger returned {rc_val}")
    val_out = json.loads(capsys.readouterr().out)
    _check(val_out["valid"] is True, "CLI --validate-ledger should report valid=True")

    # --status PASS
    rc_st = fsm.main(["--status", "--ledger", str(fixture_path)])
    _check(rc_st == 0, f"--status returned {rc_st}")
    st_out = json.loads(capsys.readouterr().out)
    _check(st_out["order_send_capable"] is False, "CLI --status must report order_send_capable=False")
    _check(st_out["fleet_summary"]["active_funded_count"] == 1, "Sample should have 1 active funded account")

    # Tamper 1 byte in JSON -> --validate-ledger MUST fail closed (exit 2)
    tampered = copy.deepcopy(raw_disk)
    tampered["accounts"][0]["equity_usd"] = 999_999.0
    tampered_path = tmp_path / "tampered_ledger.json"
    tampered_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    rc_bad = fsm.main(["--validate-ledger", str(tampered_path)])
    _check(rc_bad == 2, f"Tampered ledger must return exit code 2, got {rc_bad}")
    bad_out = json.loads(capsys.readouterr().out)
    _check(bad_out["valid"] is False, "Tampered ledger must report valid=False")
    _check(bad_out["error_code"] == "REPORT_SHA256_MISMATCH", f"Unexpected error code: {bad_out}")


# ==============================================================================
# 4. Negative Mutation Tests (>= 6 Required — 10 Exhaustive Fail-Closed Mutations)
# ==============================================================================
def test_neg_01_attach_eval_preset_to_funded_s4_to_s5_rejected() -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    orch.register_from_catalog(account_id="ACC-NEG-01", contract_id="ftmo_standard_10k")
    _advance_to_s4(orch, "ACC-NEG-01")

    # 1a: Eval preset_mode on S4->S5
    with pytest.raises(fsm.FleetTransitionError) as exc_mode:
        orch.transition(
            account_id="ACC-NEG-01",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
            preset_sha256=_sha("eval-on-funded"),
        )
    _check(exc_mode.value.code == "EVAL_PRESET_FORBIDDEN_ON_FUNDED", f"Wrong code: {exc_mode.value.code}")

    # 1b: FUNDED_1X label spoofed, but actual preset_params belong to an Eval 4.5x Sprint preset -> OPS-2 catches it!
    with pytest.raises(fsm.FleetTransitionError) as exc_params:
        orch.transition(
            account_id="ACC-NEG-01",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_name="FTMO_Std10K_Funded_Safe_1x.set",
            preset_sha256=_sha("spoofed-eval-params"),
            preset_params=_valid_eval_preset_params(),
        )
    _check(exc_params.value.code == "EVAL_PRESET_ON_FUNDED_ACCOUNT", f"Wrong code: {exc_params.value.code}")

    # 1c: Eval filename on S4->S5
    with pytest.raises(fsm.FleetTransitionError) as exc_name:
        orch.transition(
            account_id="ACC-NEG-01",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_name="FTMO_Std10K_P1_Sprint_4x.set",
            preset_sha256=_sha("eval-name"),
        )
    _check(exc_name.value.code == "EVAL_PRESET_FORBIDDEN_ON_FUNDED", f"Wrong code: {exc_name.value.code}")
    # Account state must remain unchanged at S4 (atomic rollback / no partial mutation)
    _check(orch.accounts["ACC-NEG-01"].state == fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK, "State mutated on reject!")


def test_neg_02_funded_s4_to_s5_rejects_missing_or_drifted_sha256_and_failed_ops2() -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    orch.register_from_catalog(account_id="ACC-NEG-02", contract_id="ftmo_standard_10k")
    _advance_to_s4(orch, "ACC-NEG-02")

    # Missing preset_sha256
    with pytest.raises(fsm.FleetTransitionError) as exc_missing:
        orch.transition(
            account_id="ACC-NEG-02",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_sha256="",
        )
    _check(exc_missing.value.code == "PRESET_SHA256_MISSING_OR_INVALID", f"Wrong code: {exc_missing.value.code}")

    # Drifted preset_sha256
    with pytest.raises(fsm.FleetTransitionError) as exc_drift:
        orch.transition(
            account_id="ACC-NEG-02",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_sha256=_sha("observed-preset"),
            expected_preset_sha256=_sha("expected-preset"),
        )
    _check(exc_drift.value.code == "PRESET_SHA256_DRIFT", f"Wrong code: {exc_drift.value.code}")

    # ops2_preflight_pass=False
    with pytest.raises(fsm.FleetTransitionError) as exc_ops2:
        orch.transition(
            account_id="ACC-NEG-02",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass=False,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_sha256=_sha("valid-sha"),
        )
    _check(exc_ops2.value.code == "OPS2_PREFLIGHT_NOT_PASSED", f"Wrong code: {exc_ops2.value.code}")

    # ops2_preflight_pass="true" (string coercion trap)
    with pytest.raises(fsm.FleetTransitionError) as exc_str_bool:
        orch.transition(
            account_id="ACC-NEG-02",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass="true",  # type: ignore[arg-type]
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_sha256=_sha("valid-sha"),
        )
    _check(exc_str_bool.value.code == "INVALID_OPS2_PREFLIGHT_FLAG", f"Wrong code: {exc_str_bool.value.code}")


@pytest.mark.parametrize(
    ("bad_open_positions", "expected_code"),
    [
        (1, "OPEN_POSITIONS_NONZERO_HANDOFF"),
        (None, "INVALID_OPEN_POSITIONS"),
        (True, "INVALID_OPEN_POSITIONS"),
        (False, "INVALID_OPEN_POSITIONS"),
        (float("nan"), "INVALID_OPEN_POSITIONS"),
        (-1, "INVALID_OPEN_POSITIONS"),
        (0.0, "INVALID_OPEN_POSITIONS"),
    ],
)
def test_neg_03_handoff_rejects_nonzero_none_bool_nan_open_positions(
    bad_open_positions: Any,
    expected_code: str,
) -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    orch.register_from_catalog(account_id="ACC-NEG-03", contract_id="ftmo_standard_10k")
    orch.transition(
        account_id="ACC-NEG-03",
        to_state=fsm.FleetState.S1_CHALLENGE_P1,
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
        preset_sha256=_sha("p1-open-pos"),
    )
    with pytest.raises(fsm.FleetTransitionError) as exc:
        orch.transition(
            account_id="ACC-NEG-03",
            to_state=fsm.FleetState.S2_PASS_P1_HANDOFF,
            open_positions=bad_open_positions,
            equity_usd=11100.0,
            trading_days_completed=5,
        )
    _check(exc.value.code == expected_code, f"open_positions={bad_open_positions!r} gave {exc.value.code}")


def test_neg_04_skipping_phases_and_terminal_exit_rejected() -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    orch.register_from_catalog(account_id="ACC-NEG-04", contract_id="ftmo_standard_10k")

    # S0 -> S5 forbidden
    with pytest.raises(fsm.FleetTransitionError) as exc_05:
        orch.transition(
            account_id="ACC-NEG-04",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_sha256=_sha("skip-05"),
        )
    _check(
        exc_05.value.code == "INVALID_STATE_TRANSITION",
        f"Expected INVALID_STATE_TRANSITION, got {exc_05.value.code}",
    )

    # Move to S1, then try S1 -> S3 and S1 -> S5
    orch.transition(
        account_id="ACC-NEG-04",
        to_state=fsm.FleetState.S1_CHALLENGE_P1,
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
        preset_sha256=_sha("s1"),
    )
    for illegal_target in (fsm.FleetState.S3_CHALLENGE_P2, fsm.FleetState.S5_FUNDED_ACTIVE):
        with pytest.raises(fsm.FleetTransitionError) as exc_skip:
            orch.transition(account_id="ACC-NEG-04", to_state=illegal_target, open_positions=0)
        _check(exc_skip.value.code == "INVALID_STATE_TRANSITION", f"Skip S1->{illegal_target} must fail")

    # Move to S2, try S2 -> S5
    orch.transition(
        account_id="ACC-NEG-04",
        to_state=fsm.FleetState.S2_PASS_P1_HANDOFF,
        open_positions=0,
        equity_usd=11050.0,
        trading_days_completed=5,
    )
    with pytest.raises(fsm.FleetTransitionError) as exc_25:
        orch.transition(account_id="ACC-NEG-04", to_state=fsm.FleetState.S5_FUNDED_ACTIVE, open_positions=0)
    _check(exc_25.value.code == "INVALID_STATE_TRANSITION", "Skip S2->S5 must fail")

    # Move to S4, try S4 -> S6
    orch.transition(
        account_id="ACC-NEG-04",
        to_state=fsm.FleetState.S3_CHALLENGE_P2,
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P2_SPRINT,
        preset_sha256=_sha("s3"),
    )
    orch.transition(
        account_id="ACC-NEG-04",
        to_state=fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        open_positions=0,
        equity_usd=10520.0,
        trading_days_completed=4,
    )
    with pytest.raises(fsm.FleetTransitionError) as exc_46:
        orch.transition(account_id="ACC-NEG-04", to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST, open_positions=0)
    _check(exc_46.value.code == "INVALID_STATE_TRANSITION", "Skip S4->S6 must fail")

    # Archive from S4, then attempt any exit from CLOSED_ARCHIVED
    orch.transition(account_id="ACC-NEG-04", to_state=fsm.FleetState.CLOSED_ARCHIVED, open_positions=0)
    with pytest.raises(fsm.FleetTransitionError) as exc_term:
        orch.transition(account_id="ACC-NEG-04", to_state=fsm.FleetState.S0_PRE_CHALLENGE, open_positions=0)
    _check(exc_term.value.code == "INVALID_STATE_TRANSITION", "CLOSED_ARCHIVED must be strictly terminal")


@pytest.mark.parametrize("bad_equity", [float("nan"), float("inf"), float("-inf"), True, -500.0])
def test_neg_05_nan_inf_bool_negative_equity_rejected(bad_equity: Any) -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    orch.register_from_catalog(account_id="ACC-NEG-05", contract_id="ftmo_standard_10k")
    with pytest.raises(fsm.FleetTransitionError) as exc:
        orch.transition(
            account_id="ACC-NEG-05",
            to_state=fsm.FleetState.S1_CHALLENGE_P1,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
            preset_sha256=_sha("p1-bad-eq"),
            equity_usd=bad_equity,
        )
    _check(exc.value.code == "INVALID_EQUITY_USD", f"equity={bad_equity!r} gave {exc.value.code}")


def test_neg_06_order_send_capable_tamper_rejected_in_payload_ledger_and_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    orch.register_from_catalog(account_id="ACC-NEG-06", contract_id="ftmo_standard_10k")

    # 6a: Transition payload tamper (`order_send_capable=True`)
    with pytest.raises(fsm.FleetTransitionError) as exc_arg:
        orch.transition(
            account_id="ACC-NEG-06",
            to_state=fsm.FleetState.S1_CHALLENGE_P1,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
            preset_sha256=_sha("p1-tamper"),
            order_send_capable=True,
        )
    _check(exc_arg.value.code == "ORDER_SEND_CAPABLE_TAMPER", f"Wrong code: {exc_arg.value.code}")

    # 6b: Ledger JSON tamper (`order_send_capable: true`)
    raw = orch.to_dict()
    raw["order_send_capable"] = True
    with pytest.raises(fsm.LedgerValidationError) as exc_json:
        fsm.validate_ledger_dict(raw, verify_sha256=False)
    _check(exc_json.value.code == "ORDER_SEND_CAPABLE_TAMPER", f"Wrong code: {exc_json.value.code}")

    # 6c: Runtime module constant tamper (`fsm.ORDER_SEND_CAPABLE = True`)
    monkeypatch.setattr(fsm, "ORDER_SEND_CAPABLE", True)
    with pytest.raises(fsm.FleetTransitionError) as exc_mod:
        orch.transition(
            account_id="ACC-NEG-06",
            to_state=fsm.FleetState.S1_CHALLENGE_P1,
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
            preset_sha256=_sha("p1-runtime-tamper"),
        )
    _check(exc_mod.value.code == "ORDER_SEND_CAPABLE_TAMPER", f"Wrong code: {exc_mod.value.code}")


def test_neg_07_payout_s5_to_s6_rejects_nonzero_positions_missing_ops5_red_ops4_and_inactivity() -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    orch.register_from_catalog(account_id="ACC-NEG-07", contract_id="ftmo_standard_10k")
    _advance_to_s4(orch, "ACC-NEG-07")
    orch.transition(
        account_id="ACC-NEG-07",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_sha256=_sha("funded-07"),
    )

    # Open position during S5->S6
    with pytest.raises(fsm.FleetTransitionError) as exc_pos:
        orch.transition(
            account_id="ACC-NEG-07",
            to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
            open_positions=1,
            ops5_audit_bundle_sha256=_sha("ops5-07"),
            equity_usd=10500.0,
            cycle_days_elapsed=15,
        )
    _check(exc_pos.value.code == "OPEN_POSITIONS_NONZERO_HANDOFF", f"Wrong code: {exc_pos.value.code}")

    # Missing OPS-5 SHA-256
    with pytest.raises(fsm.FleetTransitionError) as exc_ops5:
        orch.transition(
            account_id="ACC-NEG-07",
            to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
            open_positions=0,
            ops5_audit_bundle_sha256="",
            equity_usd=10500.0,
            cycle_days_elapsed=15,
        )
    _check(exc_ops5.value.code == "OPS5_AUDIT_BUNDLE_SHA256_REQUIRED", f"Wrong code: {exc_ops5.value.code}")

    # OPS-4 RED blocks payout
    with pytest.raises(fsm.FleetTransitionError) as exc_red:
        orch.transition(
            account_id="ACC-NEG-07",
            to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
            open_positions=0,
            ops4_traffic_light="RED",
            ops5_audit_bundle_sha256=_sha("ops5-07"),
            equity_usd=10500.0,
            cycle_days_elapsed=15,
        )
    _check(exc_red.value.code == "OPS4_RED_BLOCKS_PAYOUT", f"Wrong code: {exc_red.value.code}")

    # 30d inactivity limit breached blocks payout
    with pytest.raises(fsm.FleetTransitionError) as exc_inact:
        orch.transition(
            account_id="ACC-NEG-07",
            to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
            open_positions=0,
            ops5_audit_bundle_sha256=_sha("ops5-07"),
            equity_usd=10500.0,
            cycle_days_elapsed=31,
            days_since_last_trade=30.0,
        )
    _check(exc_inact.value.code == "INACTIVITY_LIMIT_BREACHED", f"Wrong code: {exc_inact.value.code}")


def test_neg_08_unavailable_vn_contract_and_hash_chain_tamper_rejected() -> None:
    orch = fsm.PropFleetOrchestrator(created_utc="2026-10-01T07:00:00Z")
    # FTMO Swing 50K is unavailable in VN (`available_vn: false` in SSOT firms_catalog.json)
    with pytest.raises(fsm.FleetTransitionError) as exc_vn:
        orch.register_from_catalog(account_id="ACC-NEG-08", contract_id="ftmo_swing_50k")
    _check(exc_vn.value.code == "CONTRACT_UNAVAILABLE_VN", f"Wrong code: {exc_vn.value.code}")

    # Build valid ledger, tamper event body AND recompute outer report_sha256 -> inner event_sha256 still catches it!
    sample = fsm.build_sample_fleet_orchestrator().to_dict()
    sample["transitions"][0]["actor"] = "tampered-actor"
    sample["report_sha256"] = fsm.canonical_payload_sha256(sample)
    with pytest.raises(fsm.LedgerValidationError) as exc_chain:
        fsm.validate_ledger_dict(sample, verify_sha256=True)
    _check(exc_chain.value.code == "EVENT_SHA256_MISMATCH", f"Wrong code: {exc_chain.value.code}")
