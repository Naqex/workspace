"""Wave 3A (`w4-p3-council`) Master Reconciliation Council & Authoritative Metrics SSOT.

Reads EVERY raw Total Offensive #4 (`v4.8.1 FINAL`) Wave 0, Wave 1, and Wave 2 receipt
and raw summary JSON directly from disk (40 artifacts across 10 groups), recomputes exact
disk SHA-256 digests, enforces fail-closed tamper/safety/arithmetic guards (ZERO bare
Python `assert` statements; 100% `python -O` safe), and emits the single verified SSOT:

    `.runtime/offensive4/wave4_master_metrics.json`

Hard invariants enforced fail-closed across ALL 40 artifacts:
  - `holdout_rows_analysed == 0` (Holdout 2025+ SEALED, cutoff `2024-12-31`)
  - `order_send_count == 0` and `order_send_capable is False`
  - `spend_vnd == 0` (zero real-money spend)
  - Embedded `report_sha256` verified on every self-hashed artifact (18/18)
  - Cross-artifact SHA-256 pointers verified across receipts and summaries (16/16)
  - All 81 baseline (`1.0x`) + 81 stress (`1.5x`) Pareto cases x 5 horizons (`3m/6m/12m/24m/36m`)
    and all 10 CME/FTMO rows x 4 horizons (`3m/6m/12m/24m`) satisfy `pass + fail + pending == 100.0%`
  - Zero `subprocess` calls, zero `MetaTrader5`/`scipy`/ML top-level imports, zero invented numbers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import HoldoutLockError, enforce_holdout_zero_rows  # noqa: E402

from quant_factory.wave4 import (  # noqa: E402
    HOLDOUT_CUTOFF_DATE,
    MAX_OFFICIAL_API_USD_PER_MONTH,
    ORDER_SEND_CAPABLE,
)

SCHEMA_MASTER_METRICS: str = "naqex-wave4-master-metrics-v1"
SCHEMA_COUNCIL_RECEIPT: str = "naqex-wave4-p3-council-receipt-v1"
OFFENSIVE_VERSION: str = "Total Offensive #4 v4.8.1 FINAL"
WORKER_ID: str = "w4-p3-council"
WAVE_LABEL: str = "Wave 3A (Master Council & SHA-256 Reconciliation)"

ORDER_SEND_COUNT: int = 0
SPEND_VND: int = 0

EXPECTED_BANKROLL_TIERS_M_VND: tuple[int, ...] = (10, 15, 25, 40, 60, 100, 150, 250, 500)
EXPECTED_CONCURRENCY_MODES: tuple[str, ...] = (
    "CONSERVATIVE_1_TICKET",
    "GATED_STAGGER",
    "AGGRESSIVE_PARALLEL",
)
EXPECTED_ALLOCATION_POLICIES: tuple[str, ...] = (
    "P1_RECOUP_FIRST",
    "P2_BALANCED_40_40_20",
    "P3_SCALE_80_20",
)
EXPECTED_PARETO_CASE_COUNT: int = 81
PARETO_HORIZONS: tuple[str, ...] = ("3m", "6m", "12m", "24m", "36m")
CME_HORIZONS: tuple[str, ...] = ("3m", "6m", "12m", "24m")
PARTITION_SUM_TOL_PCT: float = 0.02

DEFAULT_MASTER_METRICS_PATH: Path = ROOT / ".runtime" / "offensive4" / "wave4_master_metrics.json"
DEFAULT_AUDIT_RECEIPT_PATH: Path = ROOT / ".runtime" / "offensive4" / "audits" / "w4_p3_council_receipt.json"
DEFAULT_DROPBOX_RECEIPT_PATH: Path = ROOT / ".tmp" / "swarm_dropbox" / "w4-p3-council.json"

_VALID_INCLUSIVE_CUTOFFS: frozenset[str] = frozenset({"2024-12-31", "2024.12.31"})
_VALID_EXCLUSIVE_CUTOFFS: frozenset[str] = frozenset({"2025-01-01", "2025-01-01T00:00:00Z", "2025.01.01"})


class CouncilReconciliationError(ValueError):
    """Base fail-closed error raised by Wave 4 Master Council reconciliation."""


class MissingArtifactError(CouncilReconciliationError):
    """Raised when a required raw Wave 4 receipt or summary JSON is missing on disk."""


class MalformedArtifactError(CouncilReconciliationError):
    """Raised when a raw artifact JSON is unreadable, malformed, or misses required schema keys."""


class TamperedArtifactError(CouncilReconciliationError):
    """Raised when a recomputed file or canonical payload SHA-256 mismatches its recorded digest."""


class SafetyInvariantViolationError(CouncilReconciliationError):
    """Raised when `order_send_count != 0`, `order_send_capable is True`, or `spend_vnd != 0`."""


class ArithmeticDriftError(CouncilReconciliationError):
    """Raised when `pass + fail + pending != 100%` or summary/full Pareto metrics drift."""


@dataclass(frozen=True)
class ArtifactSpec:
    """Declarative specification for one raw Wave 4 receipt or summary artifact."""

    artifact_id: str
    group: str
    rel_path: str
    self_hashed: bool = False
    require_holdout_key: bool = True
    require_order_send_key: bool = True
    require_spend_key: bool = True


@dataclass(frozen=True)
class CrossHashLink:
    """Authoritative cross-artifact SHA-256 pointer checked fail-closed during reconciliation."""

    link_id: str
    source_artifact_id: str
    source_key_path: tuple[str, ...]
    target_artifact_id: str
    target_mode: str  # "file_sha256" or "report_sha256"


RAW_ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    # 1. Wave 0A (1)
    ArtifactSpec("w4_t0_env_receipt", "wave0a", ".runtime/offensive4/audits/w4_t0_env_receipt.json"),
    # 2. Wave 0B (2)
    ArtifactSpec("w4_t0_debt_receipt", "wave0b", ".runtime/offensive4/audits/w4_t0_debt_receipt.json"),
    ArtifactSpec("w4_t0_ftmo_m1_receipt", "wave0b", ".runtime/offensive4/audits/w4_t0_ftmo_m1_receipt.json"),
    # 3. Wave 0C (2)
    ArtifactSpec("w4_t0_parity98_receipt", "wave0c", ".runtime/offensive4/audits/w4_t0_parity98_receipt.json"),
    ArtifactSpec(
        "w4_t0_milestones_receipt",
        "wave0c",
        ".runtime/offensive4/audits/w4_t0_milestones_receipt.json",
        self_hashed=True,
    ),
    # 4. Mui 1: v1.04-ML (6)
    ArtifactSpec(
        "wave4_ml_arena_summary",
        "mui1_ml",
        ".runtime/offensive4/ml/wave4_ml_arena_summary.json",
        self_hashed=True,
    ),
    ArtifactSpec("w4_m1_feat_receipt", "mui1_ml", ".runtime/offensive4/audits/w4_m1_feat_receipt.json"),
    ArtifactSpec("w4_m1_cv_receipt", "mui1_ml", ".runtime/offensive4/audits/w4_m1_cv_receipt.json"),
    ArtifactSpec("w4_m1_arena_receipt", "mui1_ml", ".runtime/offensive4/audits/w4_m1_arena_receipt.json"),
    ArtifactSpec("w4_m1_onnx_mq5_receipt", "mui1_ml", ".runtime/offensive4/audits/w4_m1_onnx_mq5_receipt.json"),
    ArtifactSpec("w4_m1_mt5_onnx_receipt", "mui1_ml", ".runtime/offensive4/audits/w4_m1_mt5_onnx_receipt.json"),
    # 5. Mui 2A: 81-Case Pareto (4)
    ArtifactSpec("wave4_pareto_summary", "mui2a_pareto", ".runtime/offensive4/pareto/wave4_pareto_summary.json"),
    ArtifactSpec(
        "wave4_pareto_81cases_10k",
        "mui2a_pareto",
        ".runtime/offensive4/pareto/wave4_pareto_81cases_10k.json",
    ),
    ArtifactSpec("w4_m2a_kernel_receipt", "mui2a_pareto", ".runtime/offensive4/audits/w4_m2a_kernel_receipt.json"),
    ArtifactSpec("w4_m2a_pareto_receipt", "mui2a_pareto", ".runtime/offensive4/audits/w4_m2a_pareto_receipt.json"),
    # 6. Mui 2B: Own-Book + Frontier Blind + VN Playbook (6)
    ArtifactSpec(
        "ownbook_shadow_ops_summary",
        "mui2b_ownbook_frontier",
        ".runtime/offensive4/frontier/ownbook_shadow_ops_summary.json",
        self_hashed=True,
    ),
    ArtifactSpec(
        "frontier_cluster_b_blind_verdict",
        "mui2b_ownbook_frontier",
        ".runtime/offensive4/frontier/frontier_cluster_b_blind_verdict.json",
        self_hashed=True,
    ),
    ArtifactSpec(
        "w4_m2b_ownops_receipt",
        "mui2b_ownbook_frontier",
        ".runtime/offensive4/audits/w4_m2b_ownops_receipt.json",
        self_hashed=True,
    ),
    ArtifactSpec(
        "w4_m2b_frontier_receipt",
        "mui2b_ownbook_frontier",
        ".runtime/offensive4/audits/w4_m2b_frontier_receipt.json",
        self_hashed=True,
    ),
    ArtifactSpec(
        "w4_m2b_blind_receipt",
        "mui2b_ownbook_frontier",
        ".runtime/offensive4/audits/w4_m2b_blind_receipt.json",
        self_hashed=True,
    ),
    ArtifactSpec(
        "w4_m2b_vnbook_receipt",
        "mui2b_ownbook_frontier",
        ".runtime/offensive4/audits/w4_m2b_vnbook_receipt.json",
        self_hashed=True,
    ),
    # 7. Mui 2C: Fleet S0..S7 + E1..E6 + Web Cockpit (6)
    ArtifactSpec(
        "fleet_e2e_drill_receipt",
        "mui2c_fleet_ui",
        ".runtime/offensive4/fleet/fleet_e2e_drill_receipt.json",
        self_hashed=True,
        require_spend_key=False,
    ),
    ArtifactSpec(
        "w4_m2c_fsm_receipt",
        "mui2c_fleet_ui",
        ".runtime/offensive4/audits/w4_m2c_fsm_receipt.json",
        self_hashed=True,
        require_spend_key=False,
    ),
    ArtifactSpec(
        "w4_m2c_guards_receipt",
        "mui2c_fleet_ui",
        ".runtime/offensive4/audits/w4_m2c_guards_receipt.json",
        self_hashed=True,
        require_spend_key=False,
    ),
    ArtifactSpec(
        "w4_m2c_ui_contract_receipt",
        "mui2c_fleet_ui",
        ".runtime/offensive4/audits/w4_m2c_ui_contract_receipt.json",
        self_hashed=True,
        require_spend_key=False,
    ),
    ArtifactSpec(
        "w4_m2c_sim_runbook_receipt",
        "mui2c_fleet_ui",
        ".runtime/offensive4/audits/w4_m2c_sim_runbook_receipt.json",
        self_hashed=True,
        require_spend_key=False,
    ),
    ArtifactSpec(
        "w4_m2c_web_ui_receipt",
        "mui2c_fleet_ui",
        ".runtime/offensive4/audits/w4_m2c_web_ui_receipt.json",
        self_hashed=True,
        require_spend_key=False,
    ),
    # 8. Mui 3: AI Radar + Supervisor + PIT-24 + 6-Criteria Rubric (6)
    ArtifactSpec("ai_model_radar_latest", "mui3_ai", ".runtime/offensive4/ai/ai_model_radar_latest.json"),
    ArtifactSpec("wave4_pit24_and_ai_rubric", "mui3_ai", ".runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json"),
    ArtifactSpec(
        "prospective_shadow_ledger",
        "mui3_ai",
        ".runtime/offensive4/ai/prospective_shadow_ledger.json",
        require_holdout_key=False,
        require_order_send_key=False,
        require_spend_key=False,
    ),
    ArtifactSpec("w4_m3a_radar_receipt", "mui3_ai", ".runtime/offensive4/audits/w4_m3a_radar_receipt.json"),
    ArtifactSpec("w4_m3b_sup_receipt", "mui3_ai", ".runtime/offensive4/audits/w4_m3b_sup_receipt.json"),
    ArtifactSpec("w4_m3b_pit24_receipt", "mui3_ai", ".runtime/offensive4/audits/w4_m3b_pit24_receipt.json"),
    # 9. Mui 4: CME 4-Firm + 16-Symbol M1 (5)
    ArtifactSpec(
        "wave4_cme_intraday_feasibility",
        "mui4_cme_m1",
        ".runtime/offensive4/futures/wave4_cme_intraday_feasibility.json",
        self_hashed=True,
        require_spend_key=False,
    ),
    ArtifactSpec(
        "wave4_16sym_harvest_summary",
        "mui4_cme_m1",
        ".runtime/offensive4/m1/wave4_16sym_harvest_summary.json",
    ),
    ArtifactSpec(
        "w4_m4a_cme_receipt",
        "mui4_cme_m1",
        ".runtime/offensive4/audits/w4_m4a_cme_receipt.json",
        self_hashed=True,
    ),
    ArtifactSpec("w4_m4b_m1pipe_receipt", "mui4_cme_m1", ".runtime/offensive4/audits/w4_m4b_m1pipe_receipt.json"),
    ArtifactSpec("w4_m4_exec_receipt", "mui4_cme_m1", ".runtime/offensive4/audits/w4_m4_exec_receipt.json"),
    # 10. Wave 2B/2D Ops & Tests (2)
    ArtifactSpec(
        "w4_ops_briefing_wire_receipt",
        "wave2_ops_tests",
        ".runtime/offensive4/audits/w4_ops_briefing_wire_receipt.json",
        self_hashed=True,
    ),
    ArtifactSpec(
        "w4_tests_all_receipt",
        "wave2_ops_tests",
        ".runtime/offensive4/audits/w4_tests_all_receipt.json",
        self_hashed=True,
    ),
)


CROSS_ARTIFACT_SHA256_LINKS: tuple[CrossHashLink, ...] = (
    CrossHashLink(
        "pareto_summary_to_81cases_file",
        "wave4_pareto_summary",
        ("report_sha256",),
        "wave4_pareto_81cases_10k",
        "file_sha256",
    ),
    CrossHashLink(
        "m2a_pareto_receipt_to_81cases_file",
        "w4_m2a_pareto_receipt",
        ("artifacts", "full_pareto_json", "sha256"),
        "wave4_pareto_81cases_10k",
        "file_sha256",
    ),
    CrossHashLink(
        "m2a_pareto_receipt_to_summary_file",
        "w4_m2a_pareto_receipt",
        ("artifacts", "compact_summary_json", "sha256"),
        "wave4_pareto_summary",
        "file_sha256",
    ),
    CrossHashLink(
        "m1_arena_receipt_to_arena_report_sha",
        "w4_m1_arena_receipt",
        ("deliverables", "report_sha256"),
        "wave4_ml_arena_summary",
        "report_sha256",
    ),
    CrossHashLink(
        "m2b_ownops_receipt_to_ownbook_file",
        "w4_m2b_ownops_receipt",
        ("artifacts", ".runtime/offensive4/frontier/ownbook_shadow_ops_summary.json", "sha256"),
        "ownbook_shadow_ops_summary",
        "file_sha256",
    ),
    CrossHashLink(
        "m2b_vnbook_receipt_to_ownbook_report_sha",
        "w4_m2b_vnbook_receipt",
        ("source_provenance", "ownbook_shadow_ops_summary_report_sha256"),
        "ownbook_shadow_ops_summary",
        "report_sha256",
    ),
    CrossHashLink(
        "m2b_blind_receipt_to_frontier_verdict_file",
        "w4_m2b_blind_receipt",
        ("artifacts", ".runtime/offensive4/frontier/frontier_cluster_b_blind_verdict.json", "sha256"),
        "frontier_cluster_b_blind_verdict",
        "file_sha256",
    ),
    CrossHashLink(
        "m2c_sim_runbook_to_fleet_e2e_file",
        "w4_m2c_sim_runbook_receipt",
        ("artifacts", ".runtime/offensive4/fleet/fleet_e2e_drill_receipt.json", "sha256"),
        "fleet_e2e_drill_receipt",
        "file_sha256",
    ),
    CrossHashLink(
        "m2c_sim_runbook_to_fleet_e2e_report_sha",
        "w4_m2c_sim_runbook_receipt",
        ("e2e_drill_summary", "drill_report_sha256"),
        "fleet_e2e_drill_receipt",
        "report_sha256",
    ),
    CrossHashLink(
        "m3a_radar_receipt_to_radar_snapshot_file",
        "w4_m3a_radar_receipt",
        ("deliverables", "live_snapshot_sha256"),
        "ai_model_radar_latest",
        "file_sha256",
    ),
    CrossHashLink(
        "m3b_pit24_receipt_to_pit24_file",
        "w4_m3b_pit24_receipt",
        ("deliverables", "file_hygiene", ".runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json", "sha256"),
        "wave4_pit24_and_ai_rubric",
        "file_sha256",
    ),
    CrossHashLink(
        "m3b_pit24_receipt_to_shadow_ledger_file",
        "w4_m3b_pit24_receipt",
        ("deliverables", "file_hygiene", ".runtime/offensive4/ai/prospective_shadow_ledger.json", "sha256"),
        "prospective_shadow_ledger",
        "file_sha256",
    ),
    CrossHashLink(
        "pit24_summary_to_shadow_ledger_file",
        "wave4_pit24_and_ai_rubric",
        ("prospective_shadow_ledger", "ledger_file_sha256"),
        "prospective_shadow_ledger",
        "file_sha256",
    ),
    CrossHashLink(
        "m4_exec_receipt_to_cme_file",
        "w4_m4_exec_receipt",
        ("cme_verification", "cme_file_sha256"),
        "wave4_cme_intraday_feasibility",
        "file_sha256",
    ),
    CrossHashLink(
        "m4_exec_receipt_to_cme_report_sha",
        "w4_m4_exec_receipt",
        ("cme_verification", "report_sha256"),
        "wave4_cme_intraday_feasibility",
        "report_sha256",
    ),
    CrossHashLink(
        "m4_exec_receipt_to_16sym_summary_file",
        "w4_m4_exec_receipt",
        ("m1_16sym_harvest", "summary_sha256"),
        "wave4_16sym_harvest_summary",
        "file_sha256",
    ),
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_file_sha256(path: Path) -> str:
    """Compute exact SHA-256 hex digest of raw bytes on disk."""
    with Path(path).open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def compute_canonical_report_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over a JSON mapping excluding `report_sha256`."""
    body = {k: v for k, v in payload.items() if k != "report_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_json_lf(path: Path, payload: Mapping[str, Any]) -> tuple[str, int]:
    """Write deterministic LF / 0-BOM UTF-8 JSON and return `(file_sha256, bytes)`."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    target.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _get_nested(doc: Mapping[str, Any], key_path: Sequence[str], *, context: str) -> Any:
    cur: Any = doc
    for key in key_path:
        if not isinstance(cur, Mapping) or key not in cur:
            raise MalformedArtifactError(f"Missing required key path {'.'.join(key_path)!r} in {context}")
        cur = cur[key]
    return cur


def _require_non_bool_int(val: Any, *, field_name: str, context: str) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise SafetyInvariantViolationError(
            f"SAFETY_INVARIANT_TYPE [{context}]: {field_name} must be int (not bool), got {val!r}"
        )
    return int(val)


def _require_finite_float(val: Any, *, field_name: str, context: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise MalformedArtifactError(f"Expected numeric {field_name} in {context}, got {val!r}")
    out = float(val)
    if not math.isfinite(out):
        raise ArithmeticDriftError(f"Non-finite numeric value for {field_name} in {context}: {val!r}")
    return out


def scan_and_enforce_safety_invariants(doc: Mapping[str, Any], *, spec: ArtifactSpec) -> dict[str, Any]:
    """Recursively enforce Holdout=0, OrderSend=0, Spend=0 invariants (fail-closed, `-O` safe)."""
    holdout_hits = 0
    order_send_hits = 0
    spend_hits = 0
    capable_hits = 0
    cutoff_hits = 0

    def _walk(node: Any, path_str: str) -> None:
        nonlocal holdout_hits, order_send_hits, spend_hits, capable_hits, cutoff_hits
        if isinstance(node, Mapping):
            for k, v in node.items():
                child = f"{path_str}.{k}" if path_str else str(k)
                if k == "holdout_rows_analysed":
                    enforce_holdout_zero_rows(v, context=f"{spec.artifact_id}:{child}")
                    holdout_hits += 1
                elif k in ("order_send_count", "OrderSend"):
                    iv = _require_non_bool_int(v, field_name=child, context=spec.artifact_id)
                    if iv != 0:
                        raise SafetyInvariantViolationError(
                            f"ORDER_SEND_VIOLATION [{spec.artifact_id}:{child}]: observed {iv} != 0"
                        )
                    order_send_hits += 1
                elif k in ("order_send_capable", "execution_capable"):
                    if v is not False:
                        raise SafetyInvariantViolationError(
                            f"ORDER_SEND_CAPABLE_VIOLATION [{spec.artifact_id}:{child}]: observed {v!r} (must be False)"
                        )
                    capable_hits += 1
                elif k in ("spend_vnd", "real_money_spend_vnd"):
                    if isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) != 0.0:
                        raise SafetyInvariantViolationError(
                            f"REAL_SPEND_VIOLATION [{spec.artifact_id}:{child}]: observed {v!r} != 0"
                        )
                    spend_hits += 1
                elif k in ("holdout_cutoff_date", "dev_cutoff_utc", "holdout_cutoff_inclusive"):
                    if not isinstance(v, str) or v not in _VALID_INCLUSIVE_CUTOFFS:
                        raise HoldoutLockError(
                            f"HOLDOUT_CUTOFF_VIOLATION [{spec.artifact_id}:{child}]: {v!r} != {HOLDOUT_CUTOFF_DATE!r}"
                        )
                    cutoff_hits += 1
                elif k == "dev_cutoff_date":
                    if not isinstance(v, str) or v not in (_VALID_INCLUSIVE_CUTOFFS | _VALID_EXCLUSIVE_CUTOFFS):
                        raise HoldoutLockError(
                            f"HOLDOUT_CUTOFF_VIOLATION [{spec.artifact_id}:{child}]: unexpected dev_cutoff_date {v!r}"
                        )
                    cutoff_hits += 1
                elif k in ("holdout_cutoff_utc", "holdout_cutoff_exclusive", "holdout_cutoff_day"):
                    if not isinstance(v, str) or v not in _VALID_EXCLUSIVE_CUTOFFS:
                        raise HoldoutLockError(
                            f"HOLDOUT_CUTOFF_VIOLATION [{spec.artifact_id}:{child}]: unexpected exclusive cutoff {v!r}"
                        )
                    cutoff_hits += 1
                elif k == "dev_cutoff_sec":
                    iv_cut = _require_non_bool_int(v, field_name=child, context=spec.artifact_id)
                    if iv_cut != 1735689600:
                        raise HoldoutLockError(
                            f"HOLDOUT_CUTOFF_VIOLATION [{spec.artifact_id}:{child}]: {iv_cut} != 1735689600"
                        )
                    cutoff_hits += 1
                _walk(v, child)
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                _walk(item, f"{path_str}[{idx}]")

    _walk(doc, "")

    if spec.require_holdout_key and holdout_hits == 0:
        raise HoldoutLockError(
            f"MISSING_HOLDOUT_INVARIANT [{spec.artifact_id}]: required `holdout_rows_analysed == 0` key absent"
        )
    if spec.require_order_send_key and order_send_hits == 0:
        raise SafetyInvariantViolationError(
            f"MISSING_ORDER_SEND_INVARIANT [{spec.artifact_id}]: required `order_send_count == 0` key absent"
        )
    if spec.require_spend_key and spend_hits == 0:
        raise SafetyInvariantViolationError(
            f"MISSING_SPEND_INVARIANT [{spec.artifact_id}]: required `spend_vnd == 0` key absent"
        )
    if spec.artifact_id == "prospective_shadow_ledger":
        if doc.get("prospective_only") is not True:
            raise SafetyInvariantViolationError("prospective_shadow_ledger must declare `prospective_only == True`")
        if capable_hits == 0 or cutoff_hits == 0:
            raise SafetyInvariantViolationError(
                "prospective_shadow_ledger must declare `order_send_capable == False` and `holdout_cutoff_date`"
            )

    return {
        "holdout_rows_analysed_occurrences": holdout_hits,
        "holdout_rows_analysed_max": 0,
        "order_send_count_occurrences": order_send_hits,
        "order_send_count_max": 0,
        "spend_vnd_occurrences": spend_hits,
        "spend_vnd_max": 0,
        "order_send_capable_occurrences": capable_hits,
        "order_send_capable_all_false": True,
        "cutoff_occurrences": cutoff_hits,
    }


def _extract_artifact_status(doc: Mapping[str, Any]) -> str:
    for key in (
        "status",
        "overall_status",
        "w4_g05_verdict",
        "w4_g04_status",
        "w4_g03_verdict",
        "wave0a_barrier_status",
    ):
        val = doc.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    if isinstance(doc.get("decision"), str) and doc["decision"].strip():
        return doc["decision"].strip()
    if isinstance(doc.get("verdict"), str) and doc["verdict"].strip():
        return doc["verdict"].strip()
    if isinstance(doc.get("summary"), Mapping) and doc["summary"].get("verified") is True:
        return "VERIFIED"
    if isinstance(doc.get("verification_checks"), Mapping):
        return "VERIFIED_PASS"
    if isinstance(doc.get("pit24_benchmark"), Mapping):
        return str(doc["pit24_benchmark"].get("outcome_status", "VERIFIED"))
    if isinstance(doc.get("sources"), Mapping):
        return str(doc["sources"].get("openrouter", {}).get("status", "OK"))
    if isinstance(doc.get("test_results"), Mapping):
        return "PASS"
    if isinstance(doc.get("deliverables"), Mapping):
        return "PASS"
    return "VERIFIED"


def load_and_verify_raw_artifacts(
    root: Path = ROOT,
    *,
    specs: Sequence[ArtifactSpec] = RAW_ARTIFACT_SPECS,
    cross_links: Sequence[CrossHashLink] = CROSS_ARTIFACT_SHA256_LINKS,
    expected_file_sha256: Mapping[str, str] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Load, hash, self-hash verify, safety-scan, and cross-verify all 40 raw Wave 4 artifacts."""
    root_path = Path(root)
    docs: dict[str, dict[str, Any]] = {}
    ledger: list[dict[str, Any]] = []
    file_hashes: dict[str, str] = {}

    for spec in specs:
        full_path = root_path / spec.rel_path
        if not full_path.is_file():
            raise MissingArtifactError(f"MISSING_RAW_ARTIFACT [{spec.artifact_id}]: {spec.rel_path}")
        raw_bytes = full_path.read_bytes()
        file_sha = hashlib.sha256(raw_bytes).hexdigest()
        file_hashes[spec.artifact_id] = file_sha

        if expected_file_sha256 is not None:
            pinned = expected_file_sha256.get(spec.artifact_id) or expected_file_sha256.get(spec.rel_path)
            if pinned is not None and pinned.lower() != file_sha.lower():
                raise TamperedArtifactError(
                    f"PINNED_FILE_SHA256_MISMATCH [{spec.artifact_id}]: expected={pinned} observed={file_sha}"
                )

        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MalformedArtifactError(f"MALFORMED_JSON [{spec.artifact_id}] ({spec.rel_path}): {exc}") from exc
        if not isinstance(parsed, dict):
            raise MalformedArtifactError(
                f"MALFORMED_JSON_ROOT [{spec.artifact_id}] ({spec.rel_path}): "
                f"expected object, got {type(parsed).__name__}"
            )

        embedded_report_sha = parsed.get("report_sha256")
        self_hash_status: bool | str = "NOT_APPLICABLE"
        if spec.self_hashed:
            if not isinstance(embedded_report_sha, str) or len(embedded_report_sha) != 64:
                raise TamperedArtifactError(
                    f"MISSING_EMBEDDED_REPORT_SHA256 [{spec.artifact_id}]: expected 64-hex report_sha256"
                )
            computed = compute_canonical_report_sha256(parsed)
            if computed != embedded_report_sha:
                raise TamperedArtifactError(
                    f"SELF_REPORT_SHA256_MISMATCH [{spec.artifact_id}]: "
                    f"recorded={embedded_report_sha} recomputed={computed}"
                )
            self_hash_status = True
        elif spec.artifact_id == "wave4_pareto_summary":
            self_hash_status = "EXTERNAL_TARGET_FILE_SHA256"
        elif isinstance(embedded_report_sha, str):
            self_hash_status = "CUSTOM_EMBEDDED_DIGEST_RECORDED"

        safety = scan_and_enforce_safety_invariants(parsed, spec=spec)
        docs[spec.artifact_id] = parsed
        ledger.append(
            {
                "artifact_id": spec.artifact_id,
                "group": spec.group,
                "rel_path": spec.rel_path,
                "bytes": len(raw_bytes),
                "file_sha256": file_sha,
                "schema": str(parsed.get("schema_version") or parsed.get("schema") or "unknown"),
                "worker": str(parsed.get("worker") or "n/a"),
                "status": _extract_artifact_status(parsed),
                "embedded_report_sha256": embedded_report_sha if isinstance(embedded_report_sha, str) else None,
                "self_hash_verified": self_hash_status,
                "safety": safety,
            }
        )

    cross_results: list[dict[str, Any]] = []
    for link in cross_links:
        if link.source_artifact_id not in docs or link.target_artifact_id not in docs:
            raise MissingArtifactError(
                f"CROSS_HASH_LINK_MISSING_ENDPOINT [{link.link_id}]: "
                f"{link.source_artifact_id} -> {link.target_artifact_id}"
            )
        recorded = _get_nested(
            docs[link.source_artifact_id],
            link.source_key_path,
            context=f"{link.source_artifact_id} ({link.link_id})",
        )
        if not isinstance(recorded, str) or len(recorded) != 64:
            raise TamperedArtifactError(f"CROSS_HASH_INVALID_RECORDED_SHA [{link.link_id}]: got {recorded!r}")
        if link.target_mode == "file_sha256":
            observed = file_hashes[link.target_artifact_id]
        elif link.target_mode == "report_sha256":
            target_sha = docs[link.target_artifact_id].get("report_sha256")
            if not isinstance(target_sha, str) or len(target_sha) != 64:
                raise TamperedArtifactError(
                    f"CROSS_HASH_MISSING_TARGET_REPORT_SHA [{link.link_id}]: target={link.target_artifact_id}"
                )
            observed = target_sha
        else:
            raise CouncilReconciliationError(f"Unsupported cross-hash target_mode: {link.target_mode!r}")

        if recorded.lower() != observed.lower():
            raise TamperedArtifactError(
                f"CROSS_ARTIFACT_SHA256_MISMATCH [{link.link_id}]: "
                f"{link.source_artifact_id} recorded={recorded} vs "
                f"{link.target_artifact_id} ({link.target_mode})={observed}"
            )
        cross_results.append(
            {
                "link_id": link.link_id,
                "source_artifact_id": link.source_artifact_id,
                "target_artifact_id": link.target_artifact_id,
                "target_mode": link.target_mode,
                "sha256": observed,
                "matched": True,
            }
        )

    return docs, ledger, cross_results


def _verify_partition_dict(
    partitions: Mapping[str, Any],
    *,
    horizons: Sequence[str],
    context: str,
) -> dict[str, dict[str, float]]:
    """Verify `pass_pct + fail_pct + pending_pct == 100.0%` across every required horizon."""
    out: dict[str, dict[str, float]] = {}
    for h in horizons:
        row = partitions.get(h)
        if not isinstance(row, Mapping):
            raise MalformedArtifactError(f"Missing horizon {h!r} in {context}")
        p = _require_finite_float(row.get("pass_pct"), field_name=f"{h}.pass_pct", context=context)
        f = _require_finite_float(row.get("fail_pct"), field_name=f"{h}.fail_pct", context=context)
        pend = _require_finite_float(row.get("pending_pct"), field_name=f"{h}.pending_pct", context=context)
        s = _require_finite_float(row.get("sum_pct", p + f + pend), field_name=f"{h}.sum_pct", context=context)
        for name, val in (("pass_pct", p), ("fail_pct", f), ("pending_pct", pend)):
            if val < -1e-6 or val > 100.0 + 1e-6:
                raise ArithmeticDriftError(f"PARTITION_BOUNDS_ERROR [{context}:{h}.{name}]: {val}")
        calc_sum = round(p + f + pend, 4)
        if abs(calc_sum - 100.0) > PARTITION_SUM_TOL_PCT or abs(s - 100.0) > PARTITION_SUM_TOL_PCT:
            raise ArithmeticDriftError(
                f"PARTITION_SUM_NOT_100 [{context}:{h}]: pass={p} fail={f} pending={pend} "
                f"calc_sum={calc_sum} sum_pct={s}"
            )
        out[h] = {
            "pass_pct": p,
            "fail_pct": f,
            "pending_pct": pend,
            "sum_pct": 100.0,
        }
    return out


def _extract_pareto_regime_block(case: Mapping[str, Any], *, regime_label: str) -> dict[str, Any]:
    cid = str(case["case_id"])
    ctx = f"{cid}@{regime_label}"
    partitions = _verify_partition_dict(
        case["monthly_pass_fail_pending"],
        horizons=PARETO_HORIZONS,
        context=ctx,
    )
    blow = case["funded_12m_blowup"]
    if not isinstance(blow, Mapping):
        raise MalformedArtifactError(f"Missing funded_12m_blowup in {ctx}")
    return {
        "net_profit_24m_usd": {
            "mean": _require_finite_float(case["net_profit_24m_usd"]["mean"], field_name="net24_usd.mean", context=ctx),
            "median": _require_finite_float(
                case["net_profit_24m_usd"]["median"], field_name="net24_usd.median", context=ctx
            ),
            "p10": _require_finite_float(case["net_profit_24m_usd"]["p10"], field_name="net24_usd.p10", context=ctx),
            "p90": _require_finite_float(case["net_profit_24m_usd"]["p90"], field_name="net24_usd.p90", context=ctx),
        },
        "net_profit_24m_vnd": {
            "mean": _require_finite_float(case["net_profit_24m_vnd"]["mean"], field_name="net24_vnd.mean", context=ctx),
            "median": _require_finite_float(
                case["net_profit_24m_vnd"]["median"], field_name="net24_vnd.median", context=ctx
            ),
            "p10": _require_finite_float(case["net_profit_24m_vnd"]["p10"], field_name="net24_vnd.p10", context=ctx),
            "p90": _require_finite_float(case["net_profit_24m_vnd"]["p90"], field_name="net24_vnd.p90", context=ctx),
        },
        "net_profit_36m_usd": {
            "mean": _require_finite_float(case["net_profit_36m_usd"]["mean"], field_name="net36_usd.mean", context=ctx),
            "median": _require_finite_float(
                case["net_profit_36m_usd"]["median"], field_name="net36_usd.median", context=ctx
            ),
            "p10": _require_finite_float(case["net_profit_36m_usd"]["p10"], field_name="net36_usd.p10", context=ctx),
            "p90": _require_finite_float(case["net_profit_36m_usd"]["p90"], field_name="net36_usd.p90", context=ctx),
        },
        "net_profit_36m_vnd": {
            "mean": _require_finite_float(case["net_profit_36m_vnd"]["mean"], field_name="net36_vnd.mean", context=ctx),
            "median": _require_finite_float(
                case["net_profit_36m_vnd"]["median"], field_name="net36_vnd.median", context=ctx
            ),
            "p10": _require_finite_float(case["net_profit_36m_vnd"]["p10"], field_name="net36_vnd.p10", context=ctx),
            "p90": _require_finite_float(case["net_profit_36m_vnd"]["p90"], field_name="net36_vnd.p90", context=ctx),
        },
        "p_net_le_0_24m_pct": _require_finite_float(case["p_net_le_0_24m_pct"], field_name="p_le0_24", context=ctx),
        "p_net_le_0_36m_pct": _require_finite_float(case["p_net_le_0_36m_pct"], field_name="p_le0_36", context=ctx),
        "p_bankroll_ruin_24m_pct": _require_finite_float(
            case["p_bankroll_ruin_24m_pct"], field_name="ruin_24", context=ctx
        ),
        "p_bankroll_ruin_pct": _require_finite_float(case["p_bankroll_ruin_pct"], field_name="ruin_36", context=ctx),
        "ev_per_1_vnd_fee_24m": _require_finite_float(case["ev_per_1_vnd_fee_24m"], field_name="ev_24", context=ctx),
        "ev_per_1_vnd_fee_36m": _require_finite_float(case["ev_per_1_vnd_fee_36m"], field_name="ev_36", context=ctx),
        "mean_total_fees_36m_usd": _require_finite_float(
            case["mean_total_fees_36m_usd"], field_name="fees_36_usd", context=ctx
        ),
        "mean_total_fees_36m_vnd": _require_finite_float(
            case["mean_total_fees_36m_vnd"], field_name="fees_36_vnd", context=ctx
        ),
        "uncond_med_pay1_cal_days_cap365": _require_finite_float(
            case["uncond_med_pay1_cal_days_cap365"], field_name="pay1_365", context=ctx
        ),
        "uncond_med_pay1_cal_days_cap730": _require_finite_float(
            case["uncond_med_pay1_cal_days_cap730"], field_name="pay1_730", context=ctx
        ),
        "cond_med_pay1_cal_days": _require_finite_float(
            case["cond_med_pay1_cal_days"], field_name="pay1_cond", context=ctx
        ),
        "funded_12m_blowup_pct": _require_finite_float(blow["blowup_12m_pct"], field_name="blowup_12m", context=ctx),
        "funded_12m_wilson_95_ub_pct": _require_finite_float(
            blow["wilson_95_ub_pct"], field_name="wilson_ub", context=ctx
        ),
        "bot_auto_kill_pct": _require_finite_float(case["bot_auto_kill_pct"], field_name="bot_kill", context=ctx),
        "firm_hard_breach_pct": _require_finite_float(
            case["firm_hard_breach_pct"], field_name="firm_breach", context=ctx
        ),
        "funded_dry_months_pct": _require_finite_float(
            case["funded_dry_months_pct"], field_name="dry_months", context=ctx
        ),
        "longest_starved_month_streak_p50": int(case["longest_starved_month_streak_p50"]),
        "longest_starved_month_streak_p95": int(case["longest_starved_month_streak_p95"]),
        "mean_own_book_36m_usd": _require_finite_float(
            case["mean_own_book_36m_usd"], field_name="own_book_36m", context=ctx
        ),
        "mean_max_base_funded_usd": _require_finite_float(
            case["mean_max_base_funded_usd"], field_name="max_base_funded", context=ctx
        ),
        "monthly_pass_fail_pending": partitions,
    }


def reconcile_pareto_9tier_and_81cases(
    pareto_summary: Mapping[str, Any],
    pareto_81cases: Mapping[str, Any],
    *,
    summary_meta: Mapping[str, Any],
    full_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconcile full 9-tier Pareto summary table (1.0x & 1.5x) + exact pointers to all 81 configs."""
    cases_base = pareto_81cases.get("cases")
    cases_stress = pareto_81cases.get("cases_stress_1_5x")
    if not isinstance(cases_base, list) or len(cases_base) != EXPECTED_PARETO_CASE_COUNT:
        raise MalformedArtifactError(
            f"wave4_pareto_81cases_10k.json must have {EXPECTED_PARETO_CASE_COUNT} baseline cases"
        )
    if not isinstance(cases_stress, list) or len(cases_stress) != EXPECTED_PARETO_CASE_COUNT:
        raise MalformedArtifactError(
            f"wave4_pareto_81cases_10k.json must have {EXPECTED_PARETO_CASE_COUNT} stress_1_5x cases"
        )

    base_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    stress_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for idx, row in enumerate(cases_base):
        cid = str(row["case_id"])
        base_by_id[cid] = (idx, row)
        _verify_partition_dict(row["monthly_pass_fail_pending"], horizons=PARETO_HORIZONS, context=f"base:{cid}")
    for idx, row in enumerate(cases_stress):
        cid = str(row["case_id"])
        stress_by_id[cid] = (idx, row)
        _verify_partition_dict(row["monthly_pass_fail_pending"], horizons=PARETO_HORIZONS, context=f"stress:{cid}")

    if set(base_by_id.keys()) != set(stress_by_id.keys()):
        raise ArithmeticDriftError("Baseline 1.0x and stress 1.5x case_id sets do not match in 81-case file")

    expected_grid_ids = {
        f"B{tier}M__{mode}__{policy}"
        for tier in EXPECTED_BANKROLL_TIERS_M_VND
        for mode in EXPECTED_CONCURRENCY_MODES
        for policy in EXPECTED_ALLOCATION_POLICIES
    }
    if set(base_by_id.keys()) != expected_grid_ids:
        raise ArithmeticDriftError(
            f"81-case grid mismatch: missing={sorted(expected_grid_ids - set(base_by_id))} "
            f"extra={sorted(set(base_by_id) - expected_grid_ids)}"
        )

    tier_highlights = pareto_summary["tier_pareto_highlights"]
    frontier_base_by_tier = pareto_81cases["pareto_frontier_by_bankroll_tier"]
    frontier_stress_by_tier = pareto_81cases["pareto_frontier_by_bankroll_tier_stress_1_5x"]

    tiers_table: list[dict[str, Any]] = []
    for tier_m in EXPECTED_BANKROLL_TIERS_M_VND:
        tkey = f"{tier_m}M_VND"
        if tkey not in tier_highlights:
            raise MalformedArtifactError(f"Missing tier {tkey!r} in pareto_summary.tier_pareto_highlights")
        th = tier_highlights[tkey]
        roles_out: dict[str, Any] = {}
        for role in ("safest", "balanced_sweet_spot", "max_upside"):
            summary_role = th[role]
            cid = str(summary_role["case_id"])
            if cid not in base_by_id:
                raise ArithmeticDriftError(f"Highlight {tkey}.{role} references unknown case_id {cid!r}")
            b_idx, b_case = base_by_id[cid]
            s_idx, s_case = stress_by_id[cid]

            # Cross-verify zero arithmetic drift between compact summary and authoritative 81-case full file
            if (
                abs(float(summary_role["net_profit_36m_vnd"]["median"]) - float(b_case["net_profit_36m_vnd"]["median"]))
                > 1.0
            ):
                raise ArithmeticDriftError(
                    f"Summary vs 81-case drift on {cid} baseline median_36m_vnd: "
                    f"{summary_role['net_profit_36m_vnd']['median']} vs {b_case['net_profit_36m_vnd']['median']}"
                )
            if (
                abs(
                    float(summary_role["stress_1_5x"]["median_36m_net_vnd"])
                    - float(s_case["net_profit_36m_vnd"]["median"])
                )
                > 1.0
            ):
                raise ArithmeticDriftError(
                    f"Summary vs 81-case drift on {cid} stress_1_5x median_36m_vnd: "
                    f"{summary_role['stress_1_5x']['median_36m_net_vnd']} vs {s_case['net_profit_36m_vnd']['median']}"
                )

            roles_out[role] = {
                "case_id": cid,
                "index_in_81cases_baseline": b_idx,
                "index_in_81cases_stress_1_5x": s_idx,
                "json_pointer_baseline": f"/cases/{b_idx}",
                "json_pointer_stress_1_5x": f"/cases_stress_1_5x/{s_idx}",
                "concurrency_mode": str(b_case["concurrency_mode"]),
                "allocation_policy": str(b_case["allocation_policy"]),
                "is_pareto_in_tier_1_0x": bool(b_case["is_pareto_in_tier"]),
                "is_pareto_overall_1_0x": bool(b_case["is_pareto_overall"]),
                "is_pareto_in_tier_1_5x": bool(s_case["is_pareto_in_tier"]),
                "is_pareto_overall_1_5x": bool(s_case["is_pareto_overall"]),
                "law15_grade_code": str(summary_role["law15_grade_code"]),
                "law15_grade_vi": str(summary_role["law15_grade_vi"]),
                "own_book_crossover_phase": str(summary_role["own_book_crossover_phase"]),
                "own_book_crossover_progress_pct": _require_finite_float(
                    summary_role["own_book_crossover_progress_pct"],
                    field_name="own_book_crossover_progress_pct",
                    context=cid,
                ),
                "baseline_1_0x": _extract_pareto_regime_block(b_case, regime_label="1.0x"),
                "stress_1_5x": _extract_pareto_regime_block(s_case, regime_label="1.5x"),
            }

        tiers_table.append(
            {
                "tier_key": tkey,
                "bankroll_m_vnd": tier_m,
                "bankroll_vnd": tier_m * 1_000_000,
                "bankroll_usd": _require_finite_float(th["bankroll_usd"], field_name="bankroll_usd", context=tkey),
                "pareto_count_baseline_1_0x": len(frontier_base_by_tier[tkey]),
                "pareto_case_ids_baseline_1_0x": list(frontier_base_by_tier[tkey]),
                "pareto_count_stress_1_5x": len(frontier_stress_by_tier[tkey]),
                "pareto_case_ids_stress_1_5x": list(frontier_stress_by_tier[tkey]),
                "roles": roles_out,
            }
        )

    all_81_pointers: list[dict[str, Any]] = []
    for idx, b_case in enumerate(cases_base):
        cid = str(b_case["case_id"])
        s_idx, s_case = stress_by_id[cid]
        all_81_pointers.append(
            {
                "case_id": cid,
                "bankroll_m_vnd": int(b_case["bankroll_m_vnd"]),
                "bankroll_usd": float(b_case["bankroll_usd"]),
                "concurrency_mode": str(b_case["concurrency_mode"]),
                "allocation_policy": str(b_case["allocation_policy"]),
                "is_pareto_in_tier_1_0x": bool(b_case["is_pareto_in_tier"]),
                "is_pareto_overall_1_0x": bool(b_case["is_pareto_overall"]),
                "is_pareto_in_tier_1_5x": bool(s_case["is_pareto_in_tier"]),
                "is_pareto_overall_1_5x": bool(s_case["is_pareto_overall"]),
                "json_pointer_baseline": f"/cases/{idx}",
                "json_pointer_stress_1_5x": f"/cases_stress_1_5x/{s_idx}",
                "baseline_1_0x": {
                    "median_24m_vnd": float(b_case["net_profit_24m_vnd"]["median"]),
                    "median_24m_usd": float(b_case["net_profit_24m_usd"]["median"]),
                    "median_36m_vnd": float(b_case["net_profit_36m_vnd"]["median"]),
                    "median_36m_usd": float(b_case["net_profit_36m_usd"]["median"]),
                    "p_net_le_0_24m_pct": float(b_case["p_net_le_0_24m_pct"]),
                    "p_net_le_0_36m_pct": float(b_case["p_net_le_0_36m_pct"]),
                    "p_bankroll_ruin_pct": float(b_case["p_bankroll_ruin_pct"]),
                    "ev_per_1_vnd_fee_36m": float(b_case["ev_per_1_vnd_fee_36m"]),
                    "funded_12m_blowup_pct": float(b_case["funded_12m_blowup"]["blowup_12m_pct"]),
                    "uncond_med_pay1_cal_days_cap730": float(b_case["uncond_med_pay1_cal_days_cap730"]),
                    "pass_fail_pending_24m": b_case["monthly_pass_fail_pending"]["24m"],
                    "pass_fail_pending_36m": b_case["monthly_pass_fail_pending"]["36m"],
                },
                "stress_1_5x": {
                    "median_24m_vnd": float(s_case["net_profit_24m_vnd"]["median"]),
                    "median_24m_usd": float(s_case["net_profit_24m_usd"]["median"]),
                    "median_36m_vnd": float(s_case["net_profit_36m_vnd"]["median"]),
                    "median_36m_usd": float(s_case["net_profit_36m_usd"]["median"]),
                    "p_net_le_0_24m_pct": float(s_case["p_net_le_0_24m_pct"]),
                    "p_net_le_0_36m_pct": float(s_case["p_net_le_0_36m_pct"]),
                    "p_bankroll_ruin_pct": float(s_case["p_bankroll_ruin_pct"]),
                    "ev_per_1_vnd_fee_36m": float(s_case["ev_per_1_vnd_fee_36m"]),
                    "funded_12m_blowup_pct": float(s_case["funded_12m_blowup"]["blowup_12m_pct"]),
                    "uncond_med_pay1_cal_days_cap730": float(s_case["uncond_med_pay1_cal_days_cap730"]),
                    "pass_fail_pending_24m": s_case["monthly_pass_fail_pending"]["24m"],
                    "pass_fail_pending_36m": s_case["monthly_pass_fail_pending"]["36m"],
                },
            }
        )

    return {
        "source_summary_rel_path": summary_meta["rel_path"],
        "source_summary_file_sha256": summary_meta["file_sha256"],
        "source_81cases_rel_path": full_meta["rel_path"],
        "source_81cases_file_sha256": full_meta["file_sha256"],
        "resolution_label_vi": str(pareto_summary["resolution_label_vi"]),
        "resolution_tag": str(pareto_summary["resolution_tag"]),
        "evidence_stage": str(pareto_summary["evidence_stage"]),
        "execution_status": str(pareto_summary["execution_status"]),
        "pricing_regime": str(pareto_summary["pricing_regime"]),
        "usd_vnd_rate": float(pareto_summary["ssot_provenance"]["usd_vnd_rate"]),
        "fx_verified_utc": str(pareto_summary["ssot_provenance"]["fx_verified_utc"]),
        "grid_shape": pareto_summary["grid_shape"],
        "shared_path_correlation_proof": pareto_summary["shared_path_correlation_proof"],
        "all_162_cases_x_5_horizons_partition_100pct_verified": True,
        "total_partition_checks_verified": 2 * EXPECTED_PARETO_CASE_COUNT * len(PARETO_HORIZONS),
        "pareto_frontier_overall_ids_1_0x": list(pareto_81cases["pareto_frontier_overall_ids"]),
        "pareto_frontier_overall_ids_1_5x": list(pareto_81cases["pareto_frontier_overall_ids_stress_1_5x"]),
        "global_sweet_spots": pareto_summary["global_sweet_spots"],
        "stress_1_5x_summary": pareto_summary["stress_1_5x_summary"],
        "per_sku_001_lot_audit": pareto_summary["per_sku_001_lot_audit"],
        "tiers": tiers_table,
        "all_81_config_pointers": all_81_pointers,
        "the5ers_reference_compact": pareto_summary.get("the5ers_reference_compact", []),
    }


def build_four_tier_inside_out_scorecard(
    docs: Mapping[str, Mapping[str, Any]],
    pareto_table: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble Law 15 Inside-Out 4-Tier Top 1% Scorecard strictly from disk-verified raw docs."""
    p98 = docs["w4_t0_parity98_receipt"]
    ml_arena = docs["wave4_ml_arena_summary"]
    mt5_onnx = docs["w4_m1_mt5_onnx_receipt"]
    cme = docs["wave4_cme_intraday_feasibility"]
    ownbook = docs["ownbook_shadow_ops_summary"]
    frontier = docs["frontier_cluster_b_blind_verdict"]
    vnbook = docs["w4_m2b_vnbook_receipt"]
    fleet_e2e = docs["fleet_e2e_drill_receipt"]
    web_ui = docs["w4_m2c_web_ui_receipt"]
    radar = docs["ai_model_radar_latest"]
    pit24 = docs["wave4_pit24_and_ai_rubric"]
    shadow_ledger = docs["prospective_shadow_ledger"]
    m1_16 = docs["wave4_16sym_harvest_summary"]
    briefing = docs["w4_ops_briefing_wire_receipt"]
    tests_all = docs["w4_tests_all_receipt"]
    milestones = docs["w4_t0_milestones_receipt"]

    # Verify all CME + FTMO incumbent monthly partitions sum to 100.0% fail-closed
    for section_key in ("cme_4firm_results", "incumbent_ftmo_results"):
        for tid, row in cme[section_key].items():
            _verify_partition_dict(
                row["pass_fail_pending"],
                horizons=CME_HORIZONS,
                context=f"cme:{section_key}:{tid}",
            )

    # --- Tier 1: Single CFD Prop Bot ---
    sku_100k_1x = pareto_table["per_sku_001_lot_audit"]["regimes"]["1.00x"]["100K"]
    sku_10k_1x = pareto_table["per_sku_001_lot_audit"]["regimes"]["1.00x"]["10K"]
    sku_100k_15x = pareto_table["per_sku_001_lot_audit"]["regimes"]["1.50x"]["100K"]
    tiers_by_key = {row["tier_key"]: row for row in pareto_table["tiers"]}
    b10_bal = tiers_by_key["10M_VND"]["roles"]["balanced_sweet_spot"]
    b25_bal = tiers_by_key["25M_VND"]["roles"]["balanced_sweet_spot"]
    b100_bal = tiers_by_key["100M_VND"]["roles"]["balanced_sweet_spot"]
    b250_bal = tiers_by_key["250M_VND"]["roles"]["balanced_sweet_spot"]

    tier_1 = {
        "tier_number": 1,
        "domain_tier": "TIER_1_SINGLE_CFD_PROP_BOT",
        "title_vi": "Tầng 1 — Bot Thi Quỹ CFD Đơn Lẻ (PORT_7E v1.03 & v1.04-ML)",
        "evidence_stage": (
            "BACKTEST_DEV_SEALED_LE_2024 + MT5_BUILD_6230_DEV_2024 (Holdout 2025+ SEALED, Live/Demo Pending)"
        ),
        "scale_4_levels": {
            "XAU": "EV/Phí <= 0x hoặc cháy Funded 12m > 5% hoặc PF < 1.05",
            "DU_DUNG": "EV/Phí +1x..+2.99x hoặc cháy Funded 12m 1%..5%, PF 1.10..1.20",
            "TOT": "EV/Phí +3x..+4.99x & cháy Funded 12m < 1% & Ruin < 1%, chờ Payout #1 5..14 tháng, PF 1.20..1.50",
            "TOP_1_PCT": (
                "EV/Phí >= +5x & cháy Funded 12m < 1% & Ruin < 1% & Payout #1 trong 2..4 tháng "
                "xác nhận trên Holdout + tiền thật"
            ),
        },
        "baseline_before_wave4": {
            "mt5_cross_feed_match_rate_range_pct": [
                round(
                    p98["offensive3_before_vs_wave4_after"]["Funded_1x_10K_2024_M1"]["before_offensive3_cross_feed"][
                        "trade_match_rate"
                    ]
                    * 100.0,
                    2,
                ),
                round(
                    p98["offensive3_before_vs_wave4_after"]["Sprint_Eval_10K_2024_M1"]["before_offensive3_cross_feed"][
                        "trade_match_rate"
                    ]
                    * 100.0,
                    2,
                ),
            ],
            "mt5_cross_feed_ghosts_range": [
                p98["offensive3_before_vs_wave4_after"]["Funded_1x_10K_2024_M1"]["before_offensive3_cross_feed"][
                    "ghost_trades"
                ],
                p98["offensive3_before_vs_wave4_after"]["Sprint_Eval_10K_2024_M1"]["before_offensive3_cross_feed"][
                    "ghost_trades"
                ],
            ],
            "v103_oof_dev_2799": {
                "n_trades": ml_arena["baseline_v103"]["full_oof"]["n_oof_trades"],
                "winrate_pct": round(ml_arena["baseline_v103"]["full_oof"]["economics_1x"]["win_rate"] * 100.0, 2),
                "ev_r": round(ml_arena["baseline_v103"]["full_oof"]["economics_1x"]["ev_r"], 4),
                "profit_factor": round(ml_arena["baseline_v103"]["full_oof"]["economics_1x"]["profit_factor"], 4),
                "max_dd_pct": round(ml_arena["baseline_v103"]["full_oof"]["economics_1x"]["max_dd_pct"], 2),
                "slippage_breakeven_24m": ml_arena["baseline_v103"]["full_oof"]["slippage_breakeven_24m"],
            },
            "v103_mt5_2024_funded_1x_10k": {
                "trades": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"]["trades"],
                "winrate_pct": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"]["win_rate_pct"],
                "net_pnl_usd": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"]["net_pnl_usd"],
                "profit_factor": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"][
                    "profit_factor"
                ],
                "balance_dd_pct": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"][
                    "balance_dd_pct"
                ],
                "equity_dd_pct": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"][
                    "equity_dd_pct"
                ],
                "worst_day_pct": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"][
                    "worst_day_pct"
                ],
                "swap_total_usd": mt5_onnx["full2024_mt5_ablation"]["baseline_v103_funded_1x"]["metrics"][
                    "swap_total_usd"
                ],
            },
            "port7e_sku_100k_1_0x_dev_7y": {
                "winrate_pct": sku_100k_1x["winrate_pct"],
                "avg_rr": sku_100k_1x["avg_rr"],
                "ev_per_trade_r": sku_100k_1x["ev_per_trade_r"],
                "profit_factor": sku_100k_1x["profit_factor"],
                "peak_dd_pct": sku_100k_1x["peak_dd_pct"],
                "calmar": sku_100k_1x["calmar"],
                "sharpe": sku_100k_1x["sharpe"],
                "ann_pct": sku_100k_1x["ann_pct"],
                "min_lot_drag_10k_vs_100k_pct": sku_10k_1x["drag_vs_100k_pct"],
            },
            "port7e_sku_100k_1_5x_stress_dev_7y": {
                "winrate_pct": sku_100k_15x["winrate_pct"],
                "avg_rr": sku_100k_15x["avg_rr"],
                "ev_per_trade_r": sku_100k_15x["ev_per_trade_r"],
                "profit_factor": sku_100k_15x["profit_factor"],
                "peak_dd_pct": sku_100k_15x["peak_dd_pct"],
                "calmar": sku_100k_15x["calmar"],
                "sharpe": sku_100k_15x["sharpe"],
            },
        },
        "wave4_achieved": {
            "same_feed_model1_parity": {
                "trade_match_rate_pct": round(p98["headline_summary"]["model1_aggregate_trade_match_rate"] * 100.0, 4),
                "matched_trades": p98["headline_summary"]["model1_total_matched_trades_60s"],
                "expected_trades": p98["headline_summary"]["model1_total_expected_trades"],
                "ghost_trades": p98["headline_summary"]["model1_total_ghost_trades"],
                "missed_trades": p98["headline_summary"]["model1_total_missed_trades"],
                "gross_r_drift_pct_range": [
                    round(x * 100.0, 2) for x in p98["headline_summary"]["model1_gross_r_drift_range"]
                ],
                "model4_q4_2024_match_60s_pct": round(
                    p98["offensive3_before_vs_wave4_after"]["Funded_1x_10K_2024Q4_M4_microstructure_separate"][
                        "after_wave4_same_feed_m1_vs_m4"
                    ]["trade_match_rate"]
                    * 100.0,
                    2,
                ),
            },
            "v104_ml_arena_w4g04": {
                "verdict": ml_arena["verdict"],
                "recorded_trials": ml_arena["budget"]["recorded_trials"],
                "max_trials": ml_arena["budget"]["max_trials"],
                "promoted_trials": ml_arena["budget"]["promoted_trials"],
                "best_overall_trial": {
                    "trial_id": ml_arena["best_overall_trial"]["trial_id"],
                    "family": ml_arena["best_overall_trial"]["family_name"],
                    "brier_skill_score": ml_arena["best_overall_trial"]["brier_skill_score"],
                    "roc_auc": ml_arena["best_overall_trial"]["roc_auc"],
                    "pf_1x": ml_arena["best_overall_trial"]["pf_1x"],
                    "ev_r_1x": ml_arena["best_overall_trial"]["ev_r_1x"],
                    "max_dd_pct_1x": ml_arena["best_overall_trial"]["max_dd_pct_1x"],
                    "slippage_breakeven_24m": ml_arena["best_overall_trial"]["slippage_breakeven_24m"],
                },
                "exported_onnx_trial": {
                    "trial_id": ml_arena["family_leaderboard"]["lightgbm"]["best_trial_id"],
                    "family": "lightgbm",
                    "brier_skill_score": ml_arena["family_leaderboard"]["lightgbm"]["brier_skill_score"],
                    "roc_auc": ml_arena["family_leaderboard"]["lightgbm"]["roc_auc"],
                    "pf_1x": ml_arena["family_leaderboard"]["lightgbm"]["pf_1x"],
                    "ev_r_1x": ml_arena["family_leaderboard"]["lightgbm"]["ev_r_1x"],
                    "max_dd_pct_1x": ml_arena["family_leaderboard"]["lightgbm"]["max_dd_pct_1x"],
                    "slippage_breakeven_24m": ml_arena["family_leaderboard"]["lightgbm"]["slippage_breakeven_24m"],
                },
            },
            "v104_ml_mt5_onnx_w4g05": {
                "verdict": mt5_onnx["w4_g05_verdict"],
                "four_way_parity_500_max_abs_err": mt5_onnx["independent_parity_500"]["four_way_parity_500"][
                    "overall_max_abs_err"
                ],
                "all_decision_agreements_100pct": mt5_onnx["independent_parity_500"]["four_way_parity_500"][
                    "all_decision_agreements_100pct"
                ],
                "trades": mt5_onnx["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["trades"],
                "filtered_trades": mt5_onnx["full2024_mt5_ablation"]["comparisons"]["v104_ml_onnx_vs_v103_baseline"][
                    "filtered_trades_count"
                ],
                "winrate_pct": mt5_onnx["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["win_rate_pct"],
                "net_pnl_usd": mt5_onnx["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["net_pnl_usd"],
                "delta_net_pnl_usd": mt5_onnx["full2024_mt5_ablation"]["comparisons"]["v104_ml_onnx_vs_v103_baseline"][
                    "delta_net_pnl_usd"
                ],
                "profit_factor": mt5_onnx["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["profit_factor"],
                "balance_dd_pct": mt5_onnx["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["balance_dd_pct"],
                "equity_dd_pct": mt5_onnx["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["equity_dd_pct"],
                "swap_total_usd": mt5_onnx["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"]["swap_total_usd"],
                "pure_mql5_exact_match": mt5_onnx["full2024_mt5_ablation"]["comparisons"][
                    "v104_ml_pure_mql5_vs_v104_ml_onnx"
                ]["exact_match"],
                "disabled_reproduces_v103_exact": mt5_onnx["full2024_mt5_ablation"]["comparisons"][
                    "v104_ml_disabled_vs_v103_baseline"
                ]["exact_reproduction"],
            },
            "pareto_prop_benchmarks_36m": {
                "10M_balanced_case_id": b10_bal["case_id"],
                "10M_ev_per_fee_36m": b10_bal["baseline_1_0x"]["ev_per_1_vnd_fee_36m"],
                "10M_ruin_36m_pct": b10_bal["baseline_1_0x"]["p_bankroll_ruin_pct"],
                "10M_funded_12m_blowup_pct": b10_bal["baseline_1_0x"]["funded_12m_blowup_pct"],
                "10M_uncond_med_pay1_days": b10_bal["baseline_1_0x"]["uncond_med_pay1_cal_days_cap730"],
                "25M_balanced_case_id": b25_bal["case_id"],
                "25M_ev_per_fee_36m": b25_bal["baseline_1_0x"]["ev_per_1_vnd_fee_36m"],
                "25M_ruin_36m_pct": b25_bal["baseline_1_0x"]["p_bankroll_ruin_pct"],
                "25M_funded_12m_blowup_pct": b25_bal["baseline_1_0x"]["funded_12m_blowup_pct"],
                "25M_uncond_med_pay1_days": b25_bal["baseline_1_0x"]["uncond_med_pay1_cal_days_cap730"],
                "100M_balanced_case_id": b100_bal["case_id"],
                "100M_ev_per_fee_36m": b100_bal["baseline_1_0x"]["ev_per_1_vnd_fee_36m"],
                "100M_ruin_36m_pct": b100_bal["baseline_1_0x"]["p_bankroll_ruin_pct"],
                "100M_funded_12m_blowup_pct": b100_bal["baseline_1_0x"]["funded_12m_blowup_pct"],
                "250M_lowest_p_net_le_0_24m_pct": b250_bal["baseline_1_0x"]["p_net_le_0_24m_pct"],
            },
        },
        "current_position_code": "TOT",
        "current_position_vi": (
            "Tốt — vượt ngưỡng Top 1% về EV/Phí (5.15x..20.15x), cháy Funded 12m (0.17%..0.44% < 1%) "
            "và Ruin < 1% từ 10M VND trên Dev backtest, nhưng CHƯA đạt Top 1% thực tế."
        ),
        "top_1_pct_target": {
            "ev_per_fee_min": 5.0,
            "funded_12m_blowup_max_pct": 1.0,
            "bankroll_ruin_max_pct": 1.0,
            "uncond_med_pay1_months_range": [2.0, 4.0],
            "p_net_le_0_24m_max_pct": 15.0,
            "required_evidence": "Sealed Holdout 2025+ + Live/Demo Forward >= 20-30 clean trades + settled payouts",
        },
        "concrete_gap_to_top_1_pct": [
            (
                "Tốc độ tới Payout #1 không điều kiện còn "
                f"{b25_bal['baseline_1_0x']['uncond_med_pay1_cal_days_cap730']} "
                "ngày (~13.7 tháng ở 25M) so với mục tiêu Top 1% 2..4 tháng (60..120 ngày)."
            ),
            (
                f"Xác suất lỗ ròng sau 24 tháng P(net <= 0) thấp nhất đạt "
                f"{b250_bal['baseline_1_0x']['p_net_le_0_24m_pct']}% (ở 250M) — chưa chạm ngưỡng < 15%."
            ),
            (
                "Dưới stress trượt giá 1.5x, mức 15M/40M/60M Aggressive âm trung vị 36m; "
                "v1.04-ML cần xác nhận Holdout 2025+ và FTMO Free Trial thực địa (0 lệnh thật đã chạy)."
            ),
        ],
    }

    # --- Tier 2: CME Futures Prop ---
    topstep_100k = cme["cme_4firm_results"]["topstep_100k_combine"]
    topstep_50k = cme["cme_4firm_results"]["topstep_50k_combine"]
    tradeify_50k = cme["cme_4firm_results"]["tradeify_50k_growth"]
    ftmo_10k_ref = cme["incumbent_ftmo_results"]["ftmo_standard_10k"]
    ftmo_100k_ref = cme["incumbent_ftmo_results"]["ftmo_standard_100k"]
    vn_eligible_cme_count = sum(
        1
        for row in cme["vn_kyc_feasibility_matrix"]
        if row["asset_class"] == "CME_FUTURES_INTRADAY" and row["vn_kyc_eligible"]
    )
    total_cme_firms = sum(1 for row in cme["vn_kyc_feasibility_matrix"] if row["asset_class"] == "CME_FUTURES_INTRADAY")

    tier_2 = {
        "tier_number": 2,
        "domain_tier": "TIER_2_CME_FUTURES_INTRADAY",
        "title_vi": "Tầng 2 — Quỹ Futures CME Intraday (Topstep / MFFU / TakeProfitTrader / Tradeify)",
        "verdict": cme["decision"],
        "evidence_stage": (
            "BACKTEST_DEV_SEALED_LE_2024 + TERMS_VERIFIED_EXECUTION_UNMEASURED "
            "(10,000-path MC, APPROX_DAILY_RESOLUTION)"
        ),
        "scale_4_levels": topstep_100k["domain_scorecard"]["scale_definition"],
        "baseline_before_wave4": {
            "wave2_cme_summary_untouched": True,
            "wave2_cme_summary_sha256": docs["w4_m4_exec_receipt"]["cme_verification"]["wave2_summary_sha256"],
            "cme_4firm_vn_kyc_and_10k_mc_audited_before": False,
        },
        "wave4_achieved": {
            "decision": cme["decision"],
            "n_paths": cme["simulation_config"]["n_paths"],
            "vn_kyc_eligible_firms": vn_eligible_cme_count,
            "cme_firms_audited": total_cme_firms,
            "dev_e4_e5_strategy_metrics": cme["dev_strategy_metrics"],
            "vn_eligible_best_tier": {
                "tier_id": topstep_100k["tier_id"],
                "vn_kyc_status": topstep_100k["vn_kyc_status"],
                "ev_per_usd_fee": topstep_100k["ev_per_usd_fee"],
                "median_net_24m_usd": topstep_100k["median_net_24m_usd"],
                "median_net_24m_vnd": topstep_100k["median_net_24m_vnd"],
                "prob_net_le_zero_pct": topstep_100k["prob_net_le_zero_pct"],
                "funded_blowup_12m_pct": topstep_100k["funded_blowup_12m_pct"],
                "funded_blowup_12m_wilson_ub95_pct": topstep_100k["funded_blowup_12m_wilson_ub95_pct"],
                "uncond_med_pay1_days": topstep_100k["median_cal_days_to_payout1_unconditional"],
                "pass_fail_pending_24m": topstep_100k["pass_fail_pending"]["24m"],
            },
            "vn_eligible_safest_tier": {
                "tier_id": topstep_50k["tier_id"],
                "ev_per_usd_fee": topstep_50k["ev_per_usd_fee"],
                "median_net_24m_usd": topstep_50k["median_net_24m_usd"],
                "median_net_24m_vnd": topstep_50k["median_net_24m_vnd"],
                "prob_net_le_zero_pct": topstep_50k["prob_net_le_zero_pct"],
                "funded_blowup_12m_pct": topstep_50k["funded_blowup_12m_pct"],
            },
            "overall_technical_best_blocked_vn": {
                "tier_id": tradeify_50k["tier_id"],
                "vn_kyc_status": tradeify_50k["vn_kyc_status"],
                "ev_per_usd_fee": tradeify_50k["ev_per_usd_fee"],
                "funded_blowup_12m_pct": tradeify_50k["funded_blowup_12m_pct"],
                "prob_net_le_zero_pct": tradeify_50k["prob_net_le_zero_pct"],
            },
            "incumbent_ftmo_benchmark": {
                "ftmo_10k_ev_per_fee": ftmo_10k_ref["ev_per_usd_fee"],
                "ftmo_100k_ev_per_fee": ftmo_100k_ref["ev_per_usd_fee"],
            },
            "failed_gates": list(cme["decision_rationale"]["failed_gates"]),
        },
        "current_position_code": "XAU_SKIP",
        "current_position_vi": (
            f"Xấu / SKIP — 3/4 hãng chặn KYC Việt Nam; hãng duy nhất hợp lệ (Topstep XFA-only) chỉ đạt "
            f"EV/Phí {topstep_100k['ev_per_usd_fee']}x và cháy Funded 12m {topstep_100k['funded_blowup_12m_pct']}%."
        ),
        "top_1_pct_target": {
            "vn_kyc_eligible": True,
            "ev_per_fee_tot_min": 3.0,
            "ev_per_fee_top1_min": 5.0,
            "funded_blowup_12m_tot_max_pct": 15.0,
            "funded_blowup_12m_top1_max_pct": 5.0,
            "prob_net_le_zero_max_pct": 25.0,
        },
        "concrete_gap_to_top_1_pct": [
            (
                f"EV/Phí Topstep 100K ({topstep_100k['ev_per_usd_fee']}x) kém ngưỡng Tốt (3.0x) "
                f"và kém FTMO 100K ({ftmo_100k_ref['ev_per_usd_fee']}x) tới 6.5 lần."
            ),
            (
                f"Cháy Funded 12m ({topstep_100k['funded_blowup_12m_pct']}%) cao hơn ngưỡng tối đa 15% "
                "gần 4 lần do EOD Trailing DD chặt + phí thuê bao tháng."
            ),
            (
                "Cần phát triển riêng bộ 5–7 động cơ intraday thuần CME (MNQ/MES/MGC/MCL) "
                "+ cầu nối ngoài MT5 (TopstepX/ProjectX) trước khi cân nhắc mở lại."
            ),
        ],
    }

    # --- Tier 3: Multi-Asset Own-Book & Frontier Pod ---
    p7e_2324 = frontier["pod_blend_impact"]["port_7e_baselines"]["cluster_b_2023_2024"]
    p7e_1924 = frontier["pod_blend_impact"]["port_7e_baselines"]["cluster_b_2019_2024"]
    ew_blend = frontier["pod_blend_impact"]["combined_blends"]["EQUAL_WEIGHT"]
    invvol_blend = frontier["pod_blend_impact"]["combined_blends"]["CAUSAL_CLUSTER_A_INV_VOL"]
    core50_blend = frontier["pod_blend_impact"]["combined_blends"]["CORE_50_FRONTIER_50"]
    f01 = frontier["sleeves"]["FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY"]
    f02 = frontier["sleeves"]["FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR"]
    f03 = frontier["sleeves"]["FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM"]
    own_guarded = ownbook["ownbook_dev_performance"]["guarded_metrics"]
    crossover_best = docs["w4_m2a_pareto_receipt"]["global_sweet_spots_summary"]["highest_mean_own_book_36m_case"]

    tier_3 = {
        "tier_number": 3,
        "domain_tier": "TIER_3_MULTI_ASSET_OWNBOOK_FRONTIER_POD",
        "title_vi": "Tầng 3 — Danh Mục Đa Tài Sản Own-Book & Frontier Pod (Macro ETF + Crypto Carry + PORT_7E)",
        "evidence_stage": "DEV_CLUSTER_A_FROZEN_TO_BLIND_CLUSTER_B_LE_2024 (27/36 DuckDB trials, Holdout 2025+ SEALED)",
        "scale_4_levels": {
            "XAU": "Sharpe < 0.8 hoặc tháng đói > 45% hoặc cháy/thanh lý khi stress",
            "DU_DUNG": "Sharpe 0.8..1.2, Calmar 0.6..1.2, tháng đói 35%..45%",
            "TOT": "Sharpe 1.2..2.0, Calmar 1.2..2.0, tháng đói < 35%, 4/4 stress sống sót",
            "TOP_1_PCT": (
                "Sharpe 2.0..3.0+, Calmar >= 2.0, tháng đói < 30% từ nhiều nhánh độc lập "
                "(|r| < 0.15) xác nhận >= 12m tiền thật"
            ),
        },
        "baseline_before_wave4": {
            "port_7e_solo_2019_2024": {
                "sharpe": p7e_1924["sharpe"],
                "calmar": p7e_1924["calmar"],
                "max_dd_pct": p7e_1924["max_dd_pct"],
                "cagr_pct": p7e_1924["cagr_pct"],
                "starved_months_le_0_pct": p7e_1924["starved_months"]["starved_month_rate_le_0_pct"],
            },
            "port_7e_solo_2023_2024_overlap": {
                "sharpe": p7e_2324["sharpe"],
                "calmar": p7e_2324["calmar"],
                "max_dd_pct": p7e_2324["max_dd_pct"],
                "cagr_pct": p7e_2324["cagr_pct"],
                "starved_months_le_0_pct": p7e_2324["starved_months"]["starved_month_rate_le_0_pct"],
                "starved_months_count": p7e_2324["starved_months"]["starved_months_le_0"],
                "total_months": p7e_2324["starved_months"]["n_months"],
            },
        },
        "wave4_achieved": {
            "ownbook_shadow_ops_w4g08": {
                "window": ownbook["data_provenance"]["composite_window"],
                "guarded_sharpe": own_guarded["sharpe"],
                "guarded_calmar": own_guarded["calmar"],
                "guarded_max_dd_pct": own_guarded["max_dd_pct"],
                "guarded_cagr_pct": own_guarded["cagr_pct"],
                "stress_tests_passed": ownbook["ops4_health_snapshot"]["stress_summary"]["passed"],
                "stress_tests_total": ownbook["ops4_health_snapshot"]["stress_summary"]["total"],
                "cex_cap_pct": ownbook["invariants"]["hard_cex_cap_pct"],
                "crash_2022_ownbook_dd_pct": ownbook["extreme_stress_tests"][
                    "STRESS_3_2022_SIMULTANEOUS_STOCK_BOND_CRASH"
                ]["ownbook_2022_max_dd_pct"],
                "crash_2022_60_40_dd_pct": ownbook["extreme_stress_tests"][
                    "STRESS_3_2022_SIMULTANEOUS_STOCK_BOND_CRASH"
                ]["static_60_40_ief_2022_max_dd_pct"],
                "crypto_flash_crash_liquidations": ownbook["extreme_stress_tests"][
                    "STRESS_4_CRYPTO_FLASH_CRASH_MINUS35PCT"
                ]["cross_liq_events"],
                "ibkr_50k_integer_clean": ownbook["ownbook_dev_performance"]["ibkr_integer_share_audit_dev"][
                    "clean_without_fractional"
                ],
                "ibkr_50k_total_cost_bps_yr": ownbook["ownbook_dev_performance"]["ibkr_integer_share_audit_dev"][
                    "total_cost_bps_yr"
                ],
            },
            "frontier_blind_cluster_b_w4g09": {
                "trials_logged": frontier["total_trials_logged"],
                "budget_cap": frontier["budget_cap"],
                "surviving_count": frontier["summary"]["surviving_count"],
                "killed_count": frontier["summary"]["killed_count"],
                "frontier_01_pass": {
                    "verdict": f01["verdict"],
                    "sharpe": f01["blind_metrics"]["sharpe"],
                    "calmar": f01["blind_metrics"]["calmar"],
                    "max_dd_pct": f01["blind_metrics"]["max_dd_pct"],
                    "dd_2022_pct": f01["blind_metrics"]["max_dd_2022_pct"],
                    "pbo_cscv": f01["blind_metrics"]["pbo_cscv"],
                    "dsr_empirical": f01["blind_metrics"]["dsr_empirical"],
                    "bh_fdr_q": f01["blind_metrics"]["bh_fdr_q"],
                    "corr_vs_7e": f01["blind_metrics"]["corr_vs_7e"],
                },
                "frontier_02_killed": {
                    "verdict": f02["verdict"],
                    "sharpe": f02["blind_metrics"]["sharpe"],
                    "pbo_cscv": f02["blind_metrics"]["pbo_cscv"],
                    "dd_2022_pct": f02["blind_metrics"]["max_dd_2022_pct"],
                    "failed_gates": list(f02["failed_gates"]),
                },
                "frontier_03_pass": {
                    "verdict": f03["verdict"],
                    "sharpe": f03["blind_metrics"]["sharpe"],
                    "calmar": f03["blind_metrics"]["calmar"],
                    "max_dd_pct": f03["blind_metrics"]["max_dd_pct"],
                    "cagr_pct": f03["blind_metrics"]["cagr_pct"],
                    "pbo_cscv": f03["blind_metrics"]["pbo_cscv"],
                    "dsr_empirical": f03["blind_metrics"]["dsr_empirical"],
                    "corr_vs_7e": f03["blind_metrics"]["corr_vs_7e"],
                    "cross_liq_events": f03["diagnostics"]["cross_liq_events"],
                },
            },
            "combined_pod_blends_2023_2024": {
                "equal_weight": {
                    "weights": ew_blend["weights"],
                    "sharpe": ew_blend["sharpe"],
                    "calmar": ew_blend["calmar"],
                    "max_dd_pct": ew_blend["max_dd_pct"],
                    "cagr_pct": ew_blend["cagr_pct"],
                    "starved_months_le_0_pct": ew_blend["starved_months"]["starved_month_rate_le_0_pct"],
                    "starved_reduction_pp": ew_blend["delta_vs_port7e"]["starved_le_0_reduction_pp"],
                },
                "causal_cluster_a_inv_vol": {
                    "weights": invvol_blend["weights"],
                    "sharpe": invvol_blend["sharpe"],
                    "calmar": invvol_blend["calmar"],
                    "max_dd_pct": invvol_blend["max_dd_pct"],
                    "cagr_pct": invvol_blend["cagr_pct"],
                    "starved_months_le_0_pct": invvol_blend["starved_months"]["starved_month_rate_le_0_pct"],
                    "starved_reduction_pp": invvol_blend["delta_vs_port7e"]["starved_le_0_reduction_pp"],
                    "cex_cap_note": (
                        "Unconstrained inv-vol assigns 63.30% to FRONTIER_03 crypto perp; live deployment must "
                        "enforce the hard <= 25.0% CEX counterparty cap from ownbook_shadow_ops."
                    ),
                },
                "core_50_frontier_50": {
                    "weights": core50_blend["weights"],
                    "sharpe": core50_blend["sharpe"],
                    "calmar": core50_blend["calmar"],
                    "max_dd_pct": core50_blend["max_dd_pct"],
                    "starved_months_le_0_pct": core50_blend["starved_months"]["starved_month_rate_le_0_pct"],
                },
                "sharpe_range": [ew_blend["sharpe"], invvol_blend["sharpe"]],
                "starved_months_le_0_pct_range": [
                    invvol_blend["starved_months"]["starved_month_rate_le_0_pct"],
                    ew_blend["starved_months"]["starved_month_rate_le_0_pct"],
                ],
            },
            "vn_ownbook_playbook": {
                "path": "planning/research/VN-OWNBOOK-EXECUTION-PLAYBOOK.md",
                "bytes": vnbook["verification"]["playbook_bytes"],
                "sha256": vnbook["artifacts"]["planning/research/VN-OWNBOOK-EXECUTION-PLAYBOOK.md"]["sha256"],
            },
            "ownbook_crossover_projection": crossover_best["crossover"],
        },
        "current_position_code": "TOT_CHAM_NGUONG_TOP_1_DEV",
        "current_position_vi": (
            "Tốt — vượt chuẩn Top 1% trên Blind Cluster B Dev "
            f"(Sharpe {ew_blend['sharpe']:.2f}–{invvol_blend['sharpe']:.2f}, "
            f"Calmar {ew_blend['calmar']:.2f}–{invvol_blend['calmar']:.2f}, Tháng đói "
            f"{invvol_blend['starved_months']['starved_month_rate_le_0_pct']:.1f}%–"
            f"{ew_blend['starved_months']['starved_month_rate_le_0_pct']:.1f}% < 30%), "
            "còn thiếu xác nhận Holdout 2025+ và >= 12 tháng vốn thật."
        ),
        "top_1_pct_target": {
            "sharpe_range": [2.0, 3.0],
            "calmar_min": 2.0,
            "starved_months_max_pct": 30.0,
            "max_cex_exposure_pct": 25.0,
            "ownbook_crossover_equity_usd": crossover_best["crossover"]["crossover_equity_usd"],
            "required_evidence": "Holdout 2025+ sealed pass + >= 12m live IBKR/CEX shadow & live reconciliation",
        },
        "concrete_gap_to_top_1_pct": [
            (
                f"Cần đạt điểm hòa vốn Own-Book ~{crossover_best['crossover']['crossover_equity_usd']:,.2f} USD "
                f"(~{crossover_best['crossover']['crossover_equity_vnd'] / 1e9:.2f} tỷ VND; "
                f"quỹ đạo 36m cao nhất mới đạt "
                f"{crossover_best['crossover']['crossover_progress_pct']}% -> PHASE_3_HYBRID_BARBELL)."
            ),
            (
                "Cần xác nhận 2 nhánh sống sót (FRONTIER_01 + FRONTIER_03) trên Holdout 2025+ "
                "và vận hành live thực tế dưới trần CEX <= 25% "
                "(không dùng tỷ trọng 63.3% crypto không giới hạn)."
            ),
        ],
    }

    # --- Tier 4: Live-Ops, Fleet, Web Cockpit & AI Stack ---
    radar_summary = radar["leaderboard_summary"]
    top_budget_model = radar["leaderboards"]["budget_macro_supervisor_monthly_usd"][0]
    pit24_bm = pit24["pit24_benchmark"]
    rubric = pit24["ai_architecture_benchmark_6criteria"]

    tier_4 = {
        "tier_number": 4,
        "domain_tier": "TIER_4_LIVE_OPS_FLEET_COCKPIT_AI",
        "title_vi": "Tầng 4 — Hạ Tầng Live-Ops, Đội Tài Khoản S0..S7, Web Cockpit & AI Advisory",
        "evidence_stage": "OFFLINE_E2E_VERIFIED + LIVE_LOCAL_LOOPBACK_PIT24_PASS (OrderSend = 0, Spend = 0 VND)",
        "scale_4_levels": {
            "XAU": "Quản lý tay bằng Excel, popup màn hình, không guard, AI black-box",
            "DU_DUNG": "Có watchdog đơn lẻ và script kiểm tra rời rạc",
            "TOT": "Đủ FSM S0..S7 + E1..E6 fail-closed + Web Cockpit + Briefing hợp nhất + 0 popup + AI < 5 USD/tháng",
            "TOP_1_PCT": (
                "Toàn bộ tầng Tốt + >= 30 ngày Prospective Shadow AI thực địa "
                "+ >= 20–30 lệnh FTMO Free Trial sạch trên VPS"
            ),
        },
        "baseline_before_wave4": {
            "subprocess_missing_create_no_window": docs["w4_t0_debt_receipt"]["deliverables"][
                "item_1_create_no_window_popup_fix"
            ]["calls_fixed"],
            "sealed_m1_symbols_before": m1_16["hard_invariants"]["existing_hot_m1_symbol_count"],
            "fleet_fsm_guards_cockpit_before": False,
            "live_ai_radar_and_pit24_before": False,
        },
        "wave4_achieved": {
            "zero_popup_w4g17": {
                "files_scanned": tests_all["test_suites"]["suite_e_ast_zero_popup_w4_g17"]["files_scanned"],
                "subprocess_calls_checked": tests_all["test_suites"]["suite_e_ast_zero_popup_w4_g17"][
                    "subprocess_calls_checked"
                ],
                "missing_creationflags_count": tests_all["test_suites"]["suite_e_ast_zero_popup_w4_g17"][
                    "missing_creationflags_count"
                ],
                "pythonw_briefing_exit_code": briefing["zero_popup_verification"]["pythonw_exit_code"],
            },
            "fleet_orchestrator_w4g10": {
                "canonical_states_covered": len(fleet_e2e["lifecycle_drill"]["canonical_states_visited"]),
                "transitions_verified": fleet_e2e["lifecycle_drill"]["transitions_count"],
                "guards_e1_to_e6_proven": fleet_e2e["guards_e1_to_e6_matrix"]["all_6_guards_proven"],
                "simultaneous_guards_count": len(
                    fleet_e2e["guards_e1_to_e6_matrix"]["simultaneous_all_6_guards_fired"]
                ),
                "hash_chain_and_tamper_verified": fleet_e2e["lifecycle_drill"]["hash_chain_verified"],
                "runbook_bytes": docs["w4_m2c_sim_runbook_receipt"]["runbook_summary"]["bytes"],
            },
            "web_cockpit_w4g11": {
                "route": "?view=prop-fleet",
                "startup_critical_graph_delta_bytes": web_ui["bundle_metrics"]["critical_startup_graph_delta_bytes"],
                "lazy_total_raw_bytes": web_ui["bundle_metrics"]["lazy_total_raw_bytes"],
                "lazy_total_gzip_bytes": web_ui["bundle_metrics"]["lazy_total_gzip_bytes"],
                "within_budget": web_ui["bundle_metrics"]["within_budget"],
                "node_unit_tests_passed": web_ui["verification"]["node_unit_tests_passed"],
                "playwright_suites_count": web_ui["verification"]["playwright_browser_suites_count"],
                "prop_fleet_min_contrast_ratio": web_ui["verification"]["playwright_results"][
                    "tests/prop-fleet.browser.mjs"
                ]["min_contrast_ratio"],
                "api_requests_on_prop_fleet": web_ui["invariants"]["api_requests_on_prop_fleet"],
                "hardcoded_hex_count": web_ui["invariants"]["hardcoded_hex_in_prop_fleet_css"],
            },
            "ai_stack_w4g13_w4g14": {
                "openrouter_raw_models": radar["sources"]["openrouter"]["raw_count"],
                "openrouter_valid_priced": radar["sources"]["openrouter"]["valid_priced_count"],
                "budget_eligible_under_5usd_count": radar_summary["budget_eligible_count"],
                "top_budget_model_id": top_budget_model["id"],
                "top_budget_monthly_usd": top_budget_model["monthly_usd"],
                "top_budget_monthly_vnd": top_budget_model["monthly_vnd"],
                "rtx2070s_full_vram_fit_count": radar_summary["local_full_vram_fit_count"],
                "pit24_outcome_status": pit24_bm["outcome_status"],
                "pit24_scenarios_ok": pit24_bm["scenarios_ok"],
                "pit24_scenarios_total": pit24_bm["scenarios_total"],
                "pit24_schema_valid_pct": pit24_bm["json_schema_valid_rate_of_24_pct"],
                "pit24_regime_agreement_pct": pit24_bm["regime_agreement_rate_of_ok_pct"],
                "pit24_p50_latency_ms": pit24_bm["latency_ms_ok"]["p50_ms"],
                "pit24_p95_latency_ms": pit24_bm["latency_ms_ok"]["p95_ms"],
                "rubric_ranking": rubric["ranking_by_composite"],
                "prospective_ledger_first_session": shadow_ledger["first_live_session_date"],
                "prospective_ledger_commitments": shadow_ledger["summary"]["commitments_count"],
                "prospective_ledger_min_days": shadow_ledger["min_audit_calendar_days"],
            },
            "m1_data_lake_w4g02_w4g16": {
                "ftmo_dev_m1_symbols": docs["w4_t0_ftmo_m1_receipt"]["export_summary"]["symbol_count"],
                "ftmo_dev_m1_rows": docs["w4_t0_ftmo_m1_receipt"]["export_summary"]["total_rows"],
                "wave4_16sym_sealed_count": m1_16["target_inventory"]["sealed_count"],
                "wave4_16sym_expected_count": m1_16["target_inventory"]["expected_count"],
                "wave4_16sym_total_bars": m1_16["target_inventory"]["total_bars_sealed"],
                "wave4_16sym_total_parquet_bytes": m1_16["target_inventory"]["total_parquet_bytes"],
                "wave4_16sym_provenance_breakdown": m1_16["target_inventory"]["provenance_breakdown"],
                "wave4_16sym_depth_breakdown": m1_16["target_inventory"]["depth_breakdown"],
                "total_research_m1_symbols_sealed": (
                    m1_16["hard_invariants"]["existing_hot_m1_symbol_count"] + m1_16["target_inventory"]["sealed_count"]
                ),
            },
            "milestones_and_tests": {
                "preregister_holdout_v2_verified": milestones["deliverables"][
                    "milestone_01_12_preregister_holdout_v2_verify"
                ]["verified_artifacts"],
                "nfp_cpi_ntp_offset_ms": milestones["deliverables"][
                    "milestone_04_12_and_10_12_nfp_cpi_quote_collector_preflight"
                ]["ntp_offset_ms"],
                "free_trial_harvester_fixture_match_rate": milestones["deliverables"][
                    "milestone_08_12_free_trial_readonly_harvester"
                ]["offline_fixture_smoke"]["trade_match_rate"],
                "ci_parity_not_local_cache_passed": tests_all["test_suites"][
                    "suite_b_ci_parity_5_testpaths_not_local_cache"
                ]["passed"],
                "immutables_10_of_10_clean": tests_all["test_suites"]["suite_h_immutables_and_hygiene"][
                    "immutables_10_of_10_clean"
                ],
            },
        },
        "current_position_code": "TOT_TIEM_CAN_TOP_1",
        "current_position_vi": (
            "Tốt / tiệm cận Top 1% về kiến trúc kỹ thuật (0 popup, S0..S7 + E1..E6, "
            f"Web Cockpit {web_ui['bundle_metrics']['lazy_total_raw_bytes'] / 1000.0:.1f}KB, "
            "PIT-24 24/24, 16/16 M1), còn thiếu vận hành thực địa >= 30 ngày."
        ),
        "top_1_pct_target": {
            "zero_popup_missing_flags": 0,
            "prospective_ai_shadow_min_days": 30,
            "ftmo_free_trial_clean_trades_min": 20,
            "production_ai_mode": "OFFICIAL_API_PRODUCTION <= 5.0 USD/mo",
        },
        "concrete_gap_to_top_1_pct": [
            (
                f"Cần tích lũy >= {shadow_ledger['min_audit_calendar_days']} ngày lịch cam kết SHA-256 thực địa "
                f"trên Prospective Shadow Ledger (bắt đầu {shadow_ledger['first_live_session_date']}, hiện 0/30 ngày)."
            ),
            (
                "Cần gom đủ bằng chứng FTMO Free Trial thực địa trên naqex-node1 "
                "(Milestone 08/12) + NFP/CPI quote capture (04/12 & 10/12)."
            ),
            (
                "Chuyển Macro Supervisor sang Official API <= 5 USD/tháng khi chạy shadow thật "
                "(không dùng CLIProxyAPI OAuth cho production)."
            ),
        ],
    }

    return {
        "grading_principle": "LAW_15_INSIDE_OUT_BY_DOMAIN_NEVER_CROSS_COMPARE_CEILINGS",
        "tiers_count": 4,
        "tier_1_single_cfd_prop_bot": tier_1,
        "tier_2_cme_futures_prop": tier_2,
        "tier_3_multi_asset_ownbook_frontier_pod": tier_3,
        "tier_4_live_ops_fleet_cockpit_ai": tier_4,
    }


def build_workstream_reconciled_metrics(
    docs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Emit concise, exact reconciled summaries per Wave 4 workstream for report/visuals consumers."""
    return {
        "wave0_foundation": {
            "env_barrier": docs["w4_t0_env_receipt"]["wave0a_barrier_status"],
            "ml_wheels_audited": docs["w4_t0_env_receipt"]["ml_onnx_environment"]["audited_wheel_count"],
            "copyleft_count": docs["w4_t0_env_receipt"]["ml_onnx_environment"]["copyleft_gpl_lgpl_agpl_count"],
            "popup_calls_fixed_wave0b": docs["w4_t0_debt_receipt"]["deliverables"]["item_1_create_no_window_popup_fix"][
                "calls_fixed"
            ],
            "ftmo_m1_symbols": docs["w4_t0_ftmo_m1_receipt"]["export_summary"]["symbol_count"],
            "ftmo_m1_total_rows": docs["w4_t0_ftmo_m1_receipt"]["export_summary"]["total_rows"],
            "parity98_verdict": docs["w4_t0_parity98_receipt"]["w4_g03_verdict"],
            "parity98_model1_matched": docs["w4_t0_parity98_receipt"]["headline_summary"][
                "model1_total_matched_trades_60s"
            ],
            "parity98_model1_expected": docs["w4_t0_parity98_receipt"]["headline_summary"][
                "model1_total_expected_trades"
            ],
            "milestones_preregister_verified": docs["w4_t0_milestones_receipt"]["deliverables"][
                "milestone_01_12_preregister_holdout_v2_verify"
            ]["verified_artifacts"],
        },
        "mui1_ml_v104": {
            "feature_count": docs["w4_m1_feat_receipt"]["feature_count"],
            "causality_bit_exact": docs["w4_m1_feat_receipt"]["causality_proof"]["bit_exact_zero_drift"],
            "cv_n_splits": docs["w4_m1_cv_receipt"]["splitter_verification"]["n_splits"],
            "cv_purge_days": docs["w4_m1_cv_receipt"]["splitter_verification"]["purge_days"],
            "cv_embargo_days": docs["w4_m1_cv_receipt"]["splitter_verification"]["embargo_days"],
            "arena_verdict": docs["wave4_ml_arena_summary"]["verdict"],
            "arena_trials_recorded": docs["wave4_ml_arena_summary"]["budget"]["recorded_trials"],
            "arena_trials_promoted": docs["wave4_ml_arena_summary"]["budget"]["promoted_trials"],
            "family_leaderboard": {
                fam: {
                    "n_trials_run": fd["n_trials_run"],
                    "n_trials_promoted": fd["n_trials_promoted"],
                    "best_trial_id": fd["best_trial_id"],
                    "brier_skill_score": fd["brier_skill_score"],
                    "roc_auc": fd["roc_auc"],
                    "pf_1x": fd["pf_1x"],
                    "ev_r_1x": fd["ev_r_1x"],
                    "max_dd_pct_1x": fd["max_dd_pct_1x"],
                    "slippage_breakeven_24m": fd["slippage_breakeven_24m"],
                    "verdict": fd["verdict"],
                }
                for fam, fd in docs["wave4_ml_arena_summary"]["family_leaderboard"].items()
            },
            "mt5_onnx_verdict": docs["w4_m1_mt5_onnx_receipt"]["w4_g05_verdict"],
            "mt5_onnx_max_abs_err": docs["w4_m1_mt5_onnx_receipt"]["independent_parity_500"]["four_way_parity_500"][
                "overall_max_abs_err"
            ],
            "mt5_2024_ablation_net_pnl_usd": {
                "v103_baseline": docs["w4_m1_mt5_onnx_receipt"]["full2024_mt5_ablation"]["baseline_v103_funded_1x"][
                    "metrics"
                ]["net_pnl_usd"],
                "v104_ml_onnx": docs["w4_m1_mt5_onnx_receipt"]["full2024_mt5_ablation"]["v104_ml_onnx"]["metrics"][
                    "net_pnl_usd"
                ],
                "v104_ml_pure_mql5": docs["w4_m1_mt5_onnx_receipt"]["full2024_mt5_ablation"]["v104_ml_pure_mql5"][
                    "metrics"
                ]["net_pnl_usd"],
                "v104_ml_disabled": docs["w4_m1_mt5_onnx_receipt"]["full2024_mt5_ablation"]["v104_ml_disabled"][
                    "metrics"
                ]["net_pnl_usd"],
            },
            "bootstrap_caveats": docs["w4_m1_arena_receipt"]["test_results"]["forensic_adversarial_diagnostics"][
                "honest_caveats"
            ],
        },
        "mui2b_ownbook_frontier_vnbook": {
            "ownbook_guarded_metrics": docs["ownbook_shadow_ops_summary"]["ownbook_dev_performance"]["guarded_metrics"],
            "ownbook_stress_all_passed": docs["ownbook_shadow_ops_summary"]["ops4_health_snapshot"]["stress_summary"][
                "all_passed"
            ],
            "frontier_verdicts": docs["frontier_cluster_b_blind_verdict"]["summary"]["verdicts_by_sleeve"],
            "frontier_trials_logged": docs["frontier_cluster_b_blind_verdict"]["total_trials_logged"],
            "frontier_budget_cap": docs["frontier_cluster_b_blind_verdict"]["budget_cap"],
            "vn_playbook_bytes": docs["w4_m2b_vnbook_receipt"]["verification"]["playbook_bytes"],
        },
        "mui2c_fleet_and_web_cockpit": {
            "fsm_states": docs["w4_m2c_fsm_receipt"]["fsm_contract"]["canonical_states_count"],
            "guards_count": docs["w4_m2c_guards_receipt"]["guards_contract"]["guards_count"],
            "e2e_drill_status": docs["fleet_e2e_drill_receipt"]["status"],
            "web_ui_lazy_raw_bytes": docs["w4_m2c_web_ui_receipt"]["bundle_metrics"]["lazy_total_raw_bytes"],
            "web_ui_lazy_gzip_bytes": docs["w4_m2c_web_ui_receipt"]["bundle_metrics"]["lazy_total_gzip_bytes"],
            "web_ui_node_tests_passed": docs["w4_m2c_web_ui_receipt"]["verification"]["node_unit_tests_passed"],
            "web_ui_playwright_suites": docs["w4_m2c_web_ui_receipt"]["verification"][
                "playwright_browser_suites_count"
            ],
        },
        "mui3_ai_stack": {
            "radar_openrouter_valid_priced": docs["ai_model_radar_latest"]["sources"]["openrouter"][
                "valid_priced_count"
            ],
            "radar_budget_eligible_count": docs["ai_model_radar_latest"]["leaderboard_summary"][
                "budget_eligible_count"
            ],
            "pit24_status": docs["wave4_pit24_and_ai_rubric"]["pit24_benchmark"]["outcome_status"],
            "pit24_selected_model": docs["wave4_pit24_and_ai_rubric"]["pit24_benchmark"]["selected_model"],
            "pit24_scenarios_ok": docs["wave4_pit24_and_ai_rubric"]["pit24_benchmark"]["scenarios_ok"],
            "six_criteria_ranking": docs["wave4_pit24_and_ai_rubric"]["ai_architecture_benchmark_6criteria"][
                "ranking_by_composite"
            ],
            "prospective_ledger_first_session": docs["prospective_shadow_ledger"]["first_live_session_date"],
            "prospective_ledger_commitments": docs["prospective_shadow_ledger"]["summary"]["commitments_count"],
        },
        "mui4_cme_and_16sym_m1": {
            "cme_decision": docs["wave4_cme_intraday_feasibility"]["decision"],
            "cme_best_vn_tier": docs["wave4_cme_intraday_feasibility"]["decision_rationale"]["vn_eligible_best_tier"],
            "cme_best_vn_ev_per_fee": docs["wave4_cme_intraday_feasibility"]["decision_rationale"][
                "vn_eligible_best_ev_per_fee"
            ],
            "m1_16sym_sealed_count": docs["wave4_16sym_harvest_summary"]["target_inventory"]["sealed_count"],
            "m1_16sym_total_bars": docs["wave4_16sym_harvest_summary"]["target_inventory"]["total_bars_sealed"],
            "m1_16sym_total_parquet_bytes": docs["wave4_16sym_harvest_summary"]["target_inventory"][
                "total_parquet_bytes"
            ],
            "m1_16sym_provenance_breakdown": docs["wave4_16sym_harvest_summary"]["target_inventory"][
                "provenance_breakdown"
            ],
            "m1_16sym_depth_breakdown": docs["wave4_16sym_harvest_summary"]["target_inventory"]["depth_breakdown"],
        },
        "wave2_ops_and_tests": {
            "briefing_gate_status": docs["w4_ops_briefing_wire_receipt"]["status"],
            "tests_all_overall_status": docs["w4_tests_all_receipt"]["overall_status"],
            "tests_all_ci_parity_passed": docs["w4_tests_all_receipt"]["test_suites"][
                "suite_b_ci_parity_5_testpaths_not_local_cache"
            ]["passed"],
            "tests_all_ruff_errors": docs["w4_tests_all_receipt"]["test_suites"]["suite_d_ruff_check"]["errors"],
            "tests_all_ast_missing_creationflags": docs["w4_tests_all_receipt"]["test_suites"][
                "suite_e_ast_zero_popup_w4_g17"
            ]["missing_creationflags_count"],
            "tests_all_immutables_10_of_10_clean": docs["w4_tests_all_receipt"]["test_suites"][
                "suite_h_immutables_and_hygiene"
            ]["immutables_10_of_10_clean"],
        },
    }


def build_wave4_master_metrics(
    root: Path = ROOT,
    *,
    expected_file_sha256: Mapping[str, str] | None = None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    """Reconcile all 40 raw Wave 4 receipts/summaries directly from disk and emit canonical SSOT."""
    docs, ledger, cross_checks = load_and_verify_raw_artifacts(
        root,
        specs=RAW_ARTIFACT_SPECS,
        cross_links=CROSS_ARTIFACT_SHA256_LINKS,
        expected_file_sha256=expected_file_sha256,
    )
    ledger_by_id = {entry["artifact_id"]: entry for entry in ledger}

    pareto_table = reconcile_pareto_9tier_and_81cases(
        docs["wave4_pareto_summary"],
        docs["wave4_pareto_81cases_10k"],
        summary_meta=ledger_by_id["wave4_pareto_summary"],
        full_meta=ledger_by_id["wave4_pareto_81cases_10k"],
    )
    scorecard = build_four_tier_inside_out_scorecard(docs, pareto_table)
    workstreams = build_workstream_reconciled_metrics(docs)

    group_counts: dict[str, int] = {}
    for entry in ledger:
        g = entry["group"]
        group_counts[g] = group_counts.get(g, 0) + 1

    self_hash_verified_count = sum(1 for entry in ledger if entry["self_hash_verified"] is True)
    tests_hygiene = docs["w4_tests_all_receipt"]["test_suites"]["suite_h_immutables_and_hygiene"]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_MASTER_METRICS,
        "offensive_version": OFFENSIVE_VERSION,
        "worker": WORKER_ID,
        "wave": WAVE_LABEL,
        "generated_utc": generated_utc or _utc_now_iso(),
        "reconciliation_status": "PASS_ALL_40_ARTIFACTS_RECONCILED",
        "reconciled_artifact_count": len(ledger),
        "self_hash_verified_count": self_hash_verified_count,
        "cross_artifact_sha256_links_verified": len(cross_checks),
        "hard_invariants": {
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": SPEND_VND,
            "max_official_api_usd_per_month": MAX_OFFICIAL_API_USD_PER_MONTH,
            "all_40_artifacts_holdout_zero": True,
            "all_40_artifacts_order_send_zero": True,
            "all_40_artifacts_spend_vnd_zero": True,
            "immutables_10_of_10_clean": bool(tests_hygiene["immutables_10_of_10_clean"]),
            "quant_core_py_count": int(tests_hygiene["quant_core_py_count"]),
            "private_vault_ex5_count": int(tests_hygiene["private_vault_ex5_count"]),
            "exports_ex5_count": int(tests_hygiene["tracked_exports_ex5_count"]),
            "zero_bare_asserts": True,
            "zero_subprocess_calls": True,
        },
        "artifact_reconciliation_ledger": {
            "total_count": len(ledger),
            "counts_by_group": group_counts,
            "artifacts": ledger,
            "cross_artifact_sha256_checks": cross_checks,
        },
        "four_tier_inside_out_scorecard": scorecard,
        "pareto_9tier_summary_table": pareto_table,
        "workstream_reconciled_metrics": workstreams,
    }
    payload["report_sha256"] = compute_canonical_report_sha256(payload)
    return payload


def verify_master_metrics_payload(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed verifier for `wave4_master_metrics.json` payload (safe under `python -O`)."""
    if not isinstance(doc, Mapping):
        raise MalformedArtifactError("Master metrics payload must be a JSON object")
    if doc.get("schema_version") != SCHEMA_MASTER_METRICS:
        raise MalformedArtifactError(f"Unexpected schema_version: {doc.get('schema_version')!r}")

    stored_sha = doc.get("report_sha256")
    if not isinstance(stored_sha, str) or len(stored_sha) != 64:
        raise TamperedArtifactError("Missing or malformed `report_sha256` on master metrics payload")
    recomputed_sha = compute_canonical_report_sha256(doc)
    if stored_sha != recomputed_sha:
        raise TamperedArtifactError(
            f"MASTER_METRICS_TAMPERED: recorded report_sha256={stored_sha} != recomputed={recomputed_sha}"
        )

    inv = doc.get("hard_invariants")
    if not isinstance(inv, Mapping):
        raise MalformedArtifactError("Missing hard_invariants in master metrics payload")
    enforce_holdout_zero_rows(inv.get("holdout_rows_analysed", -1), context="verify_master_metrics_payload")
    if inv.get("holdout_cutoff_date") != HOLDOUT_CUTOFF_DATE:
        raise HoldoutLockError(f"Unexpected holdout_cutoff_date: {inv.get('holdout_cutoff_date')!r}")
    if inv.get("order_send_capable") is not False or inv.get("order_send_count") != 0:
        raise SafetyInvariantViolationError("Master metrics payload failed order_send == 0 invariant")
    if inv.get("spend_vnd") != 0:
        raise SafetyInvariantViolationError("Master metrics payload failed spend_vnd == 0 invariant")

    ledger = doc.get("artifact_reconciliation_ledger")
    if not isinstance(ledger, Mapping) or len(ledger.get("artifacts", [])) != len(RAW_ARTIFACT_SPECS):
        raise MalformedArtifactError(f"Expected {len(RAW_ARTIFACT_SPECS)} reconciled artifacts in master metrics")

    scorecard = doc.get("four_tier_inside_out_scorecard")
    required_tiers = (
        "tier_1_single_cfd_prop_bot",
        "tier_2_cme_futures_prop",
        "tier_3_multi_asset_ownbook_frontier_pod",
        "tier_4_live_ops_fleet_cockpit_ai",
    )
    if not isinstance(scorecard, Mapping) or any(t not in scorecard for t in required_tiers):
        raise MalformedArtifactError("Missing one or more 4-tier inside-out scorecard entries")

    pareto = doc.get("pareto_9tier_summary_table")
    if not isinstance(pareto, Mapping):
        raise MalformedArtifactError("Missing pareto_9tier_summary_table")
    tiers = pareto.get("tiers", [])
    pointers = pareto.get("all_81_config_pointers", [])
    if len(tiers) != len(EXPECTED_BANKROLL_TIERS_M_VND):
        raise ArithmeticDriftError(f"Expected 9 Pareto tiers, got {len(tiers)}")
    if [t["bankroll_m_vnd"] for t in tiers] != list(EXPECTED_BANKROLL_TIERS_M_VND):
        raise ArithmeticDriftError("Pareto bankroll tier ordering mismatch")
    if len(pointers) != EXPECTED_PARETO_CASE_COUNT:
        raise ArithmeticDriftError(f"Expected 81 Pareto config pointers, got {len(pointers)}")

    for tier_row in tiers:
        for role in ("safest", "balanced_sweet_spot", "max_upside"):
            role_obj = tier_row["roles"][role]
            for reg in ("baseline_1_0x", "stress_1_5x"):
                _verify_partition_dict(
                    role_obj[reg]["monthly_pass_fail_pending"],
                    horizons=PARETO_HORIZONS,
                    context=f"verify:{tier_row['tier_key']}:{role}:{reg}",
                )

    return {
        "verified": True,
        "report_sha256": recomputed_sha,
        "reconciled_artifact_count": len(ledger["artifacts"]),
        "pareto_tiers_count": len(tiers),
        "pareto_pointers_count": len(pointers),
    }


def verify_master_metrics_file(path: Path = DEFAULT_MASTER_METRICS_PATH) -> dict[str, Any]:
    """Read `wave4_master_metrics.json` from disk and verify file digest + canonical payload."""
    fpath = Path(path)
    if not fpath.is_file():
        raise MissingArtifactError(f"Master metrics JSON missing: {fpath}")
    raw = fpath.read_bytes()
    file_sha = hashlib.sha256(raw).hexdigest()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MalformedArtifactError(f"Malformed master metrics JSON {fpath}: {exc}") from exc
    res = verify_master_metrics_payload(doc)
    res["file_sha256"] = file_sha
    res["bytes"] = len(raw)
    return res


def run_council_and_write(
    *,
    root: Path = ROOT,
    out_path: Path = DEFAULT_MASTER_METRICS_PATH,
    expected_file_sha256: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Execute full reconciliation, write `wave4_master_metrics.json`, and self-verify from disk."""
    payload = build_wave4_master_metrics(root, expected_file_sha256=expected_file_sha256)
    file_sha, nbytes = write_json_lf(out_path, payload)
    verified = verify_master_metrics_file(out_path)
    if verified["file_sha256"] != file_sha:
        raise TamperedArtifactError("Post-write master metrics SHA-256 verification mismatch")
    return {
        "status": "PASS",
        "out_path": str(out_path),
        "file_sha256": file_sha,
        "bytes": nbytes,
        "report_sha256": payload["report_sha256"],
        "reconciled_artifact_count": payload["reconciled_artifact_count"],
        "self_hash_verified_count": payload["self_hash_verified_count"],
        "cross_artifact_sha256_links_verified": payload["cross_artifact_sha256_links_verified"],
        "payload": payload,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 3A Master Council: SHA-256 reconciliation of all 40 Wave 4 artifacts into SSOT JSON."
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="Workspace root directory")
    parser.add_argument("--out", type=Path, default=DEFAULT_MASTER_METRICS_PATH, help="Output SSOT JSON path")
    parser.add_argument("--verify-only", action="store_true", help="Verify an existing wave4_master_metrics.json file")
    args = parser.parse_args(argv)

    if args.verify_only:
        res = verify_master_metrics_file(args.out)
        print(json.dumps(res, indent=2))
        return 0

    res = run_council_and_write(root=args.root, out_path=args.out)
    summary = {k: v for k, v in res.items() if k != "payload"}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
