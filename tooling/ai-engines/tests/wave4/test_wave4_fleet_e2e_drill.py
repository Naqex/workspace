"""End-to-End Multi-Account Fleet Lifecycle & Edge-Case Simulation Drill (`W4-G10`).

Exhaustively exercises `prop_lifecycle_orchestrator.py` and `fleet_admission_and_edge_cases.py`
together in realistic multi-account scenarios:
  1. Full 8-state canonical lifecycle (`S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S7 -> S0`
     plus `S7 -> S5` recurring Funded cycles) across concurrent accounts:
       - Account A (`FTMO-STD10K-A`): P1 -> P2 -> Funded 1.0x (with real OPS-2 PreflightReport
         + Eval `.set` dual-lock rejection probe) -> Payout #1 + P1 Fee Refund -> S7 3-bucket
         allocation -> Cycle #2 Payout #2 -> FTMO Scaling Plan `+25% / 4m` eligibility (`90%` split).
       - Account B (`FTMO-STD25K-B`): Gated Stagger precondition block while Account A is in S1,
         then unlocked after Account A passes P1 -> full `S0..S7 -> S0` recycle.
       - Account C (`FTMO-STD50K-C`): 50K upgrade ticket admitted cleanly under Gated Stagger.
  2. Complete fail-closed incident & recovery matrix across ALL 6 guards (`E1..E6`):
       - `E1`: 1 fail watch vs `>= 2` fails in 30d BLOCK -> unlocked only by signed `OPS-6` receipt.
       - `E2`: Funded Amber `3.5%` (`0.5x`) and Red `6.0%` (`0.0x`) / `E2_FUNDED_DD_FREEZE`
         freezing new Challenges across the entire fleet + `E2 -> S5` unfreeze rules.
       - `E3`: Funded breach postmortem lock (persisting even after `CLOSED_ARCHIVED`) until
         signed `OPS-6` classification (`BOT_BUG | SLIPPAGE | VARIANCE`, `fix_verified=True`).
       - `E4`: FTMO `400,000 USD` active base Funded cap, `200,000 USD` single Challenge cap,
         VN-unavailable contract (`ftmo_swing_50k`), and `naqex-node1` VPS CPU/RAM/Disk/MT5 blocks.
       - `E5`: Same-firm opposite directional hedge (`US100` vs `US100.cash`), duplicate/overlapping
         `MagicNumber` ranges, duplicate MT5 Portable dirs (case/slash normalized), & forbidden `E:`.
       - `E6`: Inactivity `21/27/30d`, stale heartbeat (`> 180s` & `heartbeat.utc_ts < flag_write_utc_ts`
         & `open_positions=None`), NTP `>= 1000 ms`, `PRESET_SHA256_DRIFT`, & Eval `.set` on Funded `S4->S5`.
  3. Cryptographic hash-chain integrity (`event_sha256`, `prev_event_sha256`, `report_sha256`),
     1-byte tamper detection, deterministic replay parity, and strict `ORDER_SEND_CAPABLE == False`.
  4. Operator runbook (`planning/research/MULTI-ACCOUNT-FLEET-RUNBOOK.md`) hygiene audit
     (`<= 18 KB`, `0` bare dollar signs, `0` CRLF, `0` BOM, `0` G12 support nudges, `0` OPSEC leaks).

HARD SAFETY INVARIANTS (`[ARCH-02]`, `G02`, `G11`, `G12`, `G16`):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`, `Holdout 2025+ SEALED`.
  - ZERO bare `assert` statements (all checks immune to `python -O`), ZERO `MetaTrader5` imports.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Final

import pytest

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
REPO_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.tca import canonical_payload_sha256, write_atomic_sha256_json  # noqa: E402
from quant_factory.live_ops.account_phase_preflight import (  # noqa: E402
    DEFAULT_FTMO_SPECS_28,
    validate_account_deployment,
)
from quant_factory.wave4 import fleet_admission_and_edge_cases as guards  # noqa: E402
from quant_factory.wave4 import prop_lifecycle_orchestrator as fsm  # noqa: E402

DRILL_RECEIPT_SCHEMA: Final[str] = "naqex-wave4-fleet-e2e-drill-receipt-v1"
DEFAULT_DRILL_RECEIPT_PATH: Final[Path] = (
    REPO_ROOT / ".runtime" / "offensive4" / "fleet" / "fleet_e2e_drill_receipt.json"
)
RUNBOOK_PATH: Final[Path] = REPO_ROOT / "planning" / "research" / "MULTI-ACCOUNT-FLEET-RUNBOOK.md"
RUNBOOK_MAX_BYTES: Final[int] = 18 * 1024  # 18,432 bytes


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion helper immune to `python -O` stripping (`[ARCH-02]`)."""
    if not cond:
        raise AssertionError(msg)


def _sha(tag: str) -> str:
    return hashlib.sha256(f"NAQEX_E2E_DRILL|{tag}".encode()).hexdigest()


def _healthy_vps(
    *,
    now_iso: str,
    cpu_util_pct: float = 26.5,
    free_ram_gb: float = 5.4,
    disk_c_free_gb: float = 68.0,
    active_mt5_terminals: int = 2,
    ntp_offset_ms: float = 19.0,
    open_positions: Any = 0,
    hb_utc_ts: str | None = None,
    flag_write_utc_ts: str | None = None,
    preset_sha256: str | None = None,
    expected_preset_sha256: str | None = None,
) -> dict[str, Any]:
    hb: dict[str, Any] = {
        "utc_ts": now_iso if hb_utc_ts is None else hb_utc_ts,
        "open_positions": open_positions,
        "terminal_connected": True,
        "kill_switch": False,
        "orphan_no_sl": 0,
    }
    if flag_write_utc_ts is not None:
        hb["flag_write_utc_ts"] = flag_write_utc_ts
    if preset_sha256 is not None:
        hb["preset_sha256"] = preset_sha256
    if expected_preset_sha256 is not None:
        hb["expected_preset_sha256"] = expected_preset_sha256
    return {
        "node_name": "naqex-node1",
        "cpu_util_pct": cpu_util_pct,
        "free_ram_gb": free_ram_gb,
        "disk_c_free_gb": disk_c_free_gb,
        "active_mt5_terminals": active_mt5_terminals,
        "ntp_offset_ms": ntp_offset_ms,
        "heartbeat": hb,
    }


def _funded_safe_preset_params() -> dict[str, Any]:
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


def _eval_sprint_preset_params() -> dict[str, Any]:
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


def _build_ops2_funded_preflight_report(
    *,
    preset_params: dict[str, Any],
    preset_name: str,
    login: int = 99001001,
) -> Any:
    mw_snap = {
        sym: {
            "symbol": sym,
            "trade_mode": "FULL",
            "digits": DEFAULT_FTMO_SPECS_28[sym]["digits"],
            "contract_size": DEFAULT_FTMO_SPECS_28[sym]["contract_size"],
            "stops_level": 0,
            "visible": True,
        }
        for sym in ("EURUSD", "USDJPY")
    }
    return validate_account_deployment(
        expected_login=login,
        actual_login=login,
        expected_trade_mode="REAL",
        actual_trade_mode="REAL",
        firm_profile="FTMO_STANDARD",
        account_phase="FUNDED",
        preset=preset_params,
        preset_name=preset_name,
        account_leverage=100,
        market_watch_symbols=mw_snap,
        required_symbols=["EURUSD", "USDJPY"],
        strict_funded_1x=True,
    )


def _assert_fail_closed_transition(fn: Any, *, expected_codes: tuple[str, ...]) -> str:
    try:
        fn()
    except fsm.FleetTransitionError as exc:
        _check(
            exc.code in expected_codes or any(c in expected_codes for c in exc.reason_codes),
            f"Expected one of {expected_codes}, got code={exc.code!r}, reasons={exc.reason_codes!r}",
        )
        return exc.code
    raise AssertionError(f"Expected FleetTransitionError in {expected_codes}, but transition succeeded!")


