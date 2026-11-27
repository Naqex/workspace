"""Unit & Negative-Mutation Test Suite for Fleet Admission & Edge-Case Guards (`E1..E6`, `W4-G10`).

Covers `tooling/ai-engines/quant_factory/wave4/fleet_admission_and_edge_cases.py`:
  1. Static & runtime invariants: ZERO bare `assert` statements (`[ARCH-02]`), ZERO `MetaTrader5`
     imports, `ORDER_SEND_CAPABLE is False`, `ORDER_SEND_COUNT == 0`, `HOLDOUT_CUTOFF_DATE == "2024-12-31"`,
     `HOLDOUT_ROWS_ANALYSED == 0`, LF-only line endings, and fail-closed tamper detection.
  2. Sample fixture end-to-end PASS (both `PropFleetOrchestrator` & serialized JSON dict + CLI).
  3. Every guard `E1..E6` both PASS and FAIL-CLOSED at exact boundary values:
     - `E1`: `1` vs `2` failed evals in trailing 30d, `30d` vs `30d+1s` window edge, signed vs invalid OPS-6 receipt
     - `E2`: `3.49%` GREEN (`1.0x`) vs `3.50%` AMBER (`0.5x`) vs `5.99%` AMBER (`0.5x`) vs `6.00%` RED (`0.0x`)
     - `E3`: Funded breach lock (incl. archived breach) vs signed OPS-6 postmortem (`BOT_BUG | SLIPPAGE | VARIANCE`)
     - `E4`: FTMO `$400,000` vs `$400,001` Funded cap, `$200,000` vs `$200,001` single Challenge cap,
             VN-unavailable catalog contract, firm slot limits, and `naqex-node1` VPS CPU/RAM/Disk/MT5 limits
     - `E5`: same-firm opposite hedge (`US100` vs `US100.cash`), duplicate/overlapping `MagicNumber` ranges
             across accounts, duplicate MT5 Portable directory (case/slash normalized) & forbidden `E:` drive
     - `E6`: `20/21/27/30` inactivity days, stale heartbeat (`age > 180s` & `heartbeat.utc_ts < flag_write_utc_ts`),
             NTP `999 ms` / `-999 ms` vs `1000 ms` / `-1000 ms`, and `PRESET_SHA256_DRIFT`
  4. OPS-2 composition (`PreflightReport` + Funded 1.0x lock).
  5. Exhaustive `None` / `bool` / `NaN` / `Inf` poisoned input tests safe under `python -O`.
  6. FTMO Scaling Plan Tracker (`+25%` every `4m` if `>= +10%` net & `>= 2` payouts up to `$2,000,000 USD`).
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory.live_ops.account_phase_preflight import (  # noqa: E402
    DEFAULT_FTMO_SPECS_28,
    validate_account_deployment,
)
from quant_factory.wave4 import fleet_admission_and_edge_cases as guards  # noqa: E402
from quant_factory.wave4 import prop_lifecycle_orchestrator as fsm  # noqa: E402

NOW_ISO = "2026-11-27T12:00:00Z"
NOW_DT = datetime(2026, 11, 27, 12, 0, 0, tzinfo=UTC)


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def _healthy_vps(
    *,
    now_iso: str = NOW_ISO,
    cpu_util_pct: Any = 28.0,
    free_ram_gb: Any = 5.5,
    active_mt5_terminals: Any = 2,
    ntp_offset_ms: Any = 24.0,
    open_positions: Any = 0,
    hb_utc_ts: Any | None = None,
    flag_write_utc_ts: Any = None,
    disk_c_free_gb: Any = 65.0,
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
    return {
        "node_name": "naqex-node1",
        "cpu_util_pct": cpu_util_pct,
        "free_ram_gb": free_ram_gb,
        "disk_c_free_gb": disk_c_free_gb,
        "active_mt5_terminals": active_mt5_terminals,
        "ntp_offset_ms": ntp_offset_ms,
        "heartbeat": hb,
    }


def _clean_base_ledger() -> dict[str, Any]:
    """Minimal clean ledger with 1 healthy FTMO 10K Funded account."""
    sha_f1 = _sha("FTMO-F1-FUNDED-1X")
    return {
        "schema_version": fsm.FLEET_LEDGER_SCHEMA_VERSION,
        "ledger_id": "test-fleet-guards",
        "order_send_capable": False,
        "order_send_count": 0,
        "holdout_cutoff_date": guards.HOLDOUT_CUTOFF_DATE,
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
                "preset_sha256": sha_f1,
                "expected_preset_sha256": sha_f1,
                "ops2_preflight_pass": True,
                "ops4_traffic_light": "GREEN",
                "open_positions": 0,
                "equity_usd": 10_250.0,
                "balance_usd": 10_250.0,
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


def _clean_proposed_account(
    *,
    account_id: str = "FTMO-NEW-002",
    contract_id: str = "ftmo_standard_25k",
    capital_usd: Any = 25_000.0,
    magic_range: Any = (20261200, 20261299),
    mt5_portable_dir: Any = "C:\\Naqex\\mt5\\ftmo_new_002",
) -> dict[str, Any]:
    sha_p1 = _sha(f"{account_id}-p1-preset")
    return {
        "account_id": account_id,
        "contract_id": contract_id,
        "firm_id": "ftmo",
        "capital_usd": capital_usd,
        "state": fsm.FleetState.S0_PRE_CHALLENGE.value,
        "ops2_preflight_pass": True,
        "open_positions": 0,
        "days_since_last_trade": 0.0,
        "preset_sha256": sha_p1,
        "expected_preset_sha256": sha_p1,
        "magic_range": list(magic_range) if isinstance(magic_range, tuple) else magic_range,
        "mt5_portable_dir": mt5_portable_dir,
    }


# ==============================================================================
# 1. Static Safety, Architecture & Runtime Tamper Invariants
# ==============================================================================
def test_static_invariants_zero_asserts_zero_mt5_lf_only_and_safety_flags() -> None:
    src_path = AI_ENGINES_DIR / "quant_factory" / "wave4" / "fleet_admission_and_edge_cases.py"
    _check(src_path.is_file(), f"Missing {src_path}")
    raw_bytes = src_path.read_bytes()
    _check(b"\r\n" not in raw_bytes, f"CRLF detected in {src_path}; must be LF-only")
    src = raw_bytes.decode("utf-8")
    tree = ast.parse(src, filename=str(src_path))

    assert_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    _check(len(assert_nodes) == 0, f"[ARCH-02] Bare assert found in {src_path}: {len(assert_nodes)}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(alias.name != "MetaTrader5", "Forbidden MetaTrader5 import")
        elif isinstance(node, ast.ImportFrom):
            _check((node.module or "").split(".")[0] != "MetaTrader5", "Forbidden MetaTrader5 from-import")

    _check(guards.ORDER_SEND_CAPABLE is False, "ORDER_SEND_CAPABLE must be strictly False")
    _check(guards.ORDER_SEND_COUNT == 0, "ORDER_SEND_COUNT must be strictly 0")
    _check(guards.HOLDOUT_CUTOFF_DATE == "2024-12-31", "Holdout cutoff must remain 2024-12-31")
    _check(guards.HOLDOUT_ROWS_ANALYSED == 0, "HOLDOUT_ROWS_ANALYSED must be strictly 0")
    _check(len(guards.ALL_GUARD_IDS) == 6, f"Expected exactly 6 guards E1..E6, got {guards.ALL_GUARD_IDS}")


def test_order_send_capable_tamper_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = _clean_base_ledger()
    proposed = _clean_proposed_account()
    vps = _healthy_vps()

    # 1a. Payload tamper
    tampered = copy.deepcopy(ledger)
    tampered["order_send_capable"] = True
    with pytest.raises(guards.FleetGuardError) as exc_payload:
        guards.evaluate_fleet_admission(tampered, proposed, vps, NOW_ISO)
    _check(exc_payload.value.code == "ORDER_SEND_CAPABLE_TAMPER", f"Wrong code: {exc_payload.value.code}")

    # 1b. Verdict tamper
    with pytest.raises(guards.FleetGuardError) as exc_verdict:
        guards.AdmissionVerdict(
            allowed=True,
            active_guards=(),
            blocking_reasons=(),
            scaling_eligibility=guards.ScalingTrackerSummary(),
            order_send_capable=True,
        )
    _check(exc_verdict.value.code == "ORDER_SEND_CAPABLE_TAMPER", f"Wrong code: {exc_verdict.value.code}")

    # 1c. Runtime module constant tamper
    monkeypatch.setattr(guards, "ORDER_SEND_CAPABLE", True)
    with pytest.raises(guards.FleetGuardError) as exc_mod:
        guards.evaluate_fleet_admission(ledger, proposed, vps, NOW_ISO)
    _check(exc_mod.value.code == "ORDER_SEND_CAPABLE_TAMPER", f"Wrong code: {exc_mod.value.code}")


# ==============================================================================
# 2. Sample Fixture Composition (`PropFleetOrchestrator` + JSON + CLI)
# ==============================================================================
def test_sample_fleet_ledger_passes_all_6_guards_and_cli_roundtrip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    orch = fsm.build_sample_fleet_orchestrator()
    proposed = orch.accounts["FTMO-STD25K-004"]
    vps = _healthy_vps(now_iso="2026-11-27T08:01:00Z")

    verdict_orch = guards.evaluate_fleet_admission(orch, proposed, vps, "2026-11-27T08:01:00Z")
    _check(verdict_orch.allowed is True, f"Sample fixture should PASS, got {verdict_orch.blocking_reasons}")
    _check(verdict_orch.active_guards == (), f"Expected no active guards, got {verdict_orch.active_guards}")
    _check(verdict_orch.order_send_capable is False, "order_send_capable must be False")
    _check(verdict_orch.fleet_scale_factor == 1.0, f"Expected 1.0x scale, got {verdict_orch.fleet_scale_factor}")
    _check(set(verdict_orch.guard_results.keys()) == set(guards.ALL_GUARD_IDS), "All 6 guards must be evaluated")

    # Identical verdict from serialized dict
    verdict_dict = guards.evaluate_fleet_admission(orch.to_dict(), proposed.to_dict(), vps, "2026-11-27T08:01:00Z")
    _check(verdict_dict.allowed is True, f"Dict ledger should PASS, got {verdict_dict.blocking_reasons}")
    d_out = verdict_dict.to_dict()
    _check(len(str(d_out.get("report_sha256"))) == 64, "Missing canonical report_sha256")
    _check(d_out["order_send_capable"] is False, "Serialized order_send_capable must be False")

    # CLI test
    ledger_path = tmp_path / "sample_ledger.json"
    orch.save(ledger_path)
    rc = guards.main(["--ledger", str(ledger_path), "--now-utc", "2026-11-27T08:01:00Z"])
    _check(rc == 0, f"CLI returned {rc}, expected 0")
    cli_out = json.loads(capsys.readouterr().out)
    _check(cli_out["allowed"] is True, f"CLI output should be allowed=True: {cli_out}")


# ==============================================================================
# 3. E1_EVAL_FAIL_COOLDOWN (1 vs 2 fails in 30d + OPS-6 Forensic Receipt)
# ==============================================================================
def test_e1_eval_fail_cooldown_boundaries_and_ops6_receipt() -> None:
    e1_state = fsm.FleetState.E1_EVAL_FAIL_COOLDOWN.value

    # 1 fail inside 30d -> PASS (with watch warning)
    ledger_1 = _clean_base_ledger()
    ledger_1["transitions"] = [
        {"account_id": "EVAL-A", "to_state": e1_state, "utc_ts": "2026-11-10T10:00:00Z"},
    ]
    v1 = guards.evaluate_fleet_admission(ledger_1, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v1.allowed is True, f"1 fail in 30d must PASS, got {v1.blocking_reasons}")
    _check(guards.GUARD_E1 not in v1.active_guards, "E1 must not block on 1 fail")
    _check("E1_SINGLE_EVAL_FAIL_IN_30D_WATCH" in v1.warnings, "Expected 1-fail watch warning")

    # 1 fail at exact 30d boundary + 1 fail at 30d + 1s (aged out) -> count == 1 -> PASS
    ledger_edge_pass = _clean_base_ledger()
    ledger_edge_pass["transitions"] = [
        {"account_id": "EVAL-A", "to_state": e1_state, "utc_ts": "2026-10-28T12:00:00Z"},
        {"account_id": "EVAL-B", "to_state": e1_state, "utc_ts": "2026-10-28T11:59:59Z"},
    ]
    v_edge = guards.evaluate_fleet_admission(ledger_edge_pass, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v_edge.allowed is True, f"30d+1s old fail must age out (count=1), got {v_edge.blocking_reasons}")
    _check(v_edge.guard_results[guards.GUARD_E1].details["failed_evals_in_window"] == 1, "Expected exactly 1 in window")

    # 2 fails inside 30d (exact 30d boundary + recent) without OPS-6 receipt -> FAIL-CLOSED
    ledger_2 = _clean_base_ledger()
    ledger_2["transitions"] = [
        {"account_id": "EVAL-A", "to_state": e1_state, "utc_ts": "2026-10-28T12:00:00Z"},
        {"account_id": "EVAL-B", "to_state": e1_state, "utc_ts": "2026-11-20T15:00:00Z"},
    ]
    v2 = guards.evaluate_fleet_admission(ledger_2, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v2.allowed is False, "2 fails in 30d without OPS-6 receipt MUST block")
    _check(guards.GUARD_E1 in v2.active_guards, f"Expected E1 active, got {v2.active_guards}")
    _check("E1_EVAL_FAIL_COOLDOWN_BLOCKED" in v2.blocking_reasons, f"Missing E1 block reason: {v2.blocking_reasons}")
    _check("E1_OPS6_FORENSIC_RECEIPT_REQUIRED" in v2.blocking_reasons, "Missing OPS-6 receipt requirement")

    # Stale receipt (signed BEFORE latest fail) -> FAIL-CLOSED
    stale_receipt = {
        "receipt_id": "OPS6-E1-001",
        "signed_by": "owner",
        "signed_utc": "2026-11-19T12:00:00Z",
        "report_sha256": _sha("ops6-stale"),
        "approved_to_resume": True,
    }
    v2_stale = guards.evaluate_fleet_admission(
        ledger_2, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_eval_receipt=stale_receipt
    )
    _check(v2_stale.allowed is False, "Stale OPS-6 receipt predating latest fail MUST block")
    _check(
        "E1_OPS6_RECEIPT_STALE_PRE_FAILURE" in v2_stale.blocking_reasons,
        f"Wrong reasons: {v2_stale.blocking_reasons}",
    )

    # String-bool `"true"` receipt -> FAIL-CLOSED
    str_bool_receipt = dict(stale_receipt, signed_utc="2026-11-22T12:00:00Z", approved_to_resume="true")
    v2_str = guards.evaluate_fleet_admission(
        ledger_2, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_eval_receipt=str_bool_receipt
    )
    _check(v2_str.allowed is False, "String 'true' approved_to_resume MUST fail closed")

    # Valid signed OPS-6 forensic review receipt -> CLEARED (PASS)
    valid_receipt = {
        "receipt_id": "OPS6-E1-002",
        "signed_by": "owner",
        "signed_utc": "2026-11-22T12:00:00Z",
        "report_sha256": _sha("ops6-valid"),
        "approved_to_resume": True,
        "root_cause_class": "VARIANCE",
    }
    v2_ok = guards.evaluate_fleet_admission(
        ledger_2, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_eval_receipt=valid_receipt
    )
    _check(v2_ok.allowed is True, f"Valid signed OPS-6 receipt must clear E1, got {v2_ok.blocking_reasons}")
    _check(v2_ok.guard_results[guards.GUARD_E1].details["cleared_by_ops6_receipt"] is True, "Expected cleared flag")


# ==============================================================================
# 4. E2_FUNDED_DD_FREEZE (3.49% vs 3.50% Amber 0.5x vs 6.00% Red 0.0x)
# ==============================================================================
@pytest.mark.parametrize(
    ("static_dd", "expected_allowed", "expected_scale", "expected_regime"),
    [
        (3.49, True, 1.0, "GREEN"),
        (3.50, False, 0.5, "AMBER"),
        (5.99, False, 0.5, "AMBER"),
        (6.00, False, 0.0, "RED"),
    ],
)
def test_e2_funded_dd_freeze_exact_boundaries(
    static_dd: float,
    expected_allowed: bool,
    expected_scale: float,
    expected_regime: str,
) -> None:
    ledger = _clean_base_ledger()
    ledger["accounts"][0]["static_dd_pct"] = static_dd
    ledger["accounts"][0]["daily_dd_pct"] = 0.2

    verdict = guards.evaluate_fleet_admission(ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(verdict.allowed is expected_allowed, f"DD={static_dd}% expected allowed={expected_allowed}, got {verdict}")
    _check(
        verdict.fleet_scale_factor == expected_scale,
        f"DD={static_dd}% expected scale={expected_scale}, got {verdict.fleet_scale_factor}",
    )
    e2_det = verdict.guard_results[guards.GUARD_E2].details
    _check(e2_det["dd_regime"] == expected_regime, f"DD={static_dd}% expected regime={expected_regime}, got {e2_det}")
    if not expected_allowed:
        _check(guards.GUARD_E2 in verdict.active_guards, f"Expected E2 in active_guards for DD={static_dd}%")


def test_e2_ops4_traffic_light_amber_and_red_freeze_fleet() -> None:
    for light, exp_scale in (("AMBER", 0.5), ("RED", 0.0)):
        ledger = _clean_base_ledger()
        ledger["accounts"][0]["static_dd_pct"] = 1.0
        ledger["accounts"][0]["ops4_traffic_light"] = light
        v = guards.evaluate_fleet_admission(ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
        _check(v.allowed is False, f"OPS-4 {light} on S5 MUST freeze new challenge")
        _check(
            v.fleet_scale_factor == exp_scale,
            f"OPS-4 {light} expected scale={exp_scale}, got {v.fleet_scale_factor}",
        )


# ==============================================================================
# 5. E3_FUNDED_BREACH_POSTMORTEM (BOT_BUG | SLIPPAGE | VARIANCE)
# ==============================================================================
def test_e3_funded_breach_locks_fleet_until_signed_ops6_postmortem() -> None:
    # Breached Funded account even after CLOSED_ARCHIVED still requires signed OPS-6 postmortem!
    ledger = _clean_base_ledger()
    ledger["accounts"].append(
        {
            "account_id": "FTMO-BREACH-99",
            "contract_id": "ftmo_standard_10k",
            "firm_id": "ftmo",
            "capital_usd": 10_000.0,
            "state": fsm.FleetState.CLOSED_ARCHIVED.value,
            "last_transition_utc": "2026-11-15T10:00:00Z",
        }
    )
    ledger["transitions"] = [
        {
            "account_id": "FTMO-BREACH-99",
            "to_state": fsm.FleetState.E3_FUNDED_BREACH_POSTMORTEM.value,
            "utc_ts": "2026-11-14T18:00:00Z",
        }
    ]

    # Without postmortem -> BLOCK
    v_no_pm = guards.evaluate_fleet_admission(ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v_no_pm.allowed is False, "Unresolved Funded breach MUST lock entire fleet")
    _check(guards.GUARD_E3 in v_no_pm.active_guards, f"Expected E3 active: {v_no_pm.active_guards}")

    # Invalid classification ("MARKET_NOISE") -> BLOCK
    bad_cls_pm = [
        {
            "account_id": "FTMO-BREACH-99",
            "classification": "MARKET_NOISE",
            "signed_by": "owner",
            "signed_utc": "2026-11-16T10:00:00Z",
            "report_sha256": _sha("pm-bad-cls"),
        }
    ]
    v_bad_cls = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_postmortems=bad_cls_pm
    )
    _check(v_bad_cls.allowed is False, "Invalid postmortem classification MUST block")
    _check("E3_OPS6_POSTMORTEM_INVALID_CLASSIFICATION" in v_bad_cls.blocking_reasons, "Expected invalid class code")

    # BOT_BUG with fix_verified=False -> BLOCK
    unfixed_bug_pm = [
        {
            "account_id": "FTMO-BREACH-99",
            "classification": "BOT_BUG",
            "fix_verified": False,
            "signed_by": "owner",
            "signed_utc": "2026-11-16T10:00:00Z",
            "report_sha256": _sha("pm-unfixed"),
        }
    ]
    v_unfixed = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_postmortems=unfixed_bug_pm
    )
    _check(v_unfixed.allowed is False, "Unfixed BOT_BUG postmortem MUST block")
    _check("E3_OPS6_BOT_BUG_FIX_UNVERIFIED" in v_unfixed.blocking_reasons, "Expected unverified bug fix code")

    # Valid signed OPS-6 postmortem for each allowed class (BOT_BUG, SLIPPAGE, VARIANCE) -> PASS
    for valid_cls in ("BOT_BUG", "SLIPPAGE", "VARIANCE"):
        pm = [
            {
                "account_id": "FTMO-BREACH-99",
                "classification": valid_cls,
                "fix_verified": True,
                "signed_by": "owner",
                "signed_utc": "2026-11-16T10:00:00Z",
                "report_sha256": _sha(f"pm-{valid_cls}"),
            }
        ]
        v_ok = guards.evaluate_fleet_admission(
            ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_postmortems=pm
        )
        _check(
            v_ok.allowed is True,
            f"Valid signed {valid_cls} OPS-6 postmortem must unlock fleet: {v_ok.blocking_reasons}",
        )


# ==============================================================================
# 6. E4_CAP_OR_VPS_OVERFLOW ($400K/$200K Caps, Catalog Slots & naqex-node1 VPS)
# ==============================================================================
def test_e4_ftmo_400k_funded_cap_and_200k_single_challenge_boundaries() -> None:
    # Existing FTMO Funded = $200K + $100K = $300K; proposing $100K -> exact $400,000 PASS
    ledger = _clean_base_ledger()
    ledger["accounts"][0]["capital_usd"] = 200_000.0
    ledger["accounts"][0]["contract_id"] = "ftmo_standard_200k"
    acct_100k = copy.deepcopy(ledger["accounts"][0])
    acct_100k["account_id"] = "FTMO-F2"
    acct_100k["contract_id"] = "ftmo_standard_100k"
    acct_100k["capital_usd"] = 100_000.0
    acct_100k["magic_range"] = [20261200, 20261299]
    acct_100k["mt5_portable_dir"] = "C:\\Naqex\\mt5\\ftmo_f2"
    ledger["accounts"].append(acct_100k)

    prop_exact_400k = _clean_proposed_account(
        account_id="FTMO-P3",
        contract_id="ftmo_standard_100k",
        capital_usd=100_000.0,
        magic_range=(20261300, 20261399),
        mt5_portable_dir="C:\\Naqex\\mt5\\ftmo_p3",
    )
    v_400k = guards.evaluate_fleet_admission(ledger, prop_exact_400k, _healthy_vps(), NOW_ISO)
    _check(v_400k.allowed is True, f"Exact $400,000 FTMO cap must PASS, got {v_400k.blocking_reasons}")

    # $300,000 + $100,001 = $400,001 -> FAIL-CLOSED!
    prop_400k_1 = copy.deepcopy(prop_exact_400k)
    prop_400k_1["capital_usd"] = 100_001.0
    v_400k_1 = guards.evaluate_fleet_admission(ledger, prop_400k_1, _healthy_vps(), NOW_ISO)
    _check(v_400k_1.allowed is False, "$400,001 FTMO total MUST fail closed")
    _check(guards.GUARD_E4 in v_400k_1.active_guards, "Expected E4 active on $400,001")
    _check("E4_FTMO_400K_FUNDED_CAP_EXCEEDED" in v_400k_1.blocking_reasons, f"Wrong code: {v_400k_1.blocking_reasons}")

    # Single Challenge cap: $200,000 PASS vs $200,001 FAIL-CLOSED
    ledger_small = _clean_base_ledger()
    prop_200k = _clean_proposed_account(contract_id="ftmo_standard_200k", capital_usd=200_000.0)
    v_200k = guards.evaluate_fleet_admission(ledger_small, prop_200k, _healthy_vps(), NOW_ISO)
    _check(v_200k.allowed is True, f"$200,000 single FTMO Challenge must PASS, got {v_200k.blocking_reasons}")

    prop_200k_1 = _clean_proposed_account(contract_id="ftmo_standard_200k", capital_usd=200_001.0)
    v_200k_1 = guards.evaluate_fleet_admission(ledger_small, prop_200k_1, _healthy_vps(), NOW_ISO)
    _check(v_200k_1.allowed is False, "$200,001 single FTMO Challenge MUST fail closed")
    _check(
        "E4_FTMO_SINGLE_CHALLENGE_200K_CAP_EXCEEDED" in v_200k_1.blocking_reasons,
        f"Wrong code: {v_200k_1.blocking_reasons}",
    )


def test_e4_catalog_vn_availability_firm_slots_and_vps_capacity_boundaries() -> None:
    ledger = _clean_base_ledger()

    # Unavailable VN contract (`ftmo_swing_50k` has available_vn=False in SSOT firms_catalog.json)
    prop_unavail = _clean_proposed_account(contract_id="ftmo_swing_50k", capital_usd=50_000.0)
    v_vn = guards.evaluate_fleet_admission(ledger, prop_unavail, _healthy_vps(), NOW_ISO)
    _check(v_vn.allowed is False, "VN-unavailable contract MUST fail closed")
    _check("E4_CONTRACT_UNAVAILABLE_VN" in v_vn.blocking_reasons, f"Wrong code: {v_vn.blocking_reasons}")

    # Firm slot limit (`max_accounts_per_firm=1`, already 1 FTMO active -> block)
    ledger_slot = copy.deepcopy(ledger)
    ledger_slot["fleet_policy"]["max_accounts_per_firm"] = 1
    v_slot = guards.evaluate_fleet_admission(ledger_slot, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v_slot.allowed is False, "Exceeding max_accounts_per_firm MUST fail closed")
    _check("E4_FIRM_SLOT_LIMIT_EXCEEDED" in v_slot.blocking_reasons, f"Wrong code: {v_slot.blocking_reasons}")

    # VPS exact boundary PASS (CPU 75.0%, RAM 2.0 GB, Disk C 20.0 GB, 5 active + 1 = 6 <= 6)
    vps_edge_ok = _healthy_vps(cpu_util_pct=75.0, free_ram_gb=2.0, disk_c_free_gb=20.0, active_mt5_terminals=5)
    v_vps_ok = guards.evaluate_fleet_admission(ledger, _clean_proposed_account(), vps_edge_ok, NOW_ISO)
    _check(v_vps_ok.allowed is True, f"Exact VPS boundary must PASS, got {v_vps_ok.blocking_reasons}")

    # VPS CPU overflow (75.01%)
    v_cpu = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(cpu_util_pct=75.01), NOW_ISO
    )
    _check(v_cpu.allowed is False and "E4_VPS_CPU_OVERFLOW" in v_cpu.blocking_reasons, f"CPU overflow failed: {v_cpu}")

    # VPS RAM overflow (1.99 GB free)
    v_ram = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(free_ram_gb=1.99), NOW_ISO
    )
    _check(v_ram.allowed is False and "E4_VPS_RAM_OVERFLOW" in v_ram.blocking_reasons, f"RAM overflow failed: {v_ram}")

    # VPS Disk C low (19.99 GB free)
    v_disk = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(disk_c_free_gb=19.99), NOW_ISO
    )
    _check(
        v_disk.allowed is False and "E4_VPS_DISK_C_LOW" in v_disk.blocking_reasons,
        f"Disk C low check failed: {v_disk}",
    )

    # VPS Max MT5 terminals exceeded (6 active + 1 proposed = 7 > 6)
    v_terms = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(active_mt5_terminals=6), NOW_ISO
    )
    _check(
        v_terms.allowed is False and "E4_VPS_MAX_MT5_TERMINALS_EXCEEDED" in v_terms.blocking_reasons,
        f"Max terminals check failed: {v_terms}",
    )


# ==============================================================================
# 7. E5_CROSS_ACCOUNT_OPPOSITE_HEDGE (Opposite Hedge, Magic & Portable Dirs)
# ==============================================================================
def test_e5_opposite_hedge_magic_and_portable_dir_collisions() -> None:
    ledger = _clean_base_ledger()

    # 7a. Same-firm opposite directional exposure (US100 vs US100.cash canonical root match!) -> BLOCK
    opposite_signals = [
        {
            "firm": "FTMO_STANDARD",
            "account_id": "FTMO-F1",
            "symbol": "US100.cash",
            "direction": "BUY",
            "timestamp_utc": NOW_ISO,
        },
        {
            "firm": "FTMO_SWING",
            "account_id": "FTMO-NEW-002",
            "symbol": "US100",
            "direction": "SELL",
            "timestamp_utc": NOW_ISO,
        },
    ]
    v_hedge = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO, active_signals=opposite_signals
    )
    _check(v_hedge.allowed is False, "Same-firm opposite directional exposure MUST fail closed")
    _check(guards.GUARD_E5 in v_hedge.active_guards, "Expected E5 active")
    _check("E5_SAME_FIRM_OPPOSITE_HEDGE" in v_hedge.blocking_reasons, f"Wrong code: {v_hedge.blocking_reasons}")

    # 7b. Cross-firm opposite direction (FTMO BUY vs THE5ERS SELL) -> PASS
    cross_firm_signals = [
        {"firm": "FTMO", "account_id": "FTMO-F1", "symbol": "USDJPY", "direction": "BUY", "timestamp_utc": NOW_ISO},
        {
            "firm": "THE5ERS",
            "account_id": "THE5ERS-001",
            "symbol": "USDJPY",
            "direction": "SELL",
            "timestamp_utc": NOW_ISO,
        },
    ]
    v_cross = guards.evaluate_fleet_admission(
        ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO, active_signals=cross_firm_signals
    )
    _check(v_cross.allowed is True, f"Cross-firm opposite direction should PASS, got {v_cross.blocking_reasons}")

    # 7c. Overlapping MagicNumber range across accounts ([20261100, 20261199] vs [20261199, 20261250]) -> BLOCK
    prop_overlap_magic = _clean_proposed_account(magic_range=(20261199, 20261250))
    v_m_rng = guards.evaluate_fleet_admission(ledger, prop_overlap_magic, _healthy_vps(), NOW_ISO)
    _check(v_m_rng.allowed is False, "Overlapping magic_range across accounts MUST fail closed")
    _check("E5_MAGIC_RANGE_COLLISION" in v_m_rng.blocking_reasons, f"Wrong code: {v_m_rng.blocking_reasons}")

    # 7d. Duplicate single MagicNumber across accounts AND magic falling inside another account's range -> BLOCK
    ledger_single_m = copy.deepcopy(ledger)
    ledger_single_m["accounts"][0]["magic_number"] = 20261122
    prop_dup_single = _clean_proposed_account(magic_range=(20261300, 20261399))
    prop_dup_single["magic_number"] = 20261122
    v_m_dup = guards.evaluate_fleet_admission(ledger_single_m, prop_dup_single, _healthy_vps(), NOW_ISO)
    _check(
        v_m_dup.allowed is False and "E5_DUPLICATE_MAGIC_NUMBER" in v_m_dup.blocking_reasons,
        f"Duplicate single magic failed: {v_m_dup}",
    )

    prop_in_rng = _clean_proposed_account(magic_range=None)
    prop_in_rng["magic_number"] = 20261122
    v_m_in = guards.evaluate_fleet_admission(ledger, prop_in_rng, _healthy_vps(), NOW_ISO)
    _check(v_m_in.allowed is False and "E5_MAGIC_RANGE_COLLISION" in v_m_in.blocking_reasons, f"Wrong code: {v_m_in}")

    # 7e. Duplicate MT5 Portable dir (case & slash normalized: `c:/naqex/mt5/FTMO_F1/`) -> BLOCK
    prop_dup_dir = _clean_proposed_account(mt5_portable_dir="c:/naqex/mt5/FTMO_F1/")
    v_dir = guards.evaluate_fleet_admission(ledger, prop_dup_dir, _healthy_vps(), NOW_ISO)
    _check(v_dir.allowed is False, "Duplicate MT5 Portable directory MUST fail closed")
    _check("E5_DUPLICATE_PORTABLE_DIR" in v_dir.blocking_reasons, f"Wrong code: {v_dir.blocking_reasons}")

    # 7f. Broken-latch E: drive MT5 Portable dir -> BLOCK
    prop_e_drive = _clean_proposed_account(mt5_portable_dir="E:\\Naqex\\mt5\\bad_term")
    v_e_drv = guards.evaluate_fleet_admission(ledger, prop_e_drive, _healthy_vps(), NOW_ISO)
    _check(
        v_e_drv.allowed is False and "E5_FORBIDDEN_PORTABLE_DRIVE_E" in v_e_drv.blocking_reasons,
        f"E: drive: {v_e_drv}",
    )


# ==============================================================================
# 8. E6_INACTIVITY_OR_FEED_STALE_LOCK (20/21/27/30d, Heartbeat, NTP, Preset SHA)
# ==============================================================================
@pytest.mark.parametrize(
    ("days_inactive", "expected_allowed", "expected_status", "expected_code"),
    [
        (20, True, "PASS", None),
        (21, True, "WARNING", "E6_INACTIVITY_21D_WARNING"),
        (27, True, "URGENT", "E6_INACTIVITY_27D_URGENT"),
        (30, False, "BLOCK", "E6_INACTIVITY_30D_LOCK"),
    ],
)
def test_e6_inactivity_exact_20_21_27_30_day_tiers(
    days_inactive: int,
    expected_allowed: bool,
    expected_status: str,
    expected_code: str | None,
) -> None:
    ledger = _clean_base_ledger()
    ledger["accounts"][0]["days_since_last_trade"] = days_inactive

    v = guards.evaluate_fleet_admission(ledger, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v.allowed is expected_allowed, f"inactivity={days_inactive}d expected allowed={expected_allowed}, got {v}")
    e6 = v.guard_results[guards.GUARD_E6]
    _check(
        e6.status == expected_status,
        f"inactivity={days_inactive}d expected status={expected_status}, got {e6.status}",
    )
    if expected_code is not None:
        all_codes = e6.blocking_reasons if not expected_allowed else e6.warnings
        _check(expected_code in all_codes, f"Expected {expected_code} in {all_codes}")


def test_e6_heartbeat_staleness_flag_ordering_ntp_and_preset_sha_drift() -> None:
    ledger = _clean_base_ledger()
    prop = _clean_proposed_account()

    # 8a. Heartbeat age 180s PASS vs 181s BLOCK
    v_180 = guards.evaluate_fleet_admission(
        ledger, prop, _healthy_vps(hb_utc_ts="2026-11-27T11:57:00Z"), NOW_ISO
    )
    _check(v_180.allowed is True, f"180s heartbeat age must PASS, got {v_180.blocking_reasons}")

    v_181 = guards.evaluate_fleet_admission(
        ledger, prop, _healthy_vps(hb_utc_ts="2026-11-27T11:56:59Z"), NOW_ISO
    )
    _check(v_181.allowed is False and "E6_HEARTBEAT_STALE" in v_181.blocking_reasons, f"181s must block: {v_181}")

    # 8b. Post-write ACK ordering: heartbeat.utc_ts < flag_write_utc_ts -> BLOCK; == -> PASS
    v_pre_flag = guards.evaluate_fleet_admission(
        ledger,
        prop,
        _healthy_vps(hb_utc_ts="2026-11-27T11:59:50Z", flag_write_utc_ts="2026-11-27T11:59:51Z"),
        NOW_ISO,
    )
    _check(
        v_pre_flag.allowed is False and "E6_STALE_HEARTBEAT_PRE_FLAG_WRITE" in v_pre_flag.blocking_reasons,
        f"Pre-flag heartbeat MUST block: {v_pre_flag}",
    )

    v_eq_flag = guards.evaluate_fleet_admission(
        ledger,
        prop,
        _healthy_vps(hb_utc_ts="2026-11-27T11:59:51Z", flag_write_utc_ts="2026-11-27T11:59:51Z"),
        NOW_ISO,
    )
    _check(v_eq_flag.allowed is True, f"heartbeat == flag_write_utc_ts must PASS, got {v_eq_flag.blocking_reasons}")

    # 8c. NTP exact boundaries: 999 / -999 ms PASS vs 1000 / -1000 ms BLOCK
    for good_ntp in (0, 999, 999.0, -999.0):
        v_ok = guards.evaluate_fleet_admission(ledger, prop, _healthy_vps(ntp_offset_ms=good_ntp), NOW_ISO)
        _check(v_ok.allowed is True, f"NTP={good_ntp}ms must PASS, got {v_ok.blocking_reasons}")

    for bad_ntp in (1000, 1000.0, -1000.0, 1500.0):
        v_bad = guards.evaluate_fleet_admission(ledger, prop, _healthy_vps(ntp_offset_ms=bad_ntp), NOW_ISO)
        _check(
            v_bad.allowed is False and "E6_NTP_OFFSET_EXCEEDED" in v_bad.blocking_reasons,
            f"NTP={bad_ntp}ms MUST block: {v_bad}",
        )

    # 8d. PRESET_SHA256_DRIFT (1-char mismatch on active account AND on proposed account)
    drifted_ledger = copy.deepcopy(ledger)
    drifted_ledger["accounts"][0]["preset_sha256"] = _sha("TAMPERED-PRESET")
    v_drift_acct = guards.evaluate_fleet_admission(drifted_ledger, prop, _healthy_vps(), NOW_ISO)
    _check(
        v_drift_acct.allowed is False and "PRESET_SHA256_DRIFT" in v_drift_acct.blocking_reasons,
        f"Active account preset drift MUST block: {v_drift_acct}",
    )

    drifted_prop = copy.deepcopy(prop)
    drifted_prop["preset_sha256"] = _sha("WRONG-PROPOSED-SHA")
    v_drift_prop = guards.evaluate_fleet_admission(ledger, drifted_prop, _healthy_vps(), NOW_ISO)
    _check(
        v_drift_prop.allowed is False and "PRESET_SHA256_DRIFT" in v_drift_prop.blocking_reasons,
        f"Proposed account preset drift MUST block: {v_drift_prop}",
    )


# ==============================================================================
# 9. OPS-2 Composition Check (`PreflightReport` + Funded 1.0x Lock)
# ==============================================================================
def test_ops2_preflight_report_and_funded_1x_lock_composition() -> None:
    ledger = _clean_base_ledger()
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
    funded_preset = {
        "phase": "FUNDED",
        "InpContractSku": "FTMO_STD25K_FUNDED_1X",
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
    pass_rep = validate_account_deployment(
        expected_login=550099,
        actual_login=550099,
        expected_trade_mode="REAL",
        actual_trade_mode="REAL",
        firm_profile="FTMO_STANDARD",
        account_phase="FUNDED",
        preset=funded_preset,
        account_leverage=100,
        market_watch_symbols=mw_snap,
        required_symbols=["USDJPY"],
        strict_funded_1x=True,
    )
    _check(pass_rep.passed is True, f"OPS-2 pass report failed: {pass_rep.reject_codes}")

    prop_ok = _clean_proposed_account()
    prop_ok["target_phase"] = "FUNDED"
    prop_ok["ops2_report"] = pass_rep
    prop_ok["preset_params"] = funded_preset
    v_ok = guards.evaluate_fleet_admission(ledger, prop_ok, _healthy_vps(), NOW_ISO, require_ops2_pass=True)
    _check(v_ok.allowed is True, f"Valid OPS-2 Funded admission must PASS, got {v_ok.blocking_reasons}")

    # Inject Eval 4.5x Sprint preset into Funded admission -> OPS-2 rejects!
    prop_bad = copy.deepcopy(prop_ok)
    prop_bad["preset_params"] = dict(funded_preset, phase="EVAL", InpBasePhaseMult=4.5, InpTargetProfitPct=10.0)
    v_bad = guards.evaluate_fleet_admission(ledger, prop_bad, _healthy_vps(), NOW_ISO, require_ops2_pass=True)
    _check(v_bad.allowed is False and "EVAL_PRESET_ON_FUNDED_ACCOUNT" in v_bad.blocking_reasons, f"Bad OPS-2: {v_bad}")


# ==============================================================================
# 10. Poisoned Inputs (`None`, `bool`, `NaN`, `Inf`) Under `python -O`
# ==============================================================================
@pytest.mark.parametrize("bad_val", [None, True, False, float("nan"), float("inf"), float("-inf"), -1, 0.0])
def test_poisoned_open_positions_fail_closed_under_python_O(bad_val: Any) -> None:
    ledger = _clean_base_ledger()
    prop = _clean_proposed_account()

    # Heartbeat open_positions poisoned (`None` vs `0`!)
    v_hb = guards.evaluate_fleet_admission(ledger, prop, _healthy_vps(open_positions=bad_val), NOW_ISO)
    _check(v_hb.allowed is False, f"Heartbeat open_positions={bad_val!r} MUST fail closed")
    _check("E6_HEARTBEAT_INVALID_OPEN_POSITIONS" in v_hb.blocking_reasons, f"Wrong code: {v_hb.blocking_reasons}")

    # Proposed account open_positions poisoned
    bad_prop = copy.deepcopy(prop)
    bad_prop["open_positions"] = bad_val
    v_p = guards.evaluate_fleet_admission(ledger, bad_prop, _healthy_vps(), NOW_ISO)
    _check(v_p.allowed is False, f"Proposed open_positions={bad_val!r} MUST fail closed")
    _check("E6_INVALID_OPEN_POSITIONS" in v_p.blocking_reasons, f"Wrong code: {v_p.blocking_reasons}")


@pytest.mark.parametrize("poison", [None, True, False, float("nan"), float("inf"), float("-inf")])
def test_poisoned_heartbeat_ntp_dd_vps_inactivity_and_capital_fail_closed(poison: Any) -> None:
    base_ledger = _clean_base_ledger()
    base_prop = _clean_proposed_account()
    base_vps = _healthy_vps()

    # Missing/None heartbeat
    vps_no_hb = copy.deepcopy(base_vps)
    vps_no_hb["heartbeat"] = None
    v_no_hb = guards.evaluate_fleet_admission(base_ledger, base_prop, vps_no_hb, NOW_ISO)
    _check(v_no_hb.allowed is False and "E6_HEARTBEAT_MISSING" in v_no_hb.blocking_reasons, "None heartbeat must fail")

    # Poisoned NTP
    v_ntp = guards.evaluate_fleet_admission(base_ledger, base_prop, _healthy_vps(ntp_offset_ms=poison), NOW_ISO)
    _check(v_ntp.allowed is False and "E6_POISONED_OR_MISSING_NTP_OFFSET" in v_ntp.blocking_reasons, f"NTP={poison!r}")

    # Poisoned Funded DD
    dd_ledger = copy.deepcopy(base_ledger)
    dd_ledger["accounts"][0]["static_dd_pct"] = poison
    v_dd = guards.evaluate_fleet_admission(dd_ledger, base_prop, base_vps, NOW_ISO)
    _check(v_dd.allowed is False and "E2_POISONED_FUNDED_DD_INPUT" in v_dd.blocking_reasons, f"DD={poison!r}")
    _check(v_dd.fleet_scale_factor == 0.0, "Poisoned DD must emit 0.0x scale factor")

    # Poisoned VPS CPU / RAM / terminals
    v_cpu = guards.evaluate_fleet_admission(base_ledger, base_prop, _healthy_vps(cpu_util_pct=poison), NOW_ISO)
    _check(v_cpu.allowed is False and "E4_POISONED_OR_MISSING_VPS_CPU" in v_cpu.blocking_reasons, f"CPU={poison!r}")

    v_ram = guards.evaluate_fleet_admission(base_ledger, base_prop, _healthy_vps(free_ram_gb=poison), NOW_ISO)
    _check(v_ram.allowed is False and "E4_POISONED_OR_MISSING_VPS_RAM" in v_ram.blocking_reasons, f"RAM={poison!r}")

    v_term = guards.evaluate_fleet_admission(base_ledger, base_prop, _healthy_vps(active_mt5_terminals=poison), NOW_ISO)
    _check(
        v_term.allowed is False and "E4_POISONED_OR_MISSING_VPS_MT5_TERMINALS" in v_term.blocking_reasons,
        f"terms={poison!r}",
    )

    # Poisoned inactivity days
    inact_ledger = copy.deepcopy(base_ledger)
    inact_ledger["accounts"][0]["days_since_last_trade"] = poison
    v_in = guards.evaluate_fleet_admission(inact_ledger, base_prop, base_vps, NOW_ISO)
    _check(v_in.allowed is False and "E6_POISONED_INACTIVITY_DAYS" in v_in.blocking_reasons, f"inact={poison!r}")

    # Poisoned proposed capital_usd
    if poison is not None:
        bad_cap_prop = copy.deepcopy(base_prop)
        bad_cap_prop["capital_usd"] = poison
        v_cap = guards.evaluate_fleet_admission(base_ledger, bad_cap_prop, base_vps, NOW_ISO)
        _check(
            v_cap.allowed is False and "E4_POISONED_PROPOSED_CAPITAL_USD" in v_cap.blocking_reasons,
            f"cap={poison!r}",
        )


def test_poisoned_now_utc_fails_closed() -> None:
    ledger = _clean_base_ledger()
    prop = _clean_proposed_account()
    vps = _healthy_vps()
    for bad_now in (True, float("nan"), "not-a-timestamp", datetime(2026, 11, 27, 12, 0, 0)):
        v = guards.evaluate_fleet_admission(ledger, prop, vps, bad_now)  # type: ignore[arg-type]
        _check(v.allowed is False and "INVALID_NOW_UTC_FAIL_CLOSED" in v.blocking_reasons, f"now={bad_now!r} must fail")


# ==============================================================================
# 11. FTMO Scaling Plan Tracker (+25% / 4m if >= +10% net & >= 2 payouts up to 2M)
# ==============================================================================
def test_ftmo_scaling_plan_tracker_eligibility_and_2m_cap() -> None:
    base_funded = {
        "account_id": "FTMO-SCALE-01",
        "firm_id": "ftmo",
        "state": fsm.FleetState.S5_FUNDED_ACTIVE.value,
        "initial_capital_usd": 100_000.0,
        "capital_usd": 100_000.0,
        "balance_usd": 102_000.0,
        "equity_usd": 102_000.0,
        "payout_split_frac": 0.80,
        "scaling_window_days": 120.0,
        "scaling_net_profit_frac": 0.10,
        "payouts_since_last_scale": 2,
        "ops4_traffic_light": "GREEN",
    }

    # Exact threshold PASS -> +25% ($100K -> $125K) and split 80% -> 90%
    st_ok = guards.evaluate_ftmo_scaling_plan(base_funded, now_utc=NOW_ISO)
    _check(st_ok.eligible is True, f"Exact scaling threshold should be eligible: {st_ok}")
    _check(st_ok.increment_usd == 25_000.0, f"Expected +$25K step, got {st_ok.increment_usd}")
    _check(st_ok.next_capital_usd == 125_000.0, f"Expected $125K next capital, got {st_ok.next_capital_usd}")
    _check(st_ok.next_payout_split_frac == 0.90, f"Expected 90% split, got {st_ok.next_payout_split_frac}")

    # Miss 4 months (119d)
    st_days = guards.evaluate_ftmo_scaling_plan(dict(base_funded, scaling_window_days=119.0), now_utc=NOW_ISO)
    _check(st_days.eligible is False and "SCALING_WINDOW_LT_4_MONTHS" in st_days.missing_requirements, f"{st_days}")

    # Miss +10% profit (9.99%)
    st_prof = guards.evaluate_ftmo_scaling_plan(dict(base_funded, scaling_net_profit_frac=0.0999), now_utc=NOW_ISO)
    _check(st_prof.eligible is False and "SCALING_PROFIT_LT_10_PCT" in st_prof.missing_requirements, f"{st_prof}")

    # Miss 2 payouts (1 payout)
    st_pay = guards.evaluate_ftmo_scaling_plan(dict(base_funded, payouts_since_last_scale=1), now_utc=NOW_ISO)
    _check(st_pay.eligible is False and "SCALING_PAYOUTS_LT_2" in st_pay.missing_requirements, f"{st_pay}")

    # Clamped at $2,000,000 USD max cap ($1,950K + 25% of $400K = $2,050K -> clamped to $2,000K, increment $50K)
    near_cap = dict(
        base_funded,
        initial_capital_usd=400_000.0,
        capital_usd=1_950_000.0,
        balance_usd=1_960_000.0,
        equity_usd=1_960_000.0,
    )
    st_clamp = guards.evaluate_ftmo_scaling_plan(near_cap, now_utc=NOW_ISO)
    _check(st_clamp.eligible is True, f"Near-2M account should still scale up to 2M cap: {st_clamp}")
    _check(st_clamp.next_capital_usd == 2_000_000.0, f"Expected clamp at $2M, got {st_clamp.next_capital_usd}")
    _check(st_clamp.increment_usd == 50_000.0, f"Expected $50K clamped increment, got {st_clamp.increment_usd}")

    # Already at $2,000,000 USD -> at_max_cap=True, eligible=False
    at_cap = dict(near_cap, capital_usd=2_000_000.0, balance_usd=2_010_000.0, equity_usd=2_010_000.0)
    st_max = guards.evaluate_ftmo_scaling_plan(at_cap, now_utc=NOW_ISO)
    _check(st_max.eligible is False and st_max.at_max_cap is True, f"At $2M cap must not scale further: {st_max}")

    # Poisoned scaling input -> fail closed
    st_nan = guards.evaluate_ftmo_scaling_plan(dict(base_funded, scaling_net_profit_frac=float("nan")), now_utc=NOW_ISO)
    _check(st_nan.eligible is False and st_nan.status_reason == "SCALING_POISONED_PROGRESS_METRICS", f"{st_nan}")


# ==============================================================================
# 12. All 6 Guards Trigger Simultaneously Without Short-Circuiting
# ==============================================================================
def test_all_6_guards_reported_simultaneously_without_short_circuit() -> None:
    ledger = _clean_base_ledger()
    e1_st = fsm.FleetState.E1_EVAL_FAIL_COOLDOWN.value
    e3_st = fsm.FleetState.E3_FUNDED_BREACH_POSTMORTEM.value
    # E2: Funded account in Red DD (6.5%) + E6: 31d inactivity + Preset SHA drift
    ledger["accounts"][0]["static_dd_pct"] = 6.5
    ledger["accounts"][0]["days_since_last_trade"] = 31.0
    ledger["accounts"][0]["preset_sha256"] = _sha("DRIFTED")
    # E1: 2 eval fails in 30d + E3: 1 unresolved Funded breach
    ledger["transitions"] = [
        {"account_id": "E1-A", "to_state": e1_st, "utc_ts": "2026-11-10T10:00:00Z"},
        {"account_id": "E1-B", "to_state": e1_st, "utc_ts": "2026-11-20T10:00:00Z"},
        {"account_id": "E3-BREACH", "to_state": e3_st, "utc_ts": "2026-11-21T10:00:00Z"},
    ]
    # E4: $250K single FTMO Challenge + VPS CPU 90%
    # E5: Duplicate magic_range & portable_dir
    prop = _clean_proposed_account(
        contract_id="ftmo_standard_200k",
        capital_usd=250_000.0,
        magic_range=(20261150, 20261250),
        mt5_portable_dir="C:\\Naqex\\mt5\\ftmo_f1",
    )
    vps = _healthy_vps(cpu_util_pct=90.0, ntp_offset_ms=1200.0)

    v = guards.evaluate_fleet_admission(ledger, prop, vps, NOW_ISO)
    _check(v.allowed is False, "All-6-guards failure MUST deny admission")
    _check(v.active_guards == guards.ALL_GUARD_IDS, f"Expected all 6 guards active, got {v.active_guards}")
    _check(v.fleet_scale_factor == 0.0, "Expected 0.0x fleet scale factor under E2 RED")


def test_missing_vps_omitted_open_positions_heartbeat_drift_and_concurrency_modes() -> None:
    ledger = _clean_base_ledger()
    prop = _clean_proposed_account()

    # vps_telemetry=None fails closed on both E4 and E6
    v_none_vps = guards.evaluate_fleet_admission(ledger, prop, None, NOW_ISO)
    _check(v_none_vps.allowed is False, "vps_telemetry=None MUST fail closed")
    _check(guards.GUARD_E4 in v_none_vps.active_guards, "Expected E4 on None VPS")
    _check(guards.GUARD_E6 in v_none_vps.active_guards, "Expected E6 on None VPS")

    # Heartbeat with omitted open_positions key MUST fail closed (never coerce missing -> 0!)
    vps_omit = _healthy_vps()
    del vps_omit["heartbeat"]["open_positions"]
    v_omit = guards.evaluate_fleet_admission(ledger, prop, vps_omit, NOW_ISO)
    _check(
        v_omit.allowed is False and "E6_HEARTBEAT_INVALID_OPEN_POSITIONS" in v_omit.blocking_reasons,
        f"Omitted heartbeat open_positions MUST fail closed: {v_omit}",
    )

    # Heartbeat-level PRESET_SHA256_DRIFT
    vps_hb_drift = _healthy_vps()
    vps_hb_drift["heartbeat"]["preset_sha256"] = _sha("hb-obs")
    vps_hb_drift["heartbeat"]["expected_preset_sha256"] = _sha("hb-exp")
    v_hb_drift = guards.evaluate_fleet_admission(ledger, prop, vps_hb_drift, NOW_ISO)
    _check(
        v_hb_drift.allowed is False and "PRESET_SHA256_DRIFT" in v_hb_drift.blocking_reasons,
        f"Heartbeat preset SHA drift MUST fail closed: {v_hb_drift}",
    )

    # GATED_STAGGER precondition: active S1 eval with 0 accounts >= S2 blocks opening a 2nd eval
    eval_only_ledger = copy.deepcopy(ledger)
    eval_only_ledger["accounts"][0]["state"] = fsm.FleetState.S1_CHALLENGE_P1.value
    v_stagger = guards.evaluate_fleet_admission(eval_only_ledger, prop, _healthy_vps(), NOW_ISO)
    _check(
        v_stagger.allowed is False and "E4_GATED_STAGGER_PRECONDITION_UNMET" in v_stagger.blocking_reasons,
        f"GATED_STAGGER precondition failed: {v_stagger}",
    )

    # SINGLE_TICKET concurrency lock
    single_ledger = copy.deepcopy(eval_only_ledger)
    single_ledger["fleet_policy"]["concurrency_mode"] = "SINGLE_TICKET"
    v_single = guards.evaluate_fleet_admission(single_ledger, prop, _healthy_vps(), NOW_ISO)
    _check(
        v_single.allowed is False and "E4_SINGLE_TICKET_CONCURRENCY_LOCK" in v_single.blocking_reasons,
        f"SINGLE_TICKET lock failed: {v_single}",
    )


# ==============================================================================
# 13. Wave 4A-Fix Negative Mutations (E1/E3 BOT_BUG Omit, E2 S7, available_vn)
# ==============================================================================
def test_e1_and_e3_bot_bug_omitting_fix_verified_fail_closed() -> None:
    """Negative mutation: BOT_BUG receipt/postmortem omitting `fix_verified` MUST fail closed."""
    e1_state = fsm.FleetState.E1_EVAL_FAIL_COOLDOWN.value
    e3_state = fsm.FleetState.E3_FUNDED_BREACH_POSTMORTEM.value

    # (a) E1: 2 eval fails in 30d + signed BOT_BUG receipt OMITTING `fix_verified` -> FAIL_CLOSED
    ledger_e1 = _clean_base_ledger()
    ledger_e1["transitions"] = [
        {"account_id": "EVAL-A", "to_state": e1_state, "utc_ts": "2026-11-10T10:00:00Z"},
        {"account_id": "EVAL-B", "to_state": e1_state, "utc_ts": "2026-11-20T15:00:00Z"},
    ]
    e1_omit = {
        "receipt_id": "OPS6-E1-BOTBUG-OMIT",
        "signed_by": "owner",
        "signed_utc": "2026-11-22T12:00:00Z",
        "report_sha256": _sha("ops6-e1-botbug-omit"),
        "approved_to_resume": True,
        "root_cause_class": "BOT_BUG",
    }
    v_e1_omit = guards.evaluate_fleet_admission(
        ledger_e1, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_eval_receipt=e1_omit
    )
    _check(v_e1_omit.allowed is False, "E1 BOT_BUG omitting fix_verified MUST fail closed")
    _check(guards.GUARD_E1 in v_e1_omit.active_guards, f"Expected E1 active: {v_e1_omit.active_guards}")
    _check(
        "E1_OPS6_BOT_BUG_FIX_UNVERIFIED" in v_e1_omit.blocking_reasons,
        f"Expected E1_OPS6_BOT_BUG_FIX_UNVERIFIED, got {v_e1_omit.blocking_reasons}",
    )

    for bad_fix in (False, None, "true", 1):
        e1_bad = dict(e1_omit, fix_verified=bad_fix)
        v_bad = guards.evaluate_fleet_admission(
            ledger_e1, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_eval_receipt=e1_bad
        )
        _check(
            v_bad.allowed is False and "E1_OPS6_BOT_BUG_FIX_UNVERIFIED" in v_bad.blocking_reasons,
            f"E1 BOT_BUG fix_verified={bad_fix!r} MUST fail closed: {v_bad.blocking_reasons}",
        )

    e1_fixed = dict(e1_omit, fix_verified=True)
    v_e1_ok = guards.evaluate_fleet_admission(
        ledger_e1, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_eval_receipt=e1_fixed
    )
    _check(v_e1_ok.allowed is True, f"E1 BOT_BUG with strict fix_verified=True must PASS: {v_e1_ok.blocking_reasons}")

    # (b) E3: Funded breach + signed BOT_BUG postmortem OMITTING `fix_verified` -> FAIL_CLOSED
    ledger_e3 = _clean_base_ledger()
    ledger_e3["accounts"].append(
        {
            "account_id": "FTMO-BREACH-OMIT",
            "contract_id": "ftmo_standard_10k",
            "firm_id": "ftmo",
            "capital_usd": 10_000.0,
            "state": fsm.FleetState.CLOSED_ARCHIVED.value,
            "last_transition_utc": "2026-11-15T10:00:00Z",
        }
    )
    ledger_e3["transitions"] = [
        {"account_id": "FTMO-BREACH-OMIT", "to_state": e3_state, "utc_ts": "2026-11-14T18:00:00Z"}
    ]
    pm_omit = [
        {
            "account_id": "FTMO-BREACH-OMIT",
            "classification": "BOT_BUG",
            "signed_by": "owner",
            "signed_utc": "2026-11-16T10:00:00Z",
            "report_sha256": _sha("pm-botbug-omit"),
        }
    ]
    v_e3_omit = guards.evaluate_fleet_admission(
        ledger_e3, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_postmortems=pm_omit
    )
    _check(v_e3_omit.allowed is False, "E3 BOT_BUG omitting fix_verified MUST fail closed")
    _check(guards.GUARD_E3 in v_e3_omit.active_guards, f"Expected E3 active: {v_e3_omit.active_guards}")
    _check(
        "E3_OPS6_BOT_BUG_FIX_UNVERIFIED" in v_e3_omit.blocking_reasons,
        f"Expected E3_OPS6_BOT_BUG_FIX_UNVERIFIED, got {v_e3_omit.blocking_reasons}",
    )

    pm_str_true = [dict(pm_omit[0], fix_verified="true")]
    v_e3_str = guards.evaluate_fleet_admission(
        ledger_e3, _clean_proposed_account(), _healthy_vps(), NOW_ISO, ops6_postmortems=pm_str_true
    )
    _check(
        v_e3_str.allowed is False and "E3_OPS6_BOT_BUG_FIX_UNVERIFIED" in v_e3_str.blocking_reasons,
        f"E3 BOT_BUG fix_verified='true' MUST fail closed: {v_e3_str.blocking_reasons}",
    )


def test_e2_funded_dd_freeze_covers_s7_after_payout_allocator_and_available_vn_fail_closed() -> None:
    """Negative mutation: S7 Funded DD>=3.5%/OPS-4 RED blocks; from_dict defaults available_vn=False."""
    s7_state = fsm.FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value

    # Healthy S7 -> PASS
    ledger_s7_ok = _clean_base_ledger()
    ledger_s7_ok["accounts"][0]["state"] = s7_state
    ledger_s7_ok["accounts"][0]["static_dd_pct"] = 1.0
    ledger_s7_ok["accounts"][0]["ops4_traffic_light"] = "GREEN"
    v_ok = guards.evaluate_fleet_admission(ledger_s7_ok, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v_ok.allowed is True and v_ok.fleet_scale_factor == 1.0, f"Healthy S7 should PASS: {v_ok.blocking_reasons}")

    # S7 with static_dd_pct=3.50% -> AMBER 0.5x BLOCK
    ledger_s7_amber = copy.deepcopy(ledger_s7_ok)
    ledger_s7_amber["accounts"][0]["static_dd_pct"] = 3.50
    v_amber = guards.evaluate_fleet_admission(ledger_s7_amber, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v_amber.allowed is False, "S7 Funded with DD=3.50% MUST block under E2")
    _check(guards.GUARD_E2 in v_amber.active_guards, f"Expected E2 active on S7 Amber: {v_amber.active_guards}")
    _check(v_amber.fleet_scale_factor == 0.5, f"Expected 0.5x scale on S7 Amber, got {v_amber.fleet_scale_factor}")

    # S7 with static_dd_pct=6.50% -> RED 0.0x BLOCK
    ledger_s7_red_dd = copy.deepcopy(ledger_s7_ok)
    ledger_s7_red_dd["accounts"][0]["static_dd_pct"] = 6.50
    v_red_dd = guards.evaluate_fleet_admission(ledger_s7_red_dd, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v_red_dd.allowed is False, "S7 Funded with DD=6.50% MUST block under E2")
    _check(guards.GUARD_E2 in v_red_dd.active_guards, f"Expected E2 active on S7 Red DD: {v_red_dd.active_guards}")
    _check(v_red_dd.fleet_scale_factor == 0.0, f"Expected 0.0x scale on S7 Red DD, got {v_red_dd.fleet_scale_factor}")

    # S7 with OPS-4 RED traffic light (even with low DD=1.0%) -> RED 0.0x BLOCK
    ledger_s7_red_ops4 = copy.deepcopy(ledger_s7_ok)
    ledger_s7_red_ops4["accounts"][0]["ops4_traffic_light"] = "RED"
    v_red_ops4 = guards.evaluate_fleet_admission(ledger_s7_red_ops4, _clean_proposed_account(), _healthy_vps(), NOW_ISO)
    _check(v_red_ops4.allowed is False, "S7 Funded with OPS-4 RED MUST block under E2")
    _check(
        guards.GUARD_E2 in v_red_ops4.active_guards,
        f"Expected E2 active on S7 OPS-4 RED: {v_red_ops4.active_guards}",
    )
    _check(
        v_red_ops4.fleet_scale_factor == 0.0,
        f"Expected 0.0x scale on S7 OPS-4 RED, got {v_red_ops4.fleet_scale_factor}",
    )

    # FleetAccount.from_dict omitting `available_vn` defaults fail-closed to False
    acct_omitted = fsm.FleetAccount.from_dict(
        {
            "account_id": "FTMO-VN-OMIT-01",
            "contract_id": "ftmo_standard_10k",
            "firm_id": "ftmo",
            "firm_profile": "FTMO_STANDARD",
            "capital_usd": 10_000.0,
            "ticket_fee_usd": 155.0,
            "state": fsm.FleetState.S0_PRE_CHALLENGE.value,
        }
    )
    _check(acct_omitted.available_vn is False, "FleetAccount.from_dict omitting available_vn MUST default to False")