def run_full_fleet_e2e_drill(scratch_dir: Path | None = None) -> dict[str, Any]:
    """Execute full S0..S7 lifecycle + E1..E6 fail-closed drill and return deterministic receipt."""
    _check(fsm.ORDER_SEND_CAPABLE is False, "fsm.ORDER_SEND_CAPABLE must be False")
    _check(fsm.ORDER_SEND_COUNT == 0, "fsm.ORDER_SEND_COUNT must be 0")
    _check(guards.ORDER_SEND_CAPABLE is False, "guards.ORDER_SEND_CAPABLE must be False")
    _check(guards.ORDER_SEND_COUNT == 0, "guards.ORDER_SEND_COUNT must be 0")
    _check(fsm.HOLDOUT_CUTOFF_DATE == "2024-12-31", "Holdout cutoff must be 2024-12-31")
    _check(guards.HOLDOUT_CUTOFF_DATE == "2024-12-31", "Guard Holdout cutoff must be 2024-12-31")

    contracts = fsm.load_firms_catalog()
    usd_vnd = fsm.load_usd_vnd_rate()

    # =========================================================================
    # PHASE 1: Multi-Account Canonical Lifecycle (S0..S7 -> S5 & S7 -> S0)
    # =========================================================================
    orch = fsm.PropFleetOrchestrator(
        ledger_id="naqex-wave4-e2e-drill-v1",
        usd_vnd_rate=usd_vnd,
        allocation_policy=fsm.AfterPayoutAllocationPolicy(
            policy_name="PARETO_3_BUCKET_DEFAULT",
            house_money_pct=0.30,
            upgrade_challenge_pct=0.30,
            own_book_pct=0.40,
            reserve_cap_tickets=5.0,
            reference_ticket_usd=109.69,
        ),
        fleet_policy=fsm.FleetPolicy(
            concurrency_mode="GATED_STAGGER",
            max_concurrent_evals=2,
            max_concurrent_funded=4,
            max_accounts_per_firm=4,
            bankroll_budget_usd=1000.0,
        ),
        created_utc="2026-10-01T08:00:00Z",
    )

    sha_a_p1 = _sha("FTMO-STD10K-A-P1")
    sha_a_p2 = _sha("FTMO-STD10K-A-P2")
    sha_a_f1 = _sha("FTMO-STD10K-A-FUNDED-1X")
    sha_a_ops5_c1 = _sha("OPS5-BUNDLE-A-C1")
    sha_a_ops5_c2 = _sha("OPS5-BUNDLE-A-C2")

    sha_b_p1 = _sha("FTMO-STD25K-B-P1")
    sha_b_p2 = _sha("FTMO-STD25K-B-P2")
    sha_b_f1 = _sha("FTMO-STD25K-B-FUNDED-1X")
    sha_b_ops5_c1 = _sha("OPS5-BUNDLE-B-C1")

    sha_c_p1 = _sha("FTMO-STD50K-C-P1")

    # 1.1 Account A registered at S0 and admitted cleanly into S1
    acct_a = orch.register_from_catalog(
        account_id="FTMO-STD10K-A",
        contract_id="ftmo_standard_10k",
        contracts=contracts,
        use_promo_fee=True,
        opened_utc="2026-10-01T08:00:00Z",
        notes="Anchor Ticket #1 for E2E drill.",
    )
    _check(acct_a.state == fsm.FleetState.S0_PRE_CHALLENGE, "Account A must start at S0")

    verdict_a_s0 = guards.evaluate_fleet_admission(
        orch,
        {
            "account_id": "FTMO-STD10K-A",
            "contract_id": "ftmo_standard_10k",
            "firm_id": "ftmo",
            "capital_usd": 10_000.0,
            "state": fsm.FleetState.S0_PRE_CHALLENGE.value,
            "ops2_preflight_pass": True,
            "open_positions": 0,
            "preset_sha256": sha_a_p1,
            "expected_preset_sha256": sha_a_p1,
            "magic_range": [20261100, 20261199],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_std10k_a",
        },
        _healthy_vps(now_iso="2026-10-01T08:10:00Z", active_mt5_terminals=0),
        now_utc="2026-10-01T08:10:00Z",
        contracts=contracts,
        require_ops2_pass=True,
        require_flat=True,
    )
    _check(verdict_a_s0.allowed is True, f"Account A S0 admission failed: {verdict_a_s0.blocking_reasons}")
    _check(verdict_a_s0.order_send_capable is False, "Verdict must have order_send_capable=False")

    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S1_CHALLENGE_P1,
        actor="operator",
        utc_ts="2026-10-01T08:15:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
        preset_name="FTMO_Std10K_P1_Sprint_4_5x.set",
        preset_sha256=sha_a_p1,
        expected_preset_sha256=sha_a_p1,
        equity_usd=10_000.0,
    )

    # 1.2 Gated Stagger enforcement: Account B CANNOT start while Account A is still in S1
    verdict_b_blocked_stagger = guards.evaluate_fleet_admission(
        orch,
        {
            "account_id": "FTMO-STD25K-B",
            "contract_id": "ftmo_standard_25k",
            "firm_id": "ftmo",
            "capital_usd": 25_000.0,
            "ops2_preflight_pass": True,
            "open_positions": 0,
            "preset_sha256": sha_b_p1,
            "expected_preset_sha256": sha_b_p1,
            "magic_range": [20261200, 20261299],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_std25k_b",
        },
        _healthy_vps(now_iso="2026-10-05T08:00:00Z", active_mt5_terminals=1),
        now_utc="2026-10-05T08:00:00Z",
        contracts=contracts,
    )
    _check(verdict_b_blocked_stagger.allowed is False, "Gated Stagger must block Ticket #2 before P1 pass")
    _check(
        "E4_GATED_STAGGER_PRECONDITION_UNMET" in verdict_b_blocked_stagger.blocking_reasons,
        f"Missing Gated Stagger reason: {verdict_b_blocked_stagger.blocking_reasons}",
    )

    # 1.3 Account A passes P1 (S1 -> S2) -> P2 (S2 -> S3 -> S4)
    ev_a_s2 = orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S2_PASS_P1_HANDOFF,
        actor="ops-monitor",
        utc_ts="2026-10-12T16:30:00Z",
        open_positions=0,
        equity_usd=11_080.0,
        daily_dd_pct=1.10,
        static_dd_pct=1.80,
        trading_days_completed=6,
        best_day_share=0.29,
    )
    _check("GATED_STAGGER_TICKET2_ELIGIBLE" in ev_a_s2.reason_codes, "Expected GATED_STAGGER_TICKET2_ELIGIBLE")

    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S3_CHALLENGE_P2,
        actor="operator",
        utc_ts="2026-10-13T07:45:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P2_SPRINT,
        preset_name="FTMO_Std10K_P2_Sprint_3_5x.set",
        preset_sha256=sha_a_p2,
        expected_preset_sha256=sha_a_p2,
        equity_usd=10_000.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        actor="ops-monitor",
        utc_ts="2026-10-24T17:00:00Z",
        open_positions=0,
        equity_usd=10_540.0,
        daily_dd_pct=0.80,
        static_dd_pct=1.30,
        trading_days_completed=5,
        best_day_share=0.31,
    )

    # 1.4 Mandatory S4 -> S5 Dual-Lock negative probes (MUST fail closed without mutating S4 state!)
    s4_s5_eval_mode_code = _assert_fail_closed_transition(
        lambda: orch.transition(
            account_id="FTMO-STD10K-A",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            actor="operator",
            utc_ts="2026-10-26T07:00:00Z",
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
            preset_name="FTMO_Std10K_P1_Sprint_4_5x.set",
            preset_sha256=sha_a_p1,
            expected_preset_sha256=sha_a_p1,
        ),
        expected_codes=("EVAL_PRESET_FORBIDDEN_ON_FUNDED",),
    )
    s4_s5_eval_filename_code = _assert_fail_closed_transition(
        lambda: orch.transition(
            account_id="FTMO-STD10K-A",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            actor="operator",
            utc_ts="2026-10-26T07:01:00Z",
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_name="FTMO_Std10K_Eval_Sprint.set",
            preset_sha256=sha_a_f1,
            expected_preset_sha256=sha_a_f1,
        ),
        expected_codes=("EVAL_PRESET_FORBIDDEN_ON_FUNDED",),
    )
    s4_s5_eval_params_code = _assert_fail_closed_transition(
        lambda: orch.transition(
            account_id="FTMO-STD10K-A",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            actor="operator",
            utc_ts="2026-10-26T07:02:00Z",
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_name="FTMO_Std10K_Funded_Safe_1x.set",
            preset_sha256=sha_a_f1,
            expected_preset_sha256=sha_a_f1,
            preset_params=_eval_sprint_preset_params(),
        ),
        expected_codes=(
            "EVAL_PRESET_ON_FUNDED_FORBIDDEN",
            "FUNDED_BASE_MULT_NOT_1X",
            "FUNDED_RISK_MULT_EXCEEDED",
            "FUNDED_TARGET_PROFIT_NONZERO",
        ),
    )
    s4_s5_open_pos_code = _assert_fail_closed_transition(
        lambda: orch.transition(
            account_id="FTMO-STD10K-A",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            actor="operator",
            utc_ts="2026-10-26T07:03:00Z",
            open_positions=1,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_name="FTMO_Std10K_Funded_Safe_1x.set",
            preset_sha256=sha_a_f1,
            expected_preset_sha256=sha_a_f1,
        ),
        expected_codes=("OPEN_POSITIONS_NONZERO_HANDOFF",),
    )
    s4_s5_sha_drift_code = _assert_fail_closed_transition(
        lambda: orch.transition(
            account_id="FTMO-STD10K-A",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            actor="operator",
            utc_ts="2026-10-26T07:04:00Z",
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_name="FTMO_Std10K_Funded_Safe_1x.set",
            preset_sha256=_sha("TAMPERED-PRESET"),
            expected_preset_sha256=sha_a_f1,
        ),
        expected_codes=("PRESET_SHA256_DRIFT",),
    )
    _check(
        orch.accounts["FTMO-STD10K-A"].state == fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        "Account A must remain safely locked at S4 after failed S4->S5 probes",
    )

    # 1.5 Real OPS-2 PreflightReport + Funded 1.0x params -> S4 -> S5 PASS
    funded_params_a = _funded_safe_preset_params()
    ops2_report_a = _build_ops2_funded_preflight_report(
        preset_params=funded_params_a,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
    )
    _check(ops2_report_a.passed is True, f"OPS-2 Funded report failed: {ops2_report_a.reject_codes}")
    _check(ops2_report_a.order_send_capable is False, "OPS-2 report must be order_send_capable=False")

    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        actor="operator",
        utc_ts="2026-10-26T07:30:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
        preset_sha256=sha_a_f1,
        expected_preset_sha256=sha_a_f1,
        preset_params=funded_params_a,
        ops2_report=ops2_report_a,
        ops4_traffic_light="GREEN",
        equity_usd=10_000.0,
    )

    # 1.6 Account A Payout #1 (S5 -> S6 -> S7 -> S5) + P1 Fee Refund + 3-Bucket Split
    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
        actor="ops5-packager",
        utc_ts="2026-11-10T17:15:00Z",
        open_positions=0,
        ops4_traffic_light="GREEN",
        ops5_audit_bundle_sha256=sha_a_ops5_c1,
        equity_usd=10_700.0,
        daily_dd_pct=0.45,
        static_dd_pct=0.90,
        trading_days_completed=9,
        cycle_days_elapsed=15,
        days_since_last_trade=1.0,
    )
    ev_a_s7_c1 = orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
        actor="treasury-allocator",
        utc_ts="2026-11-13T10:00:00Z",
        open_positions=0,
        payout_gross_usd=700.0,
        withdrawal_fee_usd=8.40,
        fx_bank_fee_usd=2.80,
        fee_refund_usd=68.70,
        equity_usd=10_000.0,
    )
    alloc_c1 = ev_a_s7_c1.allocation_result
    _check(alloc_c1 is not None, "S7 allocation_result must be populated")
    # 700 * 0.80 = 560 - 11.20 = 548.80 + 68.70 refund = 617.50 total settled cash
    _check(abs(alloc_c1["total_settled_cash_usd"] - 617.50) < 1e-6, f"Unexpected settled cash: {alloc_c1}")
    _check(abs(alloc_c1["buckets_usd"]["house_money_usd"] - 185.25) < 1e-6, f"Bad house_money bucket: {alloc_c1}")
    _check(
        abs(alloc_c1["buckets_usd"]["upgrade_challenge_usd"] - 185.25) < 1e-6,
        f"Bad upgrade bucket: {alloc_c1}",
    )
    _check(abs(alloc_c1["buckets_usd"]["own_book_usd"] - 247.00) < 1e-6, f"Bad own_book bucket: {alloc_c1}")
    _check("P1_FEE_REFUND_RECORDED" in ev_a_s7_c1.reason_codes, "Expected P1_FEE_REFUND_RECORDED")

    # Resume Funded Cycle #2 (S7 -> S5) -> Payout #2 -> S5 (for FTMO Scaling +25% / 4m check!)
    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        actor="operator",
        utc_ts="2026-11-14T07:30:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
        preset_sha256=sha_a_f1,
        expected_preset_sha256=sha_a_f1,
        ops4_traffic_light="GREEN",
        equity_usd=10_000.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
        actor="ops5-packager",
        utc_ts="2026-12-01T17:00:00Z",
        open_positions=0,
        ops4_traffic_light="GREEN",
        ops5_audit_bundle_sha256=sha_a_ops5_c2,
        equity_usd=10_600.0,
        daily_dd_pct=0.35,
        static_dd_pct=0.70,
        trading_days_completed=8,
        cycle_days_elapsed=17,
        days_since_last_trade=1.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
        actor="treasury-allocator",
        utc_ts="2026-12-04T10:00:00Z",
        open_positions=0,
        payout_gross_usd=600.0,
        withdrawal_fee_usd=7.20,
        fx_bank_fee_usd=2.40,
        fee_refund_usd=0.0,
        equity_usd=10_000.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-A",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        actor="operator",
        utc_ts="2026-12-05T07:30:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
        preset_sha256=sha_a_f1,
        expected_preset_sha256=sha_a_f1,
        ops4_traffic_light="GREEN",
        equity_usd=10_180.0,
        trading_days_completed=4,
        cycle_days_elapsed=8,
        days_since_last_trade=1.0,
    )

    # 1.7 Account B (`FTMO-STD25K-B`, 25K upgrade) under Gated Stagger -> full S0..S7 -> S0 recycle!
    orch.register_from_catalog(
        account_id="FTMO-STD25K-B",
        contract_id="ftmo_standard_25k",
        contracts=contracts,
        use_promo_fee=True,
        parent_account_id="FTMO-STD10K-A",
        opened_utc="2026-11-15T08:00:00Z",
        notes="25K upgrade ticket unlocked via Gated Stagger + S7 upgrade bucket.",
    )
    verdict_b_admit = guards.evaluate_fleet_admission(
        orch,
        {
            "account_id": "FTMO-STD25K-B",
            "contract_id": "ftmo_standard_25k",
            "firm_id": "ftmo",
            "capital_usd": 25_000.0,
            "state": fsm.FleetState.S0_PRE_CHALLENGE.value,
            "ops2_preflight_pass": True,
            "open_positions": 0,
            "preset_sha256": sha_b_p1,
            "expected_preset_sha256": sha_b_p1,
            "magic_range": [20261200, 20261299],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_std25k_b",
        },
        _healthy_vps(now_iso="2026-11-15T08:10:00Z", active_mt5_terminals=1),
        now_utc="2026-11-15T08:10:00Z",
        contracts=contracts,
        require_ops2_pass=True,
        require_flat=True,
    )
    _check(verdict_b_admit.allowed is True, f"Account B 25K admission failed: {verdict_b_admit.blocking_reasons}")

    orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S1_CHALLENGE_P1,
        actor="operator",
        utc_ts="2026-11-15T08:15:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
        preset_name="FTMO_Std25K_P1_Sprint_4_5x.set",
        preset_sha256=sha_b_p1,
        expected_preset_sha256=sha_b_p1,
        equity_usd=25_000.0,
    )
    orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S2_PASS_P1_HANDOFF,
        actor="ops-monitor",
        utc_ts="2026-11-28T16:40:00Z",
        open_positions=0,
        equity_usd=27_600.0,
        trading_days_completed=6,
    )
    orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S3_CHALLENGE_P2,
        actor="operator",
        utc_ts="2026-11-29T07:45:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P2_SPRINT,
        preset_name="FTMO_Std25K_P2_Sprint_3_5x.set",
        preset_sha256=sha_b_p2,
        expected_preset_sha256=sha_b_p2,
        equity_usd=25_000.0,
    )
    orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        actor="ops-monitor",
        utc_ts="2026-12-10T16:50:00Z",
        open_positions=0,
        equity_usd=26_350.0,
        trading_days_completed=5,
    )
    orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        actor="operator",
        utc_ts="2026-12-12T07:30:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std25K_Funded_Safe_1x.set",
        preset_sha256=sha_b_f1,
        expected_preset_sha256=sha_b_f1,
        preset_params=_funded_safe_preset_params(),
        ops4_traffic_light="GREEN",
        equity_usd=25_000.0,
    )
    orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
        actor="ops5-packager",
        utc_ts="2026-12-28T17:10:00Z",
        open_positions=0,
        ops4_traffic_light="GREEN",
        ops5_audit_bundle_sha256=sha_b_ops5_c1,
        equity_usd=26_500.0,
        daily_dd_pct=0.50,
        static_dd_pct=1.00,
        trading_days_completed=9,
        cycle_days_elapsed=16,
        days_since_last_trade=1.0,
    )
    orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
        actor="treasury-allocator",
        utc_ts="2026-12-31T10:00:00Z",
        open_positions=0,
        payout_gross_usd=1_500.0,
        withdrawal_fee_usd=18.00,
        fx_bank_fee_usd=6.00,
        fee_refund_usd=220.50,
        equity_usd=25_000.0,
    )
    # Explicitly exercise S7 -> S0 recycle transition!
    ev_b_s0_recycle = orch.transition(
        account_id="FTMO-STD25K-B",
        to_state=fsm.FleetState.S0_PRE_CHALLENGE,
        actor="operator",
        utc_ts="2027-01-02T08:00:00Z",
        open_positions=0,
        notes="Completed S7 harvest and recycled slot to S0 for 50K upgrade lane.",
    )
    _check("POST_PAYOUT_RECYCLE_TO_S0" in ev_b_s0_recycle.reason_codes, "Expected POST_PAYOUT_RECYCLE_TO_S0")

    # 1.8 Account C (`FTMO-STD50K-C`, 50K upgrade) queued at S0 & verified via evaluate_fleet_admission
    orch.register_from_catalog(
        account_id="FTMO-STD50K-C",
        contract_id="ftmo_standard_50k",
        contracts=contracts,
        use_promo_fee=True,
        parent_account_id="FTMO-STD25K-B",
        opened_utc="2027-02-05T08:00:00Z",
        notes="50K upgrade tier funded from cumulative S7 upgrade bucket.",
    )
    verdict_c_50k = guards.evaluate_fleet_admission(
        orch,
        {
            "account_id": "FTMO-STD50K-C",
            "contract_id": "ftmo_standard_50k",
            "firm_id": "ftmo",
            "capital_usd": 50_000.0,
            "state": fsm.FleetState.S0_PRE_CHALLENGE.value,
            "ops2_preflight_pass": True,
            "open_positions": 0,
            "preset_sha256": sha_c_p1,
            "expected_preset_sha256": sha_c_p1,
            "magic_range": [20261300, 20261399],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_std50k_c",
        },
        _healthy_vps(now_iso="2027-02-05T08:10:00Z", active_mt5_terminals=1),
        now_utc="2027-02-05T08:10:00Z",
        contracts=contracts,
        require_ops2_pass=True,
    )
    _check(verdict_c_50k.allowed is True, f"Account C 50K upgrade admission failed: {verdict_c_50k.blocking_reasons}")

    # 1.9 FTMO Scaling Plan `+25% / 4m` verification on Account A (opened 2026-10-01 -> +127d = 2027-02-05)
    scaling_early = guards.evaluate_ftmo_scaling_plan(orch.accounts["FTMO-STD10K-A"], now_utc="2027-01-01T08:00:00Z")
    _check(scaling_early.eligible is False, "Account A must NOT be scaling-eligible before 4 months (120d)")
    _check("SCALING_WINDOW_LT_4_MONTHS" in scaling_early.missing_requirements, "Expected SCALING_WINDOW_LT_4_MONTHS")

    scaling_ready = verdict_c_50k.scaling_eligibility
    _check(scaling_ready.eligible_count == 1, f"Expected 1 scaling-eligible account, got {scaling_ready}")
    _check("FTMO-STD10K-A" in scaling_ready.eligible_account_ids, "Account A must be eligible for +25% scaling")
    acct_a_scale = scaling_ready.accounts[0]
    _check(abs(acct_a_scale.increment_usd - 2_500.0) < 1e-6, f"Expected +2500 USD step, got {acct_a_scale}")
    _check(abs(acct_a_scale.next_capital_usd - 12_500.0) < 1e-6, f"Expected 12500 USD next cap, got {acct_a_scale}")
    _check(abs(acct_a_scale.next_payout_split_frac - 0.90) < 1e-6, f"Expected 90% split, got {acct_a_scale}")

    # 1.10 Verify ALL 8 canonical states visited, S7->S0 visited, and hash-chain + tamper detection
    visited_states: set[str] = set()
    visited_edges: set[tuple[str, str]] = set()
    for ev in orch.transitions:
        visited_states.add(ev.from_state)
        visited_states.add(ev.to_state)
        visited_edges.add((ev.from_state, ev.to_state))
        _check(ev.order_send_capable is False, f"Event {ev.event_id} violated order_send_capable=False")

    canonical_state_names = [s.value for s in fsm.CANONICAL_LIFECYCLE_STATES]
    for st_name in canonical_state_names:
        _check(st_name in visited_states, f"Canonical state {st_name} not visited in E2E drill!")
    for src_st, dst_st in fsm.FORWARD_TRANSITIONS:
        _check((src_st.value, dst_st.value) in visited_edges, f"Forward edge {src_st.value}->{dst_st.value} missing!")
    _check(
        (fsm.FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value, fsm.FleetState.S0_PRE_CHALLENGE.value) in visited_edges,
        "S7 -> S0 recycle transition missing!",
    )
    _check(
        (fsm.FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value, fsm.FleetState.S5_FUNDED_ACTIVE.value) in visited_edges,
        "S7 -> S5 recurring cycle transition missing!",
    )

    happy_payload = orch.to_dict()
    val_report = fsm.validate_ledger_dict(happy_payload, verify_sha256=True)
    _check(val_report["valid"] is True, "Happy ledger failed validate_ledger_dict")
    _check(val_report["order_send_capable"] is False, "Validated ledger must have order_send_capable=False")
    _check(val_report["order_send_count"] == 0, "Validated ledger must have order_send_count=0")
    _check(val_report["holdout_rows_analysed"] == 0, "Validated ledger must have holdout_rows_analysed=0")

    # Round-trip save/load if scratch_dir supplied
    if scratch_dir is not None:
        ledger_tmp_path = scratch_dir / "e2e_drill_happy_ledger.json"
        save_info = orch.save(ledger_tmp_path)
        reloaded = fsm.PropFleetOrchestrator.load(ledger_tmp_path, verify_sha256=True)
        _check(
            reloaded.to_dict()["report_sha256"] == save_info["report_sha256"],
            "Round-trip reloaded ledger report_sha256 mismatch!",
        )

    # 1-byte tamper detection on report_sha256 AND event hash chain
    tampered_payload = copy.deepcopy(happy_payload)
    tampered_payload["accounts"][0]["equity_usd"] = round(tampered_payload["accounts"][0]["equity_usd"] + 0.01, 2)
    tamper_report_caught = False
    try:
        fsm.validate_ledger_dict(tampered_payload, verify_sha256=True)
    except fsm.LedgerValidationError as exc:
        _check(exc.code == "REPORT_SHA256_MISMATCH", f"Expected REPORT_SHA256_MISMATCH, got {exc.code}")
        tamper_report_caught = True
    _check(tamper_report_caught, "1-byte ledger tamper was not caught!")

    tampered_chain = copy.deepcopy(happy_payload)
    tampered_chain["transitions"][0]["actor"] = "rogue-actor"
    tamper_chain_caught = False
    try:
        fsm.validate_ledger_dict(tampered_chain, verify_sha256=False)
    except fsm.LedgerValidationError as exc:
        _check(exc.code == "EVENT_SHA256_MISMATCH", f"Expected EVENT_SHA256_MISMATCH, got {exc.code}")
        tamper_chain_caught = True
    _check(tamper_chain_caught, "Transition hash-chain tamper was not caught!")

    # =========================================================================
    # PHASE 2: Exhaustive Incident & Fail-Closed Guard Matrix (E1..E6)
    # =========================================================================
    eval_now = "2027-02-10T12:00:00Z"
    clean_base_ledger: dict[str, Any] = {
        "schema_version": fsm.FLEET_LEDGER_SCHEMA_VERSION,
        "ledger_id": "e2e-incident-matrix-base",
        "order_send_capable": False,
        "order_send_count": 0,
        "holdout_cutoff_date": fsm.HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "fleet_policy": {
            "concurrency_mode": "GATED_STAGGER",
            "max_concurrent_evals": 2,
            "max_concurrent_funded": 4,
            "max_accounts_per_firm": 4,
            "bankroll_budget_usd": 1000.0,
        },
        "accounts": [
            {
                "account_id": "FTMO-F1",
                "contract_id": "ftmo_standard_10k",
                "firm_id": "ftmo",
                "firm_profile": "FTMO_STANDARD",
                "capital_usd": 10_000.0,
                "state": fsm.FleetState.S5_FUNDED_ACTIVE.value,
                "preset_mode": fsm.PRESET_MODE_FUNDED_1X,
                "preset_sha256": sha_a_f1,
                "expected_preset_sha256": sha_a_f1,
                "ops2_preflight_pass": True,
                "ops4_traffic_light": "GREEN",
                "open_positions": 0,
                "equity_usd": 10_200.0,
                "balance_usd": 10_200.0,
                "daily_dd_pct": 0.4,
                "static_dd_pct": 0.8,
                "days_since_last_trade": 2.0,
                "payout_cycles_completed": 1,
                "cumulative_gross_payout_usd": 500.0,
                "payout_split_frac": 0.80,
                "opened_utc": "2026-10-01T08:00:00Z",
                "last_transition_utc": "2026-10-20T08:00:00Z",
                "magic_range": [20261100, 20261199],
                "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_f1",
            }
        ],
        "transitions": [],
    }
    clean_proposed: dict[str, Any] = {
        "account_id": "FTMO-NEXT-01",
        "contract_id": "ftmo_standard_25k",
        "firm_id": "ftmo",
        "capital_usd": 25_000.0,
        "state": fsm.FleetState.S0_PRE_CHALLENGE.value,
        "ops2_preflight_pass": True,
        "open_positions": 0,
        "days_since_last_trade": 0.0,
        "preset_sha256": sha_b_p1,
        "expected_preset_sha256": sha_b_p1,
        "magic_range": [20261200, 20261299],
        "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_next_01",
    }
    clean_vps = _healthy_vps(now_iso=eval_now, active_mt5_terminals=1)

    # --- E1: Anti-Tilt Cooldown (>= 2 fails in 30d -> blocked until signed OPS-6 receipt) ---
    e1_ledger = copy.deepcopy(clean_base_ledger)
    e1_ledger["transitions"] = [
        {
            "account_id": "FTMO-FAIL-01",
            "from_state": fsm.FleetState.S1_CHALLENGE_P1.value,
            "to_state": fsm.FleetState.E1_EVAL_FAIL_COOLDOWN.value,
            "utc_ts": "2027-01-20T14:00:00Z",
        }
    ]
    v_e1_single = guards.evaluate_fleet_admission(
        e1_ledger, clean_proposed, clean_vps, now_utc=eval_now, contracts=contracts
    )
    _check(v_e1_single.allowed is True, "1 fail in 30d should be WARNING watch, not hard BLOCK")
    _check("E1_SINGLE_EVAL_FAIL_IN_30D_WATCH" in v_e1_single.warnings, "Missing E1 1-fail warning")

    e1_ledger["transitions"].append(
        {
            "account_id": "FTMO-FAIL-02",
            "from_state": fsm.FleetState.S3_CHALLENGE_P2.value,
            "to_state": fsm.FleetState.E1_EVAL_FAIL_COOLDOWN.value,
            "utc_ts": "2027-02-05T16:00:00Z",
        }
    )
    v_e1_block = guards.evaluate_fleet_admission(
        e1_ledger, clean_proposed, clean_vps, now_utc=eval_now, contracts=contracts
    )
    _check(v_e1_block.allowed is False, "E1 must block when >= 2 eval fails in 30d")
    _check(guards.GUARD_E1 in v_e1_block.active_guards, "GUARD_E1 missing from active_guards")
    _check("E1_EVAL_FAIL_COOLDOWN_BLOCKED" in v_e1_block.blocking_reasons, "Missing E1 block reason")

    v_e1_stale_rcpt = guards.evaluate_fleet_admission(
        e1_ledger,
        clean_proposed,
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
        ops6_eval_receipt={
            "receipt_id": "OPS6-EVAL-STALE",
            "signed_by": "owner",
            "signed_utc": "2027-02-01T10:00:00Z",  # pre-dates latest fail 2027-02-05
            "report_sha256": _sha("OPS6-EVAL-STALE"),
            "approved_to_resume": True,
        },
    )
    _check(v_e1_stale_rcpt.allowed is False, "Pre-failure OPS-6 receipt must NOT clear E1")
    _check("E1_OPS6_RECEIPT_STALE_PRE_FAILURE" in v_e1_stale_rcpt.blocking_reasons, "Missing stale receipt code")

    v_e1_cleared = guards.evaluate_fleet_admission(
        e1_ledger,
        clean_proposed,
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
        ops6_eval_receipt={
            "receipt_id": "OPS6-EVAL-20270208",
            "signed_by": "owner",
            "signed_utc": "2027-02-08T09:00:00Z",
            "report_sha256": _sha("OPS6-EVAL-20270208"),
            "approved_to_resume": True,
            "root_cause_class": "VARIANCE",
        },
    )
    _check(v_e1_cleared.allowed is True, f"Valid signed OPS-6 receipt must clear E1: {v_e1_cleared.blocking_reasons}")
    _check("E1_COOLDOWN_CLEARED_BY_OPS6_RECEIPT" in v_e1_cleared.warnings, "Expected E1 clearance warning")

    # --- E2: Funded Amber 3.5% / Red 6.0% DD Freeze across entire fleet + FSM E2 unfreeze ---
    e2_amber_ledger = copy.deepcopy(clean_base_ledger)
    e2_amber_ledger["accounts"][0]["static_dd_pct"] = 3.5
    v_e2_amber = guards.evaluate_fleet_admission(
        e2_amber_ledger, clean_proposed, clean_vps, now_utc=eval_now, contracts=contracts
    )
    _check(v_e2_amber.allowed is False, "E2 Amber 3.5% must freeze fleet admission")
    _check(guards.GUARD_E2 in v_e2_amber.active_guards, "GUARD_E2 missing on Amber 3.5%")
    _check("E2_FUNDED_DD_AMBER_FREEZE" in v_e2_amber.blocking_reasons, "Missing E2_FUNDED_DD_AMBER_FREEZE")
    _check(abs(v_e2_amber.fleet_scale_factor - 0.5) < 1e-9, f"Expected 0.5x scale, got {v_e2_amber.fleet_scale_factor}")

    e2_red_ledger = copy.deepcopy(clean_base_ledger)
    e2_red_ledger["accounts"][0]["static_dd_pct"] = 6.0
    v_e2_red = guards.evaluate_fleet_admission(
        e2_red_ledger, clean_proposed, clean_vps, now_utc=eval_now, contracts=contracts
    )
    _check(v_e2_red.allowed is False, "E2 Red 6.0% must freeze fleet admission")
    _check("E2_FUNDED_DD_RED_FREEZE" in v_e2_red.blocking_reasons, "Missing E2_FUNDED_DD_RED_FREEZE")
    _check(abs(v_e2_red.fleet_scale_factor - 0.0) < 1e-9, f"Expected 0.0x scale, got {v_e2_red.fleet_scale_factor}")

    # Exercise FSM S5 -> E2 -> S5 unfreeze guard (blocked on RED, allowed once GREEN)
    e2_fsm = fsm.PropFleetOrchestrator(
        ledger_id="e2-fsm-drill",
        usd_vnd_rate=usd_vnd,
        created_utc="2027-01-01T08:00:00Z",
    )
    e2_fsm.register_from_catalog(
        account_id="FTMO-E2-TEST",
        contract_id="ftmo_standard_10k",
        contracts=contracts,
        opened_utc="2027-01-01T08:00:00Z",
    )
    e2_fsm.transition(
        account_id="FTMO-E2-TEST",
        to_state=fsm.FleetState.S1_CHALLENGE_P1,
        utc_ts="2027-01-01T08:10:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P1_SPRINT,
        preset_sha256=sha_a_p1,
    )
    e2_fsm.transition(
        account_id="FTMO-E2-TEST",
        to_state=fsm.FleetState.S2_PASS_P1_HANDOFF,
        utc_ts="2027-01-08T16:00:00Z",
        open_positions=0,
        equity_usd=11_020.0,
        trading_days_completed=5,
    )
    e2_fsm.transition(
        account_id="FTMO-E2-TEST",
        to_state=fsm.FleetState.S3_CHALLENGE_P2,
        utc_ts="2027-01-09T08:00:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_EVAL_P2_SPRINT,
        preset_sha256=sha_a_p2,
    )
    e2_fsm.transition(
        account_id="FTMO-E2-TEST",
        to_state=fsm.FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        utc_ts="2027-01-16T16:00:00Z",
        open_positions=0,
        equity_usd=10_520.0,
        trading_days_completed=5,
    )
    e2_fsm.transition(
        account_id="FTMO-E2-TEST",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        utc_ts="2027-01-17T08:00:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
        preset_sha256=sha_a_f1,
        expected_preset_sha256=sha_a_f1,
        ops4_traffic_light="GREEN",
    )
    e2_fsm.transition(
        account_id="FTMO-E2-TEST",
        to_state=fsm.FleetState.E2_FUNDED_DD_FREEZE,
        utc_ts="2027-01-22T15:00:00Z",
        open_positions=0,
        static_dd_pct=6.1,
        ops4_traffic_light="RED",
    )
    _assert_fail_closed_transition(
        lambda: e2_fsm.transition(
            account_id="FTMO-E2-TEST",
            to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
            utc_ts="2027-01-23T08:00:00Z",
            open_positions=0,
            ops2_preflight_pass=True,
            preset_mode=fsm.PRESET_MODE_FUNDED_1X,
            preset_name="FTMO_Std10K_Funded_Safe_1x.set",
            preset_sha256=sha_a_f1,
            expected_preset_sha256=sha_a_f1,
            ops4_traffic_light="RED",
        ),
        expected_codes=("OPS4_RED_BLOCKS_UNFREEZE",),
    )
    e2_fsm.transition(
        account_id="FTMO-E2-TEST",
        to_state=fsm.FleetState.S5_FUNDED_ACTIVE,
        utc_ts="2027-01-24T08:00:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=fsm.PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
        preset_sha256=sha_a_f1,
        expected_preset_sha256=sha_a_f1,
        ops4_traffic_light="GREEN",
        static_dd_pct=2.0,
    )

    # --- E3: Funded Breach Postmortem Lock until signed OPS-6 classification ---
    e3_ledger = copy.deepcopy(clean_base_ledger)
    e3_ledger["accounts"].append(
        {
            "account_id": "FTMO-BREACH-99",
            "contract_id": "ftmo_standard_10k",
            "firm_id": "ftmo",
            "firm_profile": "FTMO_STANDARD",
            "capital_usd": 10_000.0,
            "state": fsm.FleetState.CLOSED_ARCHIVED.value,
            "last_transition_utc": "2027-02-02T12:00:00Z",
        }
    )
    e3_ledger["transitions"] = [
        {
            "account_id": "FTMO-BREACH-99",
            "from_state": fsm.FleetState.S5_FUNDED_ACTIVE.value,
            "to_state": fsm.FleetState.E3_FUNDED_BREACH_POSTMORTEM.value,
            "utc_ts": "2027-02-01T18:00:00Z",
        },
        {
            "account_id": "FTMO-BREACH-99",
            "from_state": fsm.FleetState.E3_FUNDED_BREACH_POSTMORTEM.value,
            "to_state": fsm.FleetState.CLOSED_ARCHIVED.value,
            "utc_ts": "2027-02-02T12:00:00Z",
        },
    ]
    v_e3_block = guards.evaluate_fleet_admission(
        e3_ledger, clean_proposed, clean_vps, now_utc=eval_now, contracts=contracts
    )
    _check(v_e3_block.allowed is False, "E3 must lock fleet even if breached account is archived")
    _check(guards.GUARD_E3 in v_e3_block.active_guards, "GUARD_E3 missing")
    _check("E3_FUNDED_BREACH_UNRESOLVED_POSTMORTEM" in v_e3_block.blocking_reasons, "Missing E3 block code")

    v_e3_unverified_bug = guards.evaluate_fleet_admission(
        e3_ledger,
        clean_proposed,
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
        ops6_postmortems=[
            {
                "account_id": "FTMO-BREACH-99",
                "classification": "BOT_BUG",
                "signed_by": "owner",
                "signed_utc": "2027-02-04T10:00:00Z",
                "report_sha256": _sha("OPS6-PM-BUG-UNVERIFIED"),
                "fix_verified": False,
            }
        ],
    )
    _check(v_e3_unverified_bug.allowed is False, "BOT_BUG without fix_verified=True must stay blocked")
    _check("E3_OPS6_BOT_BUG_FIX_UNVERIFIED" in v_e3_unverified_bug.blocking_reasons, "Missing BOT_BUG unverified code")

    e3_classes_verified: list[str] = []
    for cls_name in ("BOT_BUG", "SLIPPAGE", "VARIANCE"):
        pm_item: dict[str, Any] = {
            "account_id": "FTMO-BREACH-99",
            "classification": cls_name,
            "signed_by": "owner",
            "signed_utc": "2027-02-04T10:00:00Z",
            "report_sha256": _sha(f"OPS6-PM-{cls_name}"),
            "signed": True,
        }
        if cls_name == "BOT_BUG":
            pm_item["fix_verified"] = True
        v_cls = guards.evaluate_fleet_admission(
            e3_ledger,
            clean_proposed,
            clean_vps,
            now_utc=eval_now,
            contracts=contracts,
            ops6_postmortems=[pm_item],
        )
        _check(
            v_cls.allowed is True,
            f"Signed OPS-6 {cls_name} postmortem failed to unlock E3: {v_cls.blocking_reasons}",
        )
        e3_classes_verified.append(cls_name)

    # --- E4: FTMO 400K Active Base Funded Cap, 200K Single Challenge Cap & naqex-node1 VPS ---
    e4_cap_ledger = copy.deepcopy(clean_base_ledger)
    e4_cap_ledger["fleet_policy"]["max_accounts_per_firm"] = 5
    e4_cap_ledger["accounts"] = [
        {
            **clean_base_ledger["accounts"][0],
            "account_id": "FTMO-F-200A",
            "contract_id": "ftmo_standard_200k",
            "capital_usd": 200_000.0,
            "base_capital_usd": 200_000.0,
            "equity_usd": 204_000.0,
            "balance_usd": 204_000.0,
            "magic_range": [20262100, 20262199],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_200a",
        },
        {
            **clean_base_ledger["accounts"][0],
            "account_id": "FTMO-F-150B",
            "contract_id": "ftmo_standard_200k",
            "capital_usd": 150_000.0,
            "base_capital_usd": 150_000.0,
            "equity_usd": 152_000.0,
            "balance_usd": 152_000.0,
            "magic_range": [20262200, 20262299],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_150b",
        },
    ]
    v_e4_400k = guards.evaluate_fleet_admission(
        e4_cap_ledger,
        {
            **clean_proposed,
            "account_id": "FTMO-OVER-100K",
            "contract_id": "ftmo_standard_100k",
            "capital_usd": 100_000.0,
            "magic_range": [20262300, 20262399],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_over_100k",
        },
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_e4_400k.allowed is False, "350K + 100K = 450K must exceed FTMO 400K base Funded cap")
    _check("E4_FTMO_400K_FUNDED_CAP_EXCEEDED" in v_e4_400k.blocking_reasons, "Missing E4_FTMO_400K_FUNDED_CAP_EXCEEDED")

    v_e4_200k_single = guards.evaluate_fleet_admission(
        clean_base_ledger,
        {
            **clean_proposed,
            "account_id": "FTMO-OVER-200K-SINGLE",
            "contract_id": "ftmo_standard_200k",
            "capital_usd": 200_001.0,
        },
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_e4_200k_single.allowed is False, "Single FTMO challenge > 200K must block")
    _check(
        "E4_FTMO_SINGLE_CHALLENGE_200K_CAP_EXCEEDED" in v_e4_200k_single.blocking_reasons,
        "Missing E4_FTMO_SINGLE_CHALLENGE_200K_CAP_EXCEEDED",
    )

    v_e4_vn_unavail = guards.evaluate_fleet_admission(
        clean_base_ledger,
        {
            **clean_proposed,
            "account_id": "FTMO-SWING50K-VN",
            "contract_id": "ftmo_swing_50k",
            "capital_usd": 50_000.0,
        },
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_e4_vn_unavail.allowed is False, "Unavailable VN contract ftmo_swing_50k must block")
    _check("E4_CONTRACT_UNAVAILABLE_VN" in v_e4_vn_unavail.blocking_reasons, "Missing E4_CONTRACT_UNAVAILABLE_VN")

    v_e4_vps = guards.evaluate_fleet_admission(
        clean_base_ledger,
        clean_proposed,
        _healthy_vps(
            now_iso=eval_now,
            cpu_util_pct=78.0,
            free_ram_gb=1.6,
            disk_c_free_gb=14.0,
            active_mt5_terminals=6,
        ),
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_e4_vps.allowed is False, "naqex-node1 VPS overload must block")
    for code in (
        "E4_VPS_CPU_OVERFLOW",
        "E4_VPS_RAM_OVERFLOW",
        "E4_VPS_DISK_C_LOW",
        "E4_VPS_MAX_MT5_TERMINALS_EXCEEDED",
    ):
        _check(
            code in v_e4_vps.blocking_reasons,
            f"Missing VPS capacity block code {code}: {v_e4_vps.blocking_reasons}",
        )

    # --- E5: Same-Firm Opposite Hedge, Duplicate MagicNumber, Duplicate Portable Dir & E: Drive ---
    v_e5_hedge = guards.evaluate_fleet_admission(
        clean_base_ledger,
        clean_proposed,
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
        active_signals=[
            {
                "firm": "FTMO",
                "account_id": "FTMO-F1",
                "symbol": "US100",
                "direction": "BUY",
                "timestamp_utc": "2027-02-10T11:50:00Z",
            },
            {
                "firm": "FTMO",
                "account_id": "FTMO-NEXT-01",
                "symbol": "US100.cash",
                "direction": "SELL",
                "timestamp_utc": "2027-02-10T11:55:00Z",
            },
        ],
    )
    _check(v_e5_hedge.allowed is False, "Same-firm opposite hedge (US100 vs US100.cash) must block")
    _check("E5_SAME_FIRM_OPPOSITE_HEDGE" in v_e5_hedge.blocking_reasons, "Missing E5_SAME_FIRM_OPPOSITE_HEDGE")

    v_e5_cross_firm_ok = guards.evaluate_fleet_admission(
        clean_base_ledger,
        clean_proposed,
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
        active_signals=[
            {
                "firm": "FTMO",
                "account_id": "FTMO-F1",
                "symbol": "US100",
                "direction": "BUY",
                "timestamp_utc": "2027-02-10T11:50:00Z",
            },
            {
                "firm": "THE5ERS",
                "account_id": "THE5ERS-01",
                "symbol": "US100.cash",
                "direction": "SELL",
                "timestamp_utc": "2027-02-10T11:55:00Z",
            },
        ],
    )
    _check(v_e5_cross_firm_ok.allowed is True, "Cross-firm opposite direction should NOT trigger same-firm hedge block")

    v_e5_magic_dir = guards.evaluate_fleet_admission(
        clean_base_ledger,
        {
            **clean_proposed,
            "magic_number": 20261150,  # inside FTMO-F1 range [20261100, 20261199]
            "magic_range": [20261150, 20261250],  # overlaps FTMO-F1 range
            "mt5_portable_dir": "c:/naqex/mt5/ftmo_f1/",  # case/slash duplicate of C:\Naqex\mt5\ftmo_f1
        },
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_e5_magic_dir.allowed is False, "Duplicate MagicNumber range + duplicate Portable dir must block")
    _check("E5_MAGIC_RANGE_COLLISION" in v_e5_magic_dir.blocking_reasons, "Missing E5_MAGIC_RANGE_COLLISION")
    _check("E5_DUPLICATE_PORTABLE_DIR" in v_e5_magic_dir.blocking_reasons, "Missing E5_DUPLICATE_PORTABLE_DIR")

    v_e5_edrive = guards.evaluate_fleet_admission(
        clean_base_ledger,
        {**clean_proposed, "mt5_portable_dir": "E:\\Naqex\\mt5\\ftmo_broken_drive"},
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_e5_edrive.allowed is False, "Forbidden E: drive MT5 portable path must block")
    _check("E5_FORBIDDEN_PORTABLE_DRIVE_E" in v_e5_edrive.blocking_reasons, "Missing E5_FORBIDDEN_PORTABLE_DRIVE_E")

    # --- E6: Inactivity 21/27/30d, Stale Heartbeat, NTP >= 1000ms, PRESET_SHA256_DRIFT, Eval on Funded ---
    e6_21_ledger = copy.deepcopy(clean_base_ledger)
    e6_21_ledger["accounts"][0]["days_since_last_trade"] = 21.0
    v_e6_21 = guards.evaluate_fleet_admission(
        e6_21_ledger, clean_proposed, clean_vps, now_utc=eval_now, contracts=contracts
    )
    _check(v_e6_21.allowed is True, "21d inactivity should be WARNING, not hard BLOCK")
    _check("E6_INACTIVITY_21D_WARNING" in v_e6_21.warnings, "Missing E6_INACTIVITY_21D_WARNING")

    e6_27_ledger = copy.deepcopy(clean_base_ledger)
    e6_27_ledger["accounts"][0]["days_since_last_trade"] = 27.0
    v_e6_27 = guards.evaluate_fleet_admission(
        e6_27_ledger, clean_proposed, clean_vps, now_utc=eval_now, contracts=contracts
    )
    _check(v_e6_27.allowed is True, "27d inactivity should be URGENT warning before 30d lock")
    _check(v_e6_27.guard_results[guards.GUARD_E6].status == "URGENT", "Expected URGENT status at 27d")
    _check("E6_INACTIVITY_27D_URGENT" in v_e6_27.warnings, "Missing E6_INACTIVITY_27D_URGENT")

    e6_30_ledger = copy.deepcopy(clean_base_ledger)
    e6_30_ledger["accounts"][0]["days_since_last_trade"] = 30.0
    e6_30_ledger["accounts"][0]["preset_sha256"] = _sha("DRIFTED-LIVE-SET")
    v_e6_30_drift = guards.evaluate_fleet_admission(
        e6_30_ledger,
        clean_proposed,
        _healthy_vps(
            now_iso=eval_now,
            hb_utc_ts="2027-02-10T11:56:00Z",  # 240s > 180s stale
            flag_write_utc_ts="2027-02-10T11:58:00Z",  # hb < flag_write -> pre-flag stale!
            ntp_offset_ms=1000.0,
            open_positions=None,
        ),
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_e6_30_drift.allowed is False, "E6 combined 30d + drift + stale hb + NTP 1000ms must block")
    for code in (
        "E6_INACTIVITY_30D_LOCK",
        "PRESET_SHA256_DRIFT",
        "E6_HEARTBEAT_STALE",
        "E6_STALE_HEARTBEAT_PRE_FLAG_WRITE",
        "E6_HEARTBEAT_INVALID_OPEN_POSITIONS",
        "E6_NTP_OFFSET_EXCEEDED",
    ):
        _check(
            code in v_e6_30_drift.blocking_reasons,
            f"Missing E6 block code {code}: {v_e6_30_drift.blocking_reasons}",
        )

    # OPS-2 Funded composition block on Eval .set passed into evaluate_fleet_admission
    v_ops2_eval_on_funded = guards.evaluate_fleet_admission(
        clean_base_ledger,
        {
            **clean_proposed,
            "target_phase": "FUNDED",
            "preset_name": "FTMO_Std25K_P1_Sprint_4_5x.set",
            "preset_params": _eval_sprint_preset_params(),
        },
        clean_vps,
        now_utc=eval_now,
        contracts=contracts,
    )
    _check(v_ops2_eval_on_funded.allowed is False, "Eval preset params on Funded admission must block")
    _check("OPS2_PREFLIGHT" in v_ops2_eval_on_funded.active_guards, "Expected OPS2_PREFLIGHT active guard")

    # --- Simultaneous 6-Guard Aggregation Check (E1..E6 all active at once) ---
    all6_ledger = copy.deepcopy(e4_cap_ledger)
    all6_ledger["accounts"][0]["static_dd_pct"] = 6.2  # E2 RED
    all6_ledger["accounts"][0]["days_since_last_trade"] = 31.0  # E6 30d
    all6_ledger["accounts"][0]["preset_sha256"] = _sha("ALL6-DRIFT")  # E6 drift
    all6_ledger["transitions"] = [
        {
            "account_id": "FAIL-A",
            "to_state": fsm.FleetState.E1_EVAL_FAIL_COOLDOWN.value,
            "utc_ts": "2027-01-25T10:00:00Z",
        },
        {
            "account_id": "FAIL-B",
            "to_state": fsm.FleetState.E1_EVAL_FAIL_COOLDOWN.value,
            "utc_ts": "2027-02-02T10:00:00Z",
        },
        {
            "account_id": "BREACH-X",
            "to_state": fsm.FleetState.E3_FUNDED_BREACH_POSTMORTEM.value,
            "utc_ts": "2027-02-03T10:00:00Z",
        },
    ]
    v_all6 = guards.evaluate_fleet_admission(
        all6_ledger,
        {
            **clean_proposed,
            "account_id": "FTMO-ALL6-OVER",
            "contract_id": "ftmo_standard_100k",
            "capital_usd": 100_000.0,
            "magic_range": [20262150, 20262250],
            "mt5_portable_dir": "C:\\Naqex\\mt5\\ftmo_200a",
        },
        _healthy_vps(now_iso=eval_now, cpu_util_pct=85.0, ntp_offset_ms=1200.0),
        now_utc=eval_now,
        contracts=contracts,
        active_signals=[
            {"firm": "FTMO", "account_id": "FTMO-F-200A", "symbol": "EURUSD", "direction": "BUY"},
            {"firm": "FTMO", "account_id": "FTMO-ALL6-OVER", "symbol": "EURUSD", "direction": "SELL"},
        ],
    )
    _check(v_all6.allowed is False, "Simultaneous 6-guard drill must block")
    _check(
        set(guards.ALL_GUARD_IDS).issubset(set(v_all6.active_guards)),
        f"Not all E1..E6 fired: {v_all6.active_guards}",
    )
    v_all6_dict = v_all6.to_dict()
    _check(v_all6_dict["order_send_capable"] is False, "v_all6 must keep order_send_capable=False")
    _check(len(v_all6_dict["report_sha256"]) == 64, "v_all6 report_sha256 must be 64-hex")

    receipt: dict[str, Any] = {
        "schema_version": DRILL_RECEIPT_SCHEMA,
        "gate_id": "W4-G10",
        "worker": "w4-m2c-sim-runbook",
        "status": "PASS",
        "invariants": {
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_cutoff_date": fsm.HOLDOUT_CUTOFF_DATE,
            "holdout_rows_analysed": 0,
            "zero_mt5_imports": True,
            "zero_bare_asserts": True,
        },
        "lifecycle_drill": {
            "ledger_id": orch.ledger_id,
            "accounts_count": len(orch.accounts),
            "transitions_count": len(orch.transitions),
            "canonical_states_visited": sorted(s for s in visited_states if s in canonical_state_names),
            "all_8_canonical_states_covered": len(canonical_state_names) == 8
            and all(s in visited_states for s in canonical_state_names),
            "all_7_forward_transitions_covered": all(
                (a.value, b.value) in visited_edges for a, b in fsm.FORWARD_TRANSITIONS
            ),
            "s7_to_s0_recycle_covered": True,
            "s7_to_s5_recurring_cycle_covered": True,
            "gated_stagger_block_before_p1_pass_proven": True,
            "gated_stagger_upgrade_25k_and_50k_proven": True,
            "payout_cycle1_s7_3bucket_usd": alloc_c1["buckets_usd"],
            "payout_cycle1_fee_refund_usd": alloc_c1["cash_fee_refund_usd"],
            "ftmo_scaling_25pct_4m_proven": {
                "account_id": acct_a_scale.account_id,
                "eligible_at_90d": scaling_early.eligible,
                "eligible_at_127d": acct_a_scale.eligible,
                "increment_usd": acct_a_scale.increment_usd,
                "next_capital_usd": acct_a_scale.next_capital_usd,
                "next_payout_split_frac": acct_a_scale.next_payout_split_frac,
            },
            "s4_to_s5_dual_lock_blocks": {
                "eval_mode_rejected": s4_s5_eval_mode_code,
                "eval_filename_rejected": s4_s5_eval_filename_code,
                "eval_params_rejected": s4_s5_eval_params_code,
                "open_positions_nonzero_rejected": s4_s5_open_pos_code,
                "preset_sha256_drift_rejected": s4_s5_sha_drift_code,
            },
            "hash_chain_verified": True,
            "tamper_detection_verified": {
                "report_sha256_1byte_tamper_caught": tamper_report_caught,
                "event_hash_chain_tamper_caught": tamper_chain_caught,
            },
            "happy_ledger_report_sha256": happy_payload["report_sha256"],
            "fleet_summary": happy_payload["fleet_summary"],
            "treasury_snapshot_buckets_usd": {
                "house_money_usd": happy_payload["treasury_snapshot"]["house_money_usd"],
                "upgrade_challenge_usd": happy_payload["treasury_snapshot"]["upgrade_challenge_usd"],
                "own_book_usd": happy_payload["treasury_snapshot"]["own_book_usd"],
            },
        },
        "guards_e1_to_e6_matrix": {
            "E1_EVAL_FAIL_COOLDOWN": {
                "passed": True,
                "single_fail_watch_allowed": v_e1_single.allowed,
                "two_fails_30d_blocked": not v_e1_block.allowed,
                "stale_ops6_receipt_blocked": not v_e1_stale_rcpt.allowed,
                "signed_ops6_receipt_cleared": v_e1_cleared.allowed,
            },
            "E2_FUNDED_DD_FREEZE": {
                "passed": True,
                "amber_3_5pct_blocked": not v_e2_amber.allowed,
                "amber_scale_factor": v_e2_amber.fleet_scale_factor,
                "red_6_0pct_blocked": not v_e2_red.allowed,
                "red_scale_factor": v_e2_red.fleet_scale_factor,
                "fsm_e2_red_unfreeze_blocked_and_green_recovered": True,
            },
            "E3_FUNDED_BREACH_POSTMORTEM": {
                "passed": True,
                "archived_breach_still_locked": not v_e3_block.allowed,
                "unverified_bot_bug_still_locked": not v_e3_unverified_bug.allowed,
                "signed_classifications_verified": e3_classes_verified,
            },
            "E4_CAP_OR_VPS_OVERFLOW": {
                "passed": True,
                "ftmo_400k_funded_cap_blocked": not v_e4_400k.allowed,
                "ftmo_200k_single_challenge_cap_blocked": not v_e4_200k_single.allowed,
                "vn_unavailable_contract_blocked": not v_e4_vn_unavail.allowed,
                "vps_cpu_ram_disk_terminals_blocked": not v_e4_vps.allowed,
            },
            "E5_CROSS_ACCOUNT_OPPOSITE_HEDGE": {
                "passed": True,
                "same_firm_opposite_hedge_blocked": not v_e5_hedge.allowed,
                "cross_firm_opposite_allowed": v_e5_cross_firm_ok.allowed,
                "duplicate_magic_and_portable_dir_blocked": not v_e5_magic_dir.allowed,
                "forbidden_e_drive_blocked": not v_e5_edrive.allowed,
            },
            "E6_INACTIVITY_OR_FEED_STALE_LOCK": {
                "passed": True,
                "inactivity_21d_warning": "E6_INACTIVITY_21D_WARNING" in v_e6_21.warnings,
                "inactivity_27d_urgent": v_e6_27.guard_results[guards.GUARD_E6].status == "URGENT",
                "inactivity_30d_lock_blocked": "E6_INACTIVITY_30D_LOCK" in v_e6_30_drift.blocking_reasons,
                "stale_heartbeat_and_pre_flag_blocked": (
                    "E6_HEARTBEAT_STALE" in v_e6_30_drift.blocking_reasons
                    and "E6_STALE_HEARTBEAT_PRE_FLAG_WRITE" in v_e6_30_drift.blocking_reasons
                ),
                "ntp_1000ms_blocked": "E6_NTP_OFFSET_EXCEEDED" in v_e6_30_drift.blocking_reasons,
                "preset_sha256_drift_blocked": "PRESET_SHA256_DRIFT" in v_e6_30_drift.blocking_reasons,
                "eval_preset_on_funded_ops2_blocked": not v_ops2_eval_on_funded.allowed,
            },
            "simultaneous_all_6_guards_fired": sorted(v_all6.active_guards),
            "simultaneous_all_6_report_sha256": v_all6_dict["report_sha256"],
            "all_6_guards_proven": True,
        },
    }
    receipt["report_sha256"] = canonical_payload_sha256(receipt)
    return receipt


# ==============================================================================
# Pytest Test Cases (100% Offline CI-Safe + Local Receipt Verification)
# ==============================================================================
def test_e2e_drill_static_safety_invariants() -> None:
    src_path = Path(__file__).resolve()
    raw = src_path.read_bytes()
    _check(b"\r\n" not in raw, "CRLF detected in test_wave4_fleet_e2e_drill.py; must be LF-only")
    _check(not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM detected in test_wave4_fleet_e2e_drill.py")
    tree = ast.parse(raw.decode("utf-8"), filename=str(src_path))
    asserts = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    _check(len(asserts) == 0, f"[ARCH-02] Found {len(asserts)} bare assert statements")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(alias.name != "MetaTrader5", "Forbidden MetaTrader5 import")
        elif isinstance(node, ast.ImportFrom):
            _check((node.module or "").split(".")[0] != "MetaTrader5", "Forbidden MetaTrader5 from-import")


def test_e2e_multi_account_lifecycle_and_e1_to_e6_drill(tmp_path: Path) -> None:
    r1 = run_full_fleet_e2e_drill(scratch_dir=tmp_path)
    r2 = run_full_fleet_e2e_drill(scratch_dir=tmp_path)

    _check(r1["status"] == "PASS", "E2E drill status must be PASS")
    _check(r1["invariants"]["order_send_capable"] is False, "order_send_capable must be False")
    _check(r1["invariants"]["order_send_count"] == 0, "order_send_count must be 0")
    _check(r1["invariants"]["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(r1["lifecycle_drill"]["all_8_canonical_states_covered"] is True, "All 8 states S0..S7 must be covered")
    _check(r1["lifecycle_drill"]["all_7_forward_transitions_covered"] is True, "All 7 forward edges must be covered")
    _check(r1["lifecycle_drill"]["s7_to_s0_recycle_covered"] is True, "S7->S0 must be covered")
    _check(r1["guards_e1_to_e6_matrix"]["all_6_guards_proven"] is True, "All E1..E6 guards must be proven")
    _check(r1["report_sha256"] == r2["report_sha256"], "E2E drill receipt must be byte-for-byte deterministic")
    _check(r1["report_sha256"] == canonical_payload_sha256(r1), "report_sha256 canonical verification failed")


def test_operator_runbook_hygiene_and_contract() -> None:
    _check(RUNBOOK_PATH.is_file(), f"Missing operator runbook: {RUNBOOK_PATH}")
    raw = RUNBOOK_PATH.read_bytes()
    _check(len(raw) <= RUNBOOK_MAX_BYTES, f"Runbook exceeds 18 KB limit: {len(raw)} > {RUNBOOK_MAX_BYTES} bytes")
    _check(not raw.startswith(b"\xef\xbb\xbf"), "Runbook must have 0 UTF-8 BOM")
    _check(b"\r\n" not in raw, "Runbook must have 0 CRLF line endings")
    text = raw.decode("utf-8")
    _check("$" not in text, "Runbook MUST contain 0 dollar signs ($) anywhere (even in code blocks)!")

    # G12: Zero proactive prop-firm support contact nudges
    g12_patterns = (
        r"(?i)\bliên hệ\s+(?:support|hỗ trợ|ftmo|the5ers)",
        r"(?i)\bcontact\s+(?:support|ftmo|the5ers)",
        r"(?i)\bemail\s+(?:support|ftmo|the5ers)",
        r"(?i)\blive[\s-]?chat\b",
        r"(?i)\bnhắn\s+(?:support|hỗ trợ|ftmo|the5ers)",
        r"(?i)\bgửi\s+(?:mail|email|ticket)\s+(?:cho\s+)?(?:support|hỗ trợ|ftmo|the5ers)",
    )
    for pat in g12_patterns:
        _check(re.search(pat, text) is None, f"G12 prop-firm support nudge matched pattern {pat!r}")

    # OPSEC: zero concrete private LAN/Tailscale IPs or real local user paths
    _check(re.search(r"\b192\.168\.\d{1,3}\.\d{1,3}\b", text) is None, "Concrete LAN IP leaked in runbook")
    _check(
        re.search(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b", text) is None,
        "Concrete Tailscale CGNAT IP leaked in runbook",
    )
    win_user_re = r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<|YOUR_|user\b|username\b)[A-Za-z0-9._-]+"
    _check(
        re.search(win_user_re, text) is None,
        "Hardcoded Windows user profile path leaked in runbook",
    )

    # Required operational content anchors
    for token in (
        "S0_PRE_CHALLENGE",
        "S1_CHALLENGE_P1",
        "S2_PASS_P1_HANDOFF",
        "S3_CHALLENGE_P2",
        "S4_PASS_P2_TO_FUNDED_LOCK",
        "S5_FUNDED_ACTIVE",
        "S6_PAYOUT_AUDIT_AND_HARVEST",
        "S7_AFTER_PAYOUT_ALLOCATOR",
        "E1_EVAL_FAIL_COOLDOWN",
        "E2_FUNDED_DD_FREEZE",
        "E3_FUNDED_BREACH_POSTMORTEM",
        "E4_CAP_OR_VPS_OVERFLOW",
        "E5_CROSS_ACCOUNT_OPPOSITE_HEDGE",
        "E6_INACTIVITY_OR_FEED_STALE_LOCK",
        "OPS-2",
        "OPS-5",
        "OPS-6",
        "fleet_ledger.json",
        "morning_briefing.py",
        "?view=prop-fleet",
        "execution_capability: false",
        "400,000 USD",
    ):
        _check(token in text, f"Runbook missing required operational token: {token!r}")


@pytest.mark.local_cache
def test_persisted_e2e_drill_receipt_matches_canonical_sha256() -> None:
    _check(
        DEFAULT_DRILL_RECEIPT_PATH.is_file(),
        f"Persisted drill receipt not found: {DEFAULT_DRILL_RECEIPT_PATH}",
    )
    raw_bytes = DEFAULT_DRILL_RECEIPT_PATH.read_bytes()
    _check(b"\r\n" not in raw_bytes, "Drill receipt must be LF-only")
    _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "Drill receipt must have 0 BOM")
    data = json.loads(raw_bytes.decode("utf-8"))
    _check(data.get("schema_version") == DRILL_RECEIPT_SCHEMA, "Unexpected drill receipt schema_version")
    _check(data.get("status") == "PASS", "Drill receipt status must be PASS")
    _check(data["invariants"]["order_send_capable"] is False, "Receipt order_send_capable must be False")
    _check(data["invariants"]["order_send_count"] == 0, "Receipt order_send_count must be 0")
    _check(data["invariants"]["holdout_rows_analysed"] == 0, "Receipt holdout_rows_analysed must be 0")
    _check(
        data.get("report_sha256") == canonical_payload_sha256(data),
        "Persisted drill receipt report_sha256 mismatch!",
    )
    fresh = run_full_fleet_e2e_drill()
    _check(
        data["report_sha256"] == fresh["report_sha256"],
        "Persisted drill receipt is stale vs current deterministic E2E drill!",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run W4-G10 Multi-Account Fleet E2E Simulation Drill and emit canonical SHA-256 receipt."
    )
    parser.add_argument(
        "--write-receipt",
        type=Path,
        default=DEFAULT_DRILL_RECEIPT_PATH,
        help="Destination path for fleet_e2e_drill_receipt.json.",
    )
    args = parser.parse_args(argv)
    receipt = run_full_fleet_e2e_drill()
    write_info = write_atomic_sha256_json(args.write_receipt, receipt)
    out = {
        "status": receipt["status"],
        "receipt_path": str(args.write_receipt),
        "bytes": write_info["bytes"],
        "file_sha256": write_info["file_sha256"],
        "report_sha256": write_info["report_sha256"],
        "order_send_capable": False,
        "order_send_count": 0,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
