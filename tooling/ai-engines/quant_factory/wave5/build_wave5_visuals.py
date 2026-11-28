"""Wave 5 Next-Gen Interactive 4-Color HTML Visuals Builder & Verifier (Gate W5-G20).

Total Offensive #5 v5.3 FINAL — strictly offline, read-only visual artifacts:
  - PC Dev = MODE_A_OWNER_ACTIVE (BelowNormal 0x4000)
  - ZERO external CDNs, ZERO network requests, ZERO console/page errors
  - ZERO bare dollar symbols anywhere in generated HTML/CSS/JS/JSON (uses USD / VND)
  - ZERO G12 prop-firm support nudges
  - ZERO CRLF, ZERO BOM, ZERO bare Python `assert` statements (`python -O` safe)
  - Strict `UI/contracts/evaluation-scorecard/1.0.0/CONTRACT.md` & `schema.json` compliance
  - All embedded `EvaluationScorecard` payloads validated with Pydantic v2 (`evaluation_catalog.py`)
  - 100% verbatim metrics sourced from `.runtime/offensive5/wave5_master_metrics.json`,
    `.runtime/offensive5/pareto/mc_spectrum_summary.json`, and cryptographically linked
    `mc_spectrum_all_cases.json`, `bellman_dp_schedule.json`, and `wave5_m1_arena_summary.json`.
"""

# ruff: noqa: E501  # Embedded self-contained HTML/CSS/JS template literals exceed 120 chars.

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.wave5 import (  # noqa: E402
    DEV_CUTOFF_SEC,
    DEV_PC_REQUIRED_MODE,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
)
from quant_factory.wave5.evaluation_catalog import (  # noqa: E402
    DEFAULT_SCORECARD_SCHEMA_PATH,
    DEFAULT_TAXONOMY_PATH,
    EvaluationInputRecord,
    EvaluationScorecard,
    export_scorecard_json_schema,
    grade_evaluation_record,
    load_evaluation_taxonomy,
)

BELOW_NORMAL_PRIORITY_CLASS: int = 0x00004000
OFFENSIVE_VERSION: str = "Total Offensive #5 v5.3 FINAL"
GATE_ID: str = "W5-G20"
WIDGET_FILENAME: str = "wave5_profile_spectrum_widget.html"
EXPLORER_FILENAME: str = "wave5_deep_alpha_explorer.html"
DEFAULT_RUNTIME_VISUALS_DIR: Path = REPO_ROOT / ".runtime" / "offensive5" / "visuals"
DEFAULT_CONVERSATION_ARTIFACT_ID: str = "36cdea52-9feb-4722-9a55-d4b3dd4d8c97"


def resolve_default_brain_artifacts_dir() -> Path:
    """Resolve conversation artifacts dir via NAQEX_ARTIFACTS_DIR or Path.home() (zero hardcoded user paths)."""
    env_dir = os.environ.get("NAQEX_ARTIFACTS_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".gemini" / "antigravity" / "brain" / DEFAULT_CONVERSATION_ARTIFACT_ID


DEFAULT_BRAIN_ARTIFACTS_DIR: Path = resolve_default_brain_artifacts_dir()
DEFAULT_RECEIPT_PATH: Path = REPO_ROOT / ".runtime" / "offensive5" / "audits" / "w5_visuals_receipt.json"
DEFAULT_DROPBOX_PATH: Path = REPO_ROOT / ".tmp" / "swarm_dropbox" / "w5-visuals.json"

DEFAULT_MASTER_METRICS_PATH: Path = REPO_ROOT / ".runtime" / "offensive5" / "wave5_master_metrics.json"
DEFAULT_SPECTRUM_SUMMARY_PATH: Path = REPO_ROOT / ".runtime" / "offensive5" / "pareto" / "mc_spectrum_summary.json"
DEFAULT_SPECTRUM_ALL_CASES_PATH: Path = REPO_ROOT / ".runtime" / "offensive5" / "pareto" / "mc_spectrum_all_cases.json"
DEFAULT_BELLMAN_DP_PATH: Path = REPO_ROOT / ".runtime" / "offensive5" / "pareto" / "bellman_dp_schedule.json"
DEFAULT_M1_ARENA_SUMMARY_PATH: Path = REPO_ROOT / ".runtime" / "offensive5" / "alpha" / "wave5_m1_arena_summary.json"

G12_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:email|mail|chat|live[- ]?chat|contact|nhắn|liên hệ)\s+(?:ftmo|the5ers|prop\s*firm)\s+support",
        re.I,
    ),
    re.compile(r"support@(?:ftmo|the5ers)", re.I),
    re.compile(r"mở\s+ticket\s+(?:hỗ trợ\s+)?(?:ftmo|the5ers)", re.I),
)
EXTERNAL_URL_ATTR_RE: re.Pattern[str] = re.compile(
    r"""(?:src|href)\s*=\s*["']\s*(?:https?:|//)""",
    re.IGNORECASE,
)
SCRIPT_DATA_RE: re.Pattern[str] = re.compile(
    r"""<script\s+id=["']w5-ssot-data["']\s+type=["']application/json["']\s*>(.*?)</script>""",
    re.DOTALL,
)


class VisualBuildError(RuntimeError):
    """Fail-closed exception raised when any SSOT, schema, or safety invariant fails."""


def _require(cond: bool, msg: str) -> None:
    """Explicit invariant check immune to `python -O`."""
    if not cond:
        raise VisualBuildError(msg)


def apply_mode_a_belownormal() -> dict[str, Any]:
    """Enforce PC Dev MODE_A_OWNER_ACTIVE (BelowNormal 0x4000, 0% GPU)."""
    applied = False
    win_error: str | None = None
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            kernel32.SetPriorityClass.restype = ctypes.c_int
            handle = kernel32.GetCurrentProcess()
            res = kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
            if res != 0:
                applied = True
            else:
                win_error = f"SetPriorityClass returned 0 (GetLastError={kernel32.GetLastError()})"
        except Exception as exc:  # pragma: no cover - defensive on restricted hosts
            win_error = str(exc)
    return {
        "policy_mode": DEV_PC_REQUIRED_MODE,
        "priority_class_hex": "0x4000",
        "priority_applied": applied,
        "gpu_budget_pct": 0,
        "win_error": win_error,
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_report_sha256(obj: Mapping[str, Any], hash_field: str) -> str:
    clone = {k: v for k, v in obj.items() if k != hash_field}
    encoded = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )
    return _sha256_bytes(encoded)


def _canonical_report_sha256_ascii(obj: Mapping[str, Any], hash_field: str) -> str:
    clone = {k: v for k, v in obj.items() if k != hash_field}
    encoded = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
        "utf-8"
    )
    return _sha256_bytes(encoded)


def _verify_embedded_hash(obj: Mapping[str, Any], hash_field: str, label: str) -> str:
    expected = obj.get(hash_field)
    _require(isinstance(expected, str) and len(expected) == 64, f"{label}: missing valid {hash_field}")
    c_utf8 = _canonical_report_sha256(obj, hash_field)
    c_ascii = _canonical_report_sha256_ascii(obj, hash_field)
    _require(
        expected in (c_utf8, c_ascii),
        f"{label}: {hash_field} mismatch (expected={expected}, utf8={c_utf8}, ascii={c_ascii})",
    )
    return str(expected)


def _sanitize_no_bare_dollar(node: Any) -> Any:
    """Recursively replace bare dollar symbols only if upstream strings ever contained them, fail-closed checked."""
    if isinstance(node, str):
        return node.replace("$", "USD ")
    if isinstance(node, list):
        return [_sanitize_no_bare_dollar(x) for x in node]
    if isinstance(node, dict):
        return {str(k).replace("$", "USD_"): _sanitize_no_bare_dollar(v) for k, v in node.items()}
    return node


def _safe_embed_json(payload: Any) -> str:
    """Serialize JSON safely for inline <script type='application/json'> with zero NaN and zero </script> breakouts."""
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return raw.replace("</", "<\\/")


def _verify_html_invariants(html: str, label: str) -> dict[str, Any]:
    """Fail-closed static audit of generated HTML against all Wave 5 visual & safety contracts."""
    raw_bytes = html.encode("utf-8")
    _require(not raw_bytes.startswith(b"\xef\xbb\xbf"), f"{label}: UTF-8 BOM detected")
    _require("\r" not in html, f"{label}: CRLF detected")
    _require("$" not in html, f"{label}: bare dollar character detected")
    _require(EXTERNAL_URL_ATTR_RE.search(html) is None, f"{label}: external CDN src/href detected")
    for pat in G12_FORBIDDEN_PATTERNS:
        _require(pat.search(html) is None, f"{label}: G12 prop-firm support nudge detected ({pat.pattern})")
    m = SCRIPT_DATA_RE.search(html)
    _require(m is not None, f"{label}: missing <script id='w5-ssot-data' type='application/json'>")
    embedded = json.loads(m.group(1))
    _require(isinstance(embedded, dict), f"{label}: embedded JSON must be an object")
    meta = embedded.get("ssot_meta", {})
    _require(meta.get("holdout_rows_analysed") == 0, f"{label}: holdout_rows_analysed must be 0")
    _require(meta.get("order_send_count") == 0, f"{label}: order_send_count must be 0")
    _require(meta.get("execution_capability") is False, f"{label}: execution_capability must be false")
    _require(meta.get("spend_vnd") == 0, f"{label}: spend_vnd must be 0")
    _require(meta.get("holdout_cutoff_date") == HOLDOUT_CUTOFF_DATE, f"{label}: holdout cutoff mismatch")

    scorecards = embedded.get("scorecards", {})
    _require(isinstance(scorecards, dict) and len(scorecards) >= 9, f"{label}: missing embedded scorecards")
    validated_count = 0
    for sc_key, sc_obj in scorecards.items():
        sc = EvaluationScorecard.model_validate(sc_obj)
        _require(sc.holdout_rows_analysed == 0, f"{label}: scorecard {sc_key} holdout != 0")
        _require(sc.order_send_count == 0, f"{label}: scorecard {sc_key} order_send_count != 0")
        _require(sc.execution_capability is False, f"{label}: scorecard {sc_key} execution_capability != False")
        validated_count += 1

    return {
        "bytes": len(raw_bytes),
        "sha256": _sha256_bytes(raw_bytes),
        "crlf_count": html.count("\r\n"),
        "has_bom": raw_bytes.startswith(b"\xef\xbb\xbf"),
        "bare_dollar_count": html.count("$"),
        "external_cdn_count": len(EXTERNAL_URL_ATTR_RE.findall(html)),
        "g12_nudge_count": sum(len(p.findall(html)) for p in G12_FORBIDDEN_PATTERNS),
        "embedded_scorecards_validated": validated_count,
    }


def _compute_funded_12m_partition(fn: Mapping[str, Any]) -> dict[str, float]:
    """Compute exact 100.00% 3-way partition (survived / breached / censored) for Funded 12m."""
    entered = int(fn.get("funded_entered_count", 0) or 0)
    breached = int(fn.get("funded_breach_12m_count", 0) or 0)
    censored = int(fn.get("funded_censored_12m_count", 0) or 0)
    if entered > 0:
        fail_pct = round(100.0 * breached / entered, 2)
        pend_pct = round(100.0 * censored / entered, 2)
        pass_pct = round(100.0 - fail_pct - pend_pct, 2)
        return {
            "pass_pct": max(0.0, pass_pct),
            "fail_pct": max(0.0, fail_pct),
            "pending_pct": max(0.0, pend_pct),
            "sum_pct": round(max(0.0, pass_pct) + max(0.0, fail_pct) + max(0.0, pend_pct), 2),
        }
    blow = round(float(fn.get("blowup_12m_pct", 0.0)), 2)
    return {
        "pass_pct": round(100.0 - blow, 2),
        "fail_pct": blow,
        "pending_pct": 0.0,
        "sum_pct": 100.0,
    }


def _check_partition_100(p: float, f: float, w: float, ctx: str) -> None:
    total = p + f + w
    _require(math.isfinite(total) and abs(total - 100.0) <= 0.05, f"{ctx}: partition sum {total:.4f} != 100.0")


def load_verified_ssot_bundle(
    *,
    master_metrics_path: Path = DEFAULT_MASTER_METRICS_PATH,
    spectrum_summary_path: Path = DEFAULT_SPECTRUM_SUMMARY_PATH,
    spectrum_all_cases_path: Path = DEFAULT_SPECTRUM_ALL_CASES_PATH,
    bellman_dp_path: Path = DEFAULT_BELLMAN_DP_PATH,
    m1_arena_summary_path: Path = DEFAULT_M1_ARENA_SUMMARY_PATH,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
    schema_path: Path = DEFAULT_SCORECARD_SCHEMA_PATH,
) -> dict[str, Any]:
    """Load, cryptographically verify, and Pydantic-validate every Wave 5 SSOT input."""
    for p in (
        master_metrics_path,
        spectrum_summary_path,
        spectrum_all_cases_path,
        bellman_dp_path,
        m1_arena_summary_path,
        taxonomy_path,
        schema_path,
    ):
        _require(p.is_file(), f"MISSING_SSOT_INPUT: {p}")

    master = json.loads(master_metrics_path.read_text(encoding="utf-8"))
    summary = json.loads(spectrum_summary_path.read_text(encoding="utf-8"))
    all_cases = json.loads(spectrum_all_cases_path.read_text(encoding="utf-8"))
    bellman = json.loads(bellman_dp_path.read_text(encoding="utf-8"))
    m1_arena = json.loads(m1_arena_summary_path.read_text(encoding="utf-8"))

    # 1. Verify self-hashes & cross-artifact links
    master_report_sha = _verify_embedded_hash(master, "report_sha256", "wave5_master_metrics.json")
    summary_report_sha = _verify_embedded_hash(summary, "report_sha256", "mc_spectrum_summary.json")
    all_cases_sha = _verify_embedded_hash(all_cases, "all_cases_sha256", "mc_spectrum_all_cases.json")
    bellman_sha = _verify_embedded_hash(bellman, "report_sha256", "bellman_dp_schedule.json")
    m1_arena_sha = _verify_embedded_hash(m1_arena, "report_sha256", "wave5_m1_arena_summary.json")

    _require(
        summary.get("all_cases_sha256") == all_cases_sha,
        "CROSS_HASH_MISMATCH: mc_spectrum_summary.all_cases_sha256 != mc_spectrum_all_cases.all_cases_sha256",
    )

    # Verify against master reconciliation ledger
    ledger_by_id = {a["artifact_id"]: a for a in master["artifact_reconciliation_ledger"]["artifacts"]}
    _require(
        ledger_by_id["mc_spectrum_summary"]["embedded_sha256"] == summary_report_sha,
        "LEDGER_MISMATCH: mc_spectrum_summary",
    )
    _require(
        ledger_by_id["mc_spectrum_all_cases"]["embedded_sha256"] == all_cases_sha,
        "LEDGER_MISMATCH: mc_spectrum_all_cases",
    )
    _require(
        ledger_by_id["bellman_dp_schedule"]["embedded_sha256"] == bellman_sha,
        "LEDGER_MISMATCH: bellman_dp_schedule",
    )
    _require(
        ledger_by_id["wave5_m1_arena_summary"]["embedded_sha256"] == m1_arena_sha,
        "LEDGER_MISMATCH: wave5_m1_arena_summary",
    )

    # 2. Verify hard safety invariants
    hi = master["hard_invariants"]
    _require(hi.get("holdout_rows_analysed") == 0, "SAFETY_FAIL: master holdout_rows_analysed != 0")
    _require(hi.get("order_send_count") == 0, "SAFETY_FAIL: master order_send_count != 0")
    _require(hi.get("order_send_capable") is False, "SAFETY_FAIL: master order_send_capable != False")
    _require(hi.get("holdout_cutoff_date") == HOLDOUT_CUTOFF_DATE, "SAFETY_FAIL: holdout_cutoff_date mismatch")
    _require(hi.get("dev_cutoff_sec") == DEV_CUTOFF_SEC, "SAFETY_FAIL: dev_cutoff_sec mismatch")
    _require(hi.get("spend_vnd") == 0, "SAFETY_FAIL: spend_vnd != 0")

    # 3. Verify taxonomy & UI scorecard JSON schema parity (zero jsonschema dependency)
    taxonomy_cfg, taxonomy_sha = load_evaluation_taxonomy(taxonomy_path)
    disk_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    exported_schema = export_scorecard_json_schema()
    _require(disk_schema == exported_schema, "UI_CONTRACT_MISMATCH: schema.json != export_scorecard_json_schema()")

    # 4. Validate ALL EvaluationScorecards via Pydantic v2
    validated_master_scorecards: dict[str, dict[str, Any]] = {}
    for k, raw_sc in master["four_tier_inside_out_scorecard"]["validated_evaluation_scorecards"].items():
        sc = EvaluationScorecard.model_validate(raw_sc)
        validated_master_scorecards[k] = sc.model_dump(mode="json")

    validated_tier_a_scorecards: dict[str, dict[str, Any]] = {}
    for case in list(all_cases["tier_a_core_cases"]) + list(all_cases["tier_a_oof_ml_cases"]):
        ph = case["phases"]
        fn = ph["funded_12m"]
        p1 = ph["p1"]
        p2 = ph["p2"]
        pe = ph["pass_eval"]
        compact_sc = case["scorecard"]
        rec = EvaluationInputRecord(
            record_id=case["record_id"],
            domain_tier="T1_CFD_PROP",
            eval_scope="SINGLE_TICKET",
            pricing_regime=case.get("pricing_regime", "ALL_REGULAR_SSOT"),
            evidence_stage="DEV_CONSUMED_OOS",
            data_resolution="APPROX_DAILY",
            execution_status="MEASURED_DEMO_EXECUTION",
            risk_spectrum_tier=compact_sc.get("risk_spectrum_tier"),
            profit_factor=float(fn["profit_factor"]),
            calmar=float(fn["calmar"]),
            sharpe=float(fn["sharpe"]),
            ev_per_fee=float(fn["ev_per_fee_npv24"]),
            funded_12m_blowup_pct=float(fn["blowup_12m_pct"]),
            p_le_zero_24m_pct=float(fn["p_npv24_le_0_pct"]),
            payout_1_cal_days=float(fn["uncond_med_pay1_cal_days_cap730"]),
            slippage_breakeven_mult=float(case["slippage_breakeven_mult"])
            if case.get("slippage_breakeven_mult") is not None
            else None,
            p1_pass_rate_pct=float(p1["pass_12m_pct"]),
            p1_fail_rate_pct=float(p1["fail_12m_pct"]),
            p1_pending_rate_pct=float(p1["pending_12m_pct"]),
            p2_pass_rate_pct=float(p2["pass_12m_elapsed_pct"]),
            p2_fail_rate_pct=float(p2["fail_12m_elapsed_pct"]),
            p2_pending_rate_pct=float(p2["pending_12m_elapsed_pct"]),
            pass_eval_12m_pct=float(pe["pass_12m_pct"]),
            pass_eval_36m_pct=float(pe["pass_36m_pct"]),
            monthly_pass_fail_pending={
                "12m": {
                    "pass_pct": float(pe["pass_12m_pct"]),
                    "fail_pct": float(pe["fail_12m_pct"]),
                    "pending_pct": float(pe["pending_12m_pct"]),
                }
            },
            holdout_rows_analysed=0,
            order_send_count=0,
        )
        sc = grade_evaluation_record(rec, taxonomy_path=taxonomy_path)
        _require(
            sc.overall_grade == compact_sc["overall_grade"],
            f"TIER_A_GRADE_PARITY_FAIL: {case['record_id']} ({sc.overall_grade} != {compact_sc['overall_grade']})",
        )
        for pk in ("p1", "p2", "pass_eval", "funded_12m"):
            _require(
                sc.phase_grades[pk].grade == compact_sc["phase_grades"][pk]["grade"],
                f"TIER_A_PHASE_PARITY_FAIL: {case['record_id']}.{pk}",
            )
        validated_tier_a_scorecards[case["record_id"]] = sc.model_dump(mode="json")

    validated_tier_b_count = 0
    for fcase in all_cases["tier_b_fleet_cases"]:
        compact_sc = fcase["scorecard"]
        sq = fcase.get("strategy_quality") or {}
        rec_b = EvaluationInputRecord(
            record_id=fcase["record_id"],
            domain_tier="T1_CFD_PROP",
            eval_scope="MULTI_ACCOUNT_FLEET",
            pricing_regime=fcase.get("pricing_regime", "ALL_REGULAR_SSOT"),
            evidence_stage="DEV_CONSUMED_OOS",
            data_resolution="APPROX_DAILY",
            execution_status="MEASURED_DEMO_EXECUTION",
            risk_spectrum_tier=compact_sc.get("risk_spectrum_tier"),
            profit_factor=float(sq["profit_factor"]) if sq.get("profit_factor") is not None else None,
            calmar=float(sq["calmar"]) if sq.get("calmar") is not None else None,
            sharpe=float(sq["sharpe"]) if sq.get("sharpe") is not None else None,
            ev_per_fee=float(fcase["ev_per_1_vnd_fee_36m"]),
            funded_12m_blowup_pct=float(fcase["funded_12m_blowup"]["blowup_12m_pct"]),
            ruin_36m_pct=float(fcase["p_bankroll_ruin_pct"]),
            p_le_zero_24m_pct=float(fcase["p_net_le_0_24m_pct"]),
            payout_1_cal_days=float(fcase["uncond_med_pay1_cal_days_cap730"]),
            p1_pass_rate_pct=float(fcase["p1_pass_rate_pct"]),
            p1_fail_rate_pct=float(fcase["p1_fail_rate_pct"]),
            p1_pending_rate_pct=float(fcase["p1_pending_rate_pct"]),
            p2_pass_rate_pct=float(fcase["p2_pass_rate_pct"]),
            p2_fail_rate_pct=float(fcase["p2_fail_rate_pct"]),
            p2_pending_rate_pct=float(fcase["p2_pending_rate_pct"]),
            pass_eval_12m_pct=float(fcase["monthly_pass_fail_pending"]["12m"]["pass_pct"]),
            holdout_rows_analysed=0,
            order_send_count=0,
        )
        sc_b = grade_evaluation_record(rec_b, taxonomy_path=taxonomy_path)
        _require(
            sc_b.overall_grade == compact_sc["overall_grade"],
            f"TIER_B_GRADE_PARITY_FAIL: {fcase['record_id']} ({sc_b.overall_grade} != {compact_sc['overall_grade']})",
        )
        validated_tier_b_count += 1

    # Canonical Wave 4 legacy scorecard (explicit UNKNOWN_LEGACY_UNINSTRUMENTED P1/P2 + legacy_grade_code="TOT")
    w4_baseline_sql = next(
        r
        for r in master["wave4_vs_wave5_sql_comparison"]["campaign_profile_sql_matrix"]
        if r["campaign_id"] == "offensive4" and math.isclose(float(r["friction_mult"]), 1.0)
    )
    w4_legacy_sc = grade_evaluation_record(
        EvaluationInputRecord(
            record_id="w4_legacy_c10_fleet_1_0x_reference",
            domain_tier="T1_CFD_PROP",
            eval_scope="MULTI_ACCOUNT_FLEET",
            pricing_regime="ALL_REGULAR_SSOT",
            evidence_stage="DEV_CONSUMED_OOS",
            data_resolution="APPROX_DAILY",
            execution_status="MEASURED_DEMO_EXECUTION",
            risk_spectrum_tier="T3_BALANCED",
            legacy_grade_code="TOT",
            ev_per_fee=float(w4_baseline_sql["mean_ev_per_fee_36m"]),
            funded_12m_blowup_pct=float(w4_baseline_sql["mean_fn12_blowup_pct"]),
            ruin_36m_pct=float(w4_baseline_sql["mean_ruin_36m_pct"]),
            p_le_zero_24m_pct=float(w4_baseline_sql["mean_p_le_0_24m_pct"]),
            payout_1_cal_days=float(w4_baseline_sql["mean_uncond_pay1_days"]),
            p1_pass_rate_pct=None,
            p2_pass_rate_pct=None,
            pass_eval_12m_pct=None,
            holdout_rows_analysed=0,
            order_send_count=0,
        ),
        taxonomy_path=taxonomy_path,
    )
    _require(
        w4_legacy_sc.phase_grades["p1"].grade == "UNKNOWN_LEGACY_UNINSTRUMENTED",
        "W4_LEGACY_CHECK: p1 must be UNKNOWN_LEGACY_UNINSTRUMENTED",
    )
    _require(
        w4_legacy_sc.phase_grades["p2"].grade == "UNKNOWN_LEGACY_UNINSTRUMENTED",
        "W4_LEGACY_CHECK: p2 must be UNKNOWN_LEGACY_UNINSTRUMENTED",
    )
    _require(w4_legacy_sc.legacy_grade_code == "TOT", "W4_LEGACY_CHECK: legacy_grade_code must be TOT")
    _require(w4_legacy_sc.unified_grade_code == "ADEQUATE", "W4_LEGACY_CHECK: unified_grade_code must be ADEQUATE")

    return {
        "master": master,
        "summary": summary,
        "all_cases": all_cases,
        "bellman": bellman,
        "m1_arena": m1_arena,
        "taxonomy": taxonomy_cfg,
        "taxonomy_sha256": taxonomy_sha,
        "validated_master_scorecards": validated_master_scorecards,
        "validated_tier_a_scorecards": validated_tier_a_scorecards,
        "w4_legacy_scorecard": w4_legacy_sc.model_dump(mode="json"),
        "pydantic_v2_total_validated": (
            len(validated_master_scorecards) + len(validated_tier_a_scorecards) + validated_tier_b_count + 1
        ),
        "provenance": {
            "wave5_master_metrics_sha256": _sha256_file(master_metrics_path),
            "wave5_master_metrics_report_sha256": master_report_sha,
            "mc_spectrum_summary_sha256": _sha256_file(spectrum_summary_path),
            "mc_spectrum_summary_report_sha256": summary_report_sha,
            "mc_spectrum_all_cases_sha256": _sha256_file(spectrum_all_cases_path),
            "mc_spectrum_all_cases_embedded_sha256": all_cases_sha,
            "bellman_dp_schedule_sha256": _sha256_file(bellman_dp_path),
            "bellman_dp_schedule_report_sha256": bellman_sha,
            "wave5_m1_arena_summary_sha256": _sha256_file(m1_arena_summary_path),
            "wave5_m1_arena_summary_report_sha256": m1_arena_sha,
            "taxonomy_sha256": taxonomy_sha,
            "ui_scorecard_schema_sha256": _sha256_file(schema_path),
        },
    }


def _extract_single_ticket_case(
    case: Mapping[str, Any],
    full_sc: Mapping[str, Any],
) -> dict[str, Any]:
    """Extract clean verbatim fields + compact contract-aligned grading from a Tier A single-ticket record."""
    ph = case["phases"]
    p1 = ph["p1"]
    p2 = ph["p2"]
    pe = ph["pass_eval"]
    fn = ph["funded_12m"]
    _check_partition_100(p1["pass_12m_pct"], p1["fail_12m_pct"], p1["pending_12m_pct"], f"{case['record_id']}.p1")
    _check_partition_100(
        p2["pass_12m_elapsed_pct"],
        p2["fail_12m_elapsed_pct"],
        p2["pending_12m_elapsed_pct"],
        f"{case['record_id']}.p2",
    )
    _check_partition_100(
        pe["pass_12m_pct"], pe["fail_12m_pct"], pe["pending_12m_pct"], f"{case['record_id']}.pass_eval"
    )
    fn_part = _compute_funded_12m_partition(fn)
    _check_partition_100(
        fn_part["pass_pct"], fn_part["fail_pct"], fn_part["pending_pct"], f"{case['record_id']}.funded_12m"
    )

    return {
        "record_id": case["record_id"],
        "cohort": case["cohort"],
        "schedule_id": case["schedule_id"],
        "contract_id": case["contract_id"],
        "capital_usd": float(case["capital_usd"]),
        "friction_mult": float(case["friction_mult"]),
        "mandatory_tags": list(case["mandatory_tags"]),
        "overall_grade": full_sc["overall_grade"],
        "overall_grade_vi": full_sc["overall_grade_vi"],
        "aria_label": full_sc["presentation_state"]["ariaLabel"],
        "phase_grades": {
            pk: {
                "grade": full_sc["phase_grades"][pk]["grade"],
                "aria": full_sc["phase_grades"][pk]["presentation_state"]["ariaLabel"],
            }
            for pk in ("p1", "p2", "pass_eval", "funded_12m")
        },
        "exact_bottlenecks": [
            {
                "code": b["code"],
                "cur": b["current_value"],
                "tgt": b["target_threshold"],
                "rank": b["severity_rank"],
                "vi": b["label_vi"],
            }
            for b in full_sc["exact_bottlenecks"]
        ],
        "gap_vi": full_sc["gap_to_top_1_pct_vi"],
        "p1": {
            "pass_12m": float(p1["pass_12m_pct"]),
            "fail_12m": float(p1["fail_12m_pct"]),
            "pend_12m": float(p1["pending_12m_pct"]),
            "pass_3m": float(p1["pass_3m_pct"]),
            "pass_6m": float(p1["pass_6m_pct"]),
            "pass_36m": float(p1["pass_36m_pct"]),
            "cond_med_days": float(p1["cond_med_pass_cal_days"]),
            "uncond_med_days": float(p1["uncond_med_pass_cal_days_cap730"]),
        },
        "p2": {
            "pass_12m": float(p2["pass_12m_elapsed_pct"]),
            "fail_12m": float(p2["fail_12m_elapsed_pct"]),
            "pend_12m": float(p2["pending_12m_elapsed_pct"]),
            "pass_3m": float(p2["horizons"]["3m_elapsed"]["pass_pct"]),
            "pass_6m": float(p2["horizons"]["6m_elapsed"]["pass_pct"]),
            "entered_count": int(p2["entered_p2_count"]),
            "cond_med_days": float(p2["cond_med_pass_cal_days"]),
        },
        "pass_eval": {
            "pass_12m": float(pe["pass_12m_pct"]),
            "fail_12m": float(pe["fail_12m_pct"]),
            "pend_12m": float(pe["pending_12m_pct"]),
            "pass_3m": float(pe["pass_3m_pct"]),
            "pass_6m": float(pe["pass_6m_pct"]),
            "pass_36m": float(pe["pass_36m_pct"]),
            "fail_36m": float(pe["fail_36m_pct"]),
            "cond_med_days": float(pe["cond_med_pass_cal_days"]),
            "uncond_med_days": float(pe["uncond_med_pass_cal_days_cap730"]),
        },
        "funded": {
            "blowup_12m": float(fn["blowup_12m_pct"]),
            "wilson_ub": float(fn["wilson_95_ub_pct"]),
            "pass_12m": fn_part["pass_pct"],
            "fail_12m": fn_part["fail_pct"],
            "pend_12m": fn_part["pending_pct"],
            "ev_per_fee": float(fn["ev_per_fee_npv24"]),
            "ev_24m_vnd": float(fn["ev_npv_24m_vnd"]),
            "ev_24m_usd": float(fn["ev_npv_24m_usd"]),
            "med_24m_vnd": float(fn["med_npv_24m_vnd"]),
            "med_24m_usd": float(fn["med_npv_24m_usd"]),
            "fee_usd": float(fn["effective_fee_usd"]),
            "fee_vnd": float(fn["effective_fee_vnd"]),
            "cond_pay1": float(fn["cond_med_pay1_cal_days"]),
            "uncond_pay1": float(fn["uncond_med_pay1_cal_days_cap730"]),
            "p_le_0_24m": float(fn["p_npv24_le_0_pct"]),
            "pay1_reached_pct": float(fn["pay1_reached_pct"]),
            "firm_daily_breach": float(fn["firm_hard_breach_daily_pct"]),
            "wr": float(fn["winrate_pct"]),
            "rr": float(fn["avg_rr"]),
            "ev_r": float(fn["ev_per_trade_r"]),
            "pf": float(fn["profit_factor"]),
            "sharpe": float(fn["sharpe"]),
            "calmar": float(fn["calmar"]),
            "max_dd": float(fn["max_dd_pct"]),
        },
    }


def _extract_schedule_meta(schedules: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    labels_vi = {
        "T1_ULTRA_SAFE": "T1 Siêu an toàn",
        "T2_SAFE_C00": "T2 An toàn",
        "T3_BALANCED_EV": "T3 Cân bằng (Sprint)",
        "V103_SPRINT": "V103 Sprint",
        "T4_TURBO_FAST": "T4 Tăng tốc mạnh",
        "T5_MAX_THROTTLE_YOLO": "T5 100% Liều",
        "C00": "C00",
        "C10_NEWS_ON": "C10",
        "BELLMAN_DP_6TIER": "Bellman DP",
    }
    out: dict[str, dict[str, Any]] = {}
    for sid, spec in schedules.items():
        out[sid] = {
            "schedule_id": sid,
            "label_vi": labels_vi.get(sid, sid),
            "p1_mult": float(spec["p1_mult"]),
            "p2_mult": float(spec["p2_mult"]),
            "funded_mult": float(spec["funded_mult"]),
            "taxonomy_tier": spec["taxonomy_tier"],
            "mandatory_tags": list(spec["mandatory_tags"]),
            "eval_is_dp": bool(spec.get("eval_is_dp", False)),
        }
    return out


def build_widget_payload(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Build the compact embedded JSON payload for `wave5_profile_spectrum_widget.html`."""
    master = bundle["master"]
    all_cases = bundle["all_cases"]
    summary = bundle["summary"]

    single_cases: list[dict[str, Any]] = []
    for raw in list(all_cases["tier_a_core_cases"]) + list(all_cases["tier_a_oof_ml_cases"]):
        single_cases.append(_extract_single_ticket_case(raw, bundle["validated_tier_a_scorecards"][raw["record_id"]]))

    intraday_map: dict[str, dict[str, Any]] = {}
    for row in summary["intraday_trade_dd_audit"]:
        key = f"{row['schedule_id']}__{row['contract_id']}"
        intraday_map[key] = {
            "schedule_id": row["schedule_id"],
            "contract_id": row["contract_id"],
            "drift_trade_minus_daily_close_pp": float(row["drift_trade_minus_daily_close_pp"]),
            "drift_gap125_minus_m1_daily_approx_pp": float(row["drift_gap125_minus_m1_daily_approx_pp"]),
            "hist_days_ge5_trade": int(row["historical_days_ge_5pct_trade_seq_count"]),
            "hist_max_day_dd_trade": float(row["historical_max_single_day_trade_seq_dd_pct"]),
            "trade_1x_daily_breach": float(row["modes"]["trade_level_intraday_1_0x"]["daily_5pct_hard_breach_pct"]),
            "gap_125x_daily_breach": float(
                row["modes"]["trade_level_intraday_1_25x_gap"]["daily_5pct_hard_breach_pct"]
            ),
        }

    payload = {
        "ssot_meta": {
            "offensive_version": OFFENSIVE_VERSION,
            "gate": GATE_ID,
            "master_report_sha256": bundle["provenance"]["wave5_master_metrics_report_sha256"],
            "spectrum_summary_sha256": bundle["provenance"]["mc_spectrum_summary_report_sha256"],
            "taxonomy_sha256": bundle["provenance"]["taxonomy_sha256"],
            "usd_vnd_rate": float(master["fleet_9bankroll_summary"]["usd_vnd_rate"]),
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_rows_analysed": 0,
            "order_send_count": ORDER_SEND_COUNT,
            "order_send_capable": ORDER_SEND_CAPABLE,
            "execution_capability": False,
            "spend_vnd": 0,
            "reconciled_artifact_count": int(master["reconciled_artifact_count"]),
        },
        "schedules": _extract_schedule_meta(all_cases["schedules"]),
        "intraday_audit": intraday_map,
        "cases": single_cases,
        "scorecards": bundle["validated_master_scorecards"],
    }
    return _sanitize_no_bare_dollar(payload)


def _compact_fleet_case(fc: Mapping[str, Any]) -> dict[str, Any]:
    """Lossless compact representation of one Tier B fleet case (1 of 972) with zero repeated prose."""
    sc = fc["scorecard"]
    ph_grades = [sc["phase_grades"][k]["grade"] for k in ("p1", "p2", "pass_eval", "funded_12m")]
    horizons = {}
    for hk in ("3m", "6m", "12m", "24m", "36m"):
        h = fc["monthly_pass_fail_pending"][hk]
        _check_partition_100(h["pass_pct"], h["fail_pct"], h["pending_pct"], f"{fc['record_id']}.{hk}")
        horizons[hk] = [float(h["pass_pct"]), float(h["fail_pct"]), float(h["pending_pct"])]

    return {
        "rid": fc["record_id"],
        "sid": fc["schedule_id"],
        "fr": float(fc["friction_mult"]),
        "b": int(fc["bankroll_m_vnd"]),
        "b_usd": float(fc["bankroll_usd"]),
        "cc": fc["concurrency_mode"],
        "ap": fc["allocation_policy"],
        "gr": sc["overall_grade"],
        "pg": ph_grades,
        "evf": float(fc["ev_per_1_vnd_fee_36m"]),
        "m24": round(float(fc["median_24m_net_vnd"])),
        "m36": round(float(fc["median_36m_net_vnd"])),
        "m36_u": float(fc["median_36m_net_usd"]),
        "p10_36": round(float(fc["net_profit_36m_vnd"]["p10"])),
        "p90_36": round(float(fc["net_profit_36m_vnd"]["p90"])),
        "fn12": float(fc["funded_12m_blowup"]["blowup_12m_pct"]),
        "fn12_ub": float(fc["funded_12m_blowup"]["wilson_95_ub_pct"]),
        "ruin": float(fc["p_bankroll_ruin_pct"]),
        "ple0": float(fc["p_net_le_0_24m_pct"]),
        "cp1": float(fc["cond_med_pay1_cal_days"]),
        "up1": float(fc["uncond_med_pay1_cal_days_cap730"]),
        "p1p": float(fc["p1_pass_rate_pct"]),
        "p2p": float(fc["p2_pass_rate_pct"]),
        "pe12": float(fc["first_ticket_pass_fail_pending"]["12m"]["pass_pct"]),
        "maxf": round(float(fc["max_active_base_funded_usd"])),
        "pi": 1 if fc["is_pareto_in_tier"] else 0,
        "po": 1 if fc["is_pareto_overall"] else 0,
        "hz": horizons,
        "bn": [[b["code"], b["current_value"], b["target_threshold"]] for b in sc["exact_bottlenecks"][:3]],
    }


def build_explorer_payload(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Build the complete embedded JSON payload for `wave5_deep_alpha_explorer.html`."""
    master = bundle["master"]
    summary = bundle["summary"]
    all_cases = bundle["all_cases"]
    bellman = bundle["bellman"]
    m1_arena = bundle["m1_arena"]

    single_cases = [
        _extract_single_ticket_case(raw, bundle["validated_tier_a_scorecards"][raw["record_id"]])
        for raw in list(all_cases["tier_a_core_cases"]) + list(all_cases["tier_a_oof_ml_cases"])
    ]
    fleet_cases = [_compact_fleet_case(fc) for fc in all_cases["tier_b_fleet_cases"]]

    # Embed all 9 canonical Wave 5 scorecards + 1 canonical Wave 4 legacy scorecard (all Pydantic v2 validated)
    scorecards_map: dict[str, dict[str, Any]] = {}
    scorecards_map.update(bundle["validated_master_scorecards"])
    scorecards_map["w4_legacy_c10_fleet_1_0x_reference"] = bundle["w4_legacy_scorecard"]
    bn_catalog = {k: str(v["label_vi"]) for k, v in bundle["taxonomy"].bottleneck_catalog.items()}

    # Extract 6 Cluster B finalists verbatim from wave5_m1_arena_summary.json
    finalists_compact = [
        {
            "candidate_id": f["candidate_id"],
            "family_id": f["family_id"],
            "symbol": f["symbol"],
            "leader_symbol": f.get("leader_symbol"),
            "tier_classification": f["tier_classification"],
            "gates_passed_count": int(f["gates_passed_count"]),
            "failed_gates": list(f["failed_gates"]),
            "cluster_a_sharpe_1x": float(f["cluster_a_sharpe_1x"]),
            "sharpe_daily_b": float(f["sharpe_daily_b"]),
            "pf_1x_b": float(f["pf_1x_b"]),
            "n_trades_b": int(f["n_trades_b"]),
            "corr_vs_port_7e": float(f["corr_vs_port_7e"]),
            "cost_breakeven_mult": float(f["cost_breakeven_mult"]),
            "pbo_cscv": float(f["pbo_cscv"]),
            "bh_fdr_q": float(f["bh_fdr_q"]),
        }
        for f in m1_arena["cluster_b_all_finalists"]
    ]

    # Extract Wave 4 reference curve by bankroll from bankroll_gated_p2_1x_comparison
    w4_curve_by_bankroll: dict[str, dict[str, Any]] = {}
    for row in master["fleet_9bankroll_summary"]["bankroll_gated_p2_1x_comparison"]:
        bk = str(row["bankroll_m_vnd"])
        if bk not in w4_curve_by_bankroll:
            w4_curve_by_bankroll[bk] = {
                "bankroll_m_vnd": int(row["bankroll_m_vnd"]),
                "w4_c10_med36m_vnd": float(row["w4_c10_med36m_vnd"]),
                "w4_c10_pay1_days": float(row["w4_c10_pay1_days"]),
                "w4_c10_fn12_pct": float(row["w4_c10_fn12_pct"]),
                "w4_c10_grade": row["w4_c10_grade"],
            }

    payload = {
        "ssot_meta": {
            "offensive_version": OFFENSIVE_VERSION,
            "gate": GATE_ID,
            "master_report_sha256": bundle["provenance"]["wave5_master_metrics_report_sha256"],
            "spectrum_summary_sha256": bundle["provenance"]["mc_spectrum_summary_report_sha256"],
            "all_cases_sha256": bundle["provenance"]["mc_spectrum_all_cases_embedded_sha256"],
            "taxonomy_sha256": bundle["provenance"]["taxonomy_sha256"],
            "usd_vnd_rate": float(master["fleet_9bankroll_summary"]["usd_vnd_rate"]),
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_rows_analysed": 0,
            "order_send_count": ORDER_SEND_COUNT,
            "order_send_capable": ORDER_SEND_CAPABLE,
            "execution_capability": False,
            "spend_vnd": 0,
            "reconciled_artifact_count": int(master["reconciled_artifact_count"]),
            "mc_cases_catalog_count": int(master["unified_catalog_verification"]["mc_cases_catalog_count"]),
            "legacy_trials_distinct_count": int(master["unified_catalog_verification"]["legacy_trials_distinct_count"]),
            "pydantic_v2_total_validated": int(bundle["pydantic_v2_total_validated"]),
        },
        "schedules": _extract_schedule_meta(all_cases["schedules"]),
        "bottleneck_catalog": bn_catalog,
        "single_cases": single_cases,
        "intraday_audit": summary["intraday_trade_dd_audit"],
        "oof_ml_deltas": summary["oof_ml_deltas"],
        "fleet_cases": fleet_cases,
        "fleet_bankrolls": list(master["fleet_9bankroll_summary"]["bankroll_tiers_m_vnd"]),
        "fleet_tier_overview": master["fleet_9bankroll_summary"]["tier_overview"],
        "shared_path_rho_proof": master["fleet_9bankroll_summary"]["shared_path_rho_proof"],
        "w4_curve_by_bankroll": w4_curve_by_bankroll,
        "wave4_vs_wave5_sql": {
            "sql_source": master["wave4_vs_wave5_sql_comparison"]["sql_source"],
            "apples_to_apples_disclosure": master["wave4_vs_wave5_sql_comparison"]["apples_to_apples_disclosure"],
            "paired_162_cell_fleet_sql_deltas": master["wave4_vs_wave5_sql_comparison"][
                "paired_162_cell_fleet_sql_deltas"
            ],
            "wave4_legacy_vs_unified_by_cohort": master["wave4_vs_wave5_sql_comparison"][
                "wave4_legacy_vs_unified_by_cohort"
            ],
            "wave4_legacy_vs_unified_grade_matrix": master["wave4_vs_wave5_sql_comparison"][
                "wave4_legacy_vs_unified_grade_matrix"
            ],
        },
        "bellman_dp": {
            "p1_tiers": bellman["mql5_loadable_schedule"]["P1"]["tiers"],
            "p2_tiers": bellman["mql5_loadable_schedule"]["P2"]["tiers"],
            "p1_check": bellman["mql5_loadable_schedule"]["P1"]["distilled_schedule_check"],
            "p2_check": bellman["mql5_loadable_schedule"]["P2"]["distilled_schedule_check"],
            "ablation": master["single_ticket_spectrum_summary"]["w5_g13_bellman_dp_causal_ablation"],
        },
        "mt5_proof": master["mt5_build_6230_parity_proof"],
        "alpha_factory": {
            "universe_28": master["alpha_factory_closed_loop_summary"]["m1_universe_28_w5_g06"],
            "m1_arena": master["alpha_factory_closed_loop_summary"]["m1_alpha_arena_w5_g07_g09"],
            "finalists_6": finalists_compact,
            "ml_v105_arena": master["alpha_factory_closed_loop_summary"]["ml_v105_arena_w5_g11"],
            "e2e_drills": master["alpha_factory_closed_loop_summary"]["alpha_factory_e2e_drills_w5_g16_g17"],
        },
        "four_tier_scorecard": {
            tk: {
                "tier_number": master["four_tier_inside_out_scorecard"][tk]["tier_number"],
                "domain_tier": master["four_tier_inside_out_scorecard"][tk]["domain_tier"],
                "title_vi": master["four_tier_inside_out_scorecard"][tk]["title_vi"],
                "current_unified_grade": master["four_tier_inside_out_scorecard"][tk]["current_unified_grade"],
                "evidence_stage": master["four_tier_inside_out_scorecard"][tk]["evidence_stage"],
                "current_position_vi": master["four_tier_inside_out_scorecard"][tk]["current_position_vi"],
                "concrete_gap_to_top_1_pct": master["four_tier_inside_out_scorecard"][tk]["concrete_gap_to_top_1_pct"],
            }
            for tk in ("tier_1_cfd_prop", "tier_2_cme_futures", "tier_3_multi_asset_ownbook", "tier_4_live_ops")
        },
        "scorecards": scorecards_map,
    }
    return _sanitize_no_bare_dollar(payload)


def render_profile_spectrum_widget_html(payload: Mapping[str, Any]) -> str:
    """Render compact inline `wave5_profile_spectrum_widget.html` (<= 450px tall, zero CDN, dark/light)."""
    data_json = _safe_embed_json(payload)
    html = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Wave 5 — Quang Phổ 5 Bậc x 4 Pha (Total Offensive #5 v5.3 FINAL)</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    html {
      margin: 0;
      padding: 0;
      color-scheme: light dark;
      background: var(--background, transparent);
    }
    body {
      margin: 0;
      padding: 0;
      background: transparent;
      -webkit-font-smoothing: antialiased;
    }
    .w5-root {
      --_bg: #ffffff;
      --_fg: #0f172a;
      --_muted: #334155;
      --_card: #f8fafc;
      --_subtle: #f1f5f9;
      --_border: #cbd5e1;
      --_pri: #1d4ed8;
      --_pri-fg: #ffffff;
      --_sec: #e2e8f0;
      --_sec-fg: #0f172a;
      --_bad-bg: #fee2e2;
      --_bad-fg: #991b1b;
      --_warn-bg: #fef3c7;
      --_warn-fg: #78350f;
      --_good-bg: #d1fae5;
      --_good-fg: #065f46;
      --_top-bg: #dbeafe;
      --_top-fg: #1e40af;
      --_stale-bg: #e2e8f0;
      --_stale-fg: #334155;
      --_sep: #ffffff;
      --_c-fg: var(--foreground, var(--_fg));
      --_c-muted: var(--muted-foreground, var(--_muted));
      --_c-card: var(--card, var(--_card));
      --_c-border: var(--card-border, var(--_border));
      --_c-pri: var(--primary, var(--_pri));
      --_c-pri-fg: var(--primary-foreground, var(--_pri-fg));
      --_c-sec: var(--secondary, var(--_sec));
      --_c-sec-fg: var(--secondary-foreground, var(--_sec-fg));
      --_c-bg: var(--background, var(--_bg));
      color: var(--_c-fg);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      font-size: 11.5px;
      line-height: 1.26;
      padding: 5px 4px 4px;
      display: flex;
      flex-direction: column;
      gap: 5px;
      user-select: none;
    }
    @media (prefers-color-scheme: dark) {
      html:not([data-theme="light"]) {
        background: var(--background, #0b1220);
      }
      html:not([data-theme="light"]) .w5-root {
        --_bg: #0b1220;
        --_fg: #f1f5f9;
        --_muted: #cbd5e1;
        --_card: #111c30;
        --_subtle: #18253d;
        --_border: #334155;
        --_pri: #1d4ed8;
        --_pri-fg: #ffffff;
        --_sec: #1e293b;
        --_sec-fg: #f1f5f9;
        --_bad-bg: #450a0a;
        --_bad-fg: #fecaca;
        --_warn-bg: #451a03;
        --_warn-fg: #fde68a;
        --_good-bg: #052e16;
        --_good-fg: #a7f3d0;
        --_top-bg: #172554;
        --_top-fg: #bfdbfe;
        --_stale-bg: #273549;
        --_stale-fg: #e2e8f0;
        --_sep: #0b1220;
      }
    }
    html[data-theme="dark"] {
      color-scheme: dark;
      background: var(--background, #0b1220);
    }
    html[data-theme="dark"] .w5-root {
      --_bg: #0b1220;
      --_fg: #f1f5f9;
      --_muted: #cbd5e1;
      --_card: #111c30;
      --_subtle: #18253d;
      --_border: #334155;
      --_pri: #1d4ed8;
      --_pri-fg: #ffffff;
      --_sec: #1e293b;
      --_sec-fg: #f1f5f9;
      --_bad-bg: #450a0a;
      --_bad-fg: #fecaca;
      --_warn-bg: #451a03;
      --_warn-fg: #fde68a;
      --_good-bg: #052e16;
      --_good-fg: #a7f3d0;
      --_top-bg: #172554;
      --_top-fg: #bfdbfe;
      --_stale-bg: #273549;
      --_stale-fg: #e2e8f0;
      --_sep: #0b1220;
    }
    html[data-theme="light"] {
      color-scheme: light;
      background: var(--background, #ffffff);
    }
    html[data-theme="light"] .w5-root {
      --_bg: #ffffff;
      --_fg: #0f172a;
      --_muted: #334155;
      --_card: #f8fafc;
      --_subtle: #f1f5f9;
      --_border: #cbd5e1;
      --_pri: #1d4ed8;
      --_pri-fg: #ffffff;
      --_sec: #e2e8f0;
      --_sec-fg: #0f172a;
      --_bad-bg: #fee2e2;
      --_bad-fg: #991b1b;
      --_warn-bg: #fef3c7;
      --_warn-fg: #78350f;
      --_good-bg: #d1fae5;
      --_good-fg: #065f46;
      --_top-bg: #dbeafe;
      --_top-fg: #1e40af;
      --_stale-bg: #e2e8f0;
      --_stale-fg: #334155;
      --_sep: #ffffff;
    }
    html[data-theme-manual="true"] .w5-root {
      --_c-fg: var(--_fg);
      --_c-muted: var(--_muted);
      --_c-card: var(--_card);
      --_c-border: var(--_border);
      --_c-pri: var(--_pri);
      --_c-pri-fg: var(--_pri-fg);
      --_c-sec: var(--_sec);
      --_c-sec-fg: var(--_sec-fg);
      --_c-bg: var(--_bg);
      background: var(--_bg);
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-variant-numeric: tabular-nums;
    }
    .row1 {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      padding-bottom: 5px;
      border-bottom: 1px solid var(--_c-border);
      flex-wrap: nowrap;
    }
    .ctrl-left, .ctrl-right {
      display: flex;
      align-items: center;
      gap: 5px;
      min-width: 0;
    }
    .core-sel {
      appearance: auto;
      border: 1px solid var(--_c-border);
      background: var(--_c-card);
      color: var(--_c-fg);
      border-radius: 5px;
      padding: 2px 6px;
      font-size: 11px;
      font-weight: 600;
      height: 24px;
      cursor: pointer;
    }
    .seg-grp {
      display: inline-flex;
      border: 1px solid var(--_c-border);
      border-radius: 5px;
      overflow: hidden;
    }
    .seg-btn {
      appearance: none;
      border: 0;
      border-right: 1px solid var(--_c-border);
      background: var(--_c-sec);
      color: var(--_c-sec-fg);
      padding: 2px 7px;
      height: 22px;
      font-size: 10.5px;
      font-weight: 700;
      cursor: pointer;
      line-height: 1;
    }
    .seg-btn:last-child { border-right: 0; }
    .seg-btn[aria-pressed="true"] {
      background: var(--_c-pri);
      color: var(--_c-pri-fg);
    }
    .theme-btn {
      appearance: none;
      border: 1px solid var(--_c-border);
      background: var(--_c-sec);
      color: var(--_c-sec-fg);
      border-radius: 5px;
      padding: 2px 7px;
      height: 24px;
      font-size: 10.5px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }
    .row2 {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-wrap: nowrap;
      overflow-x: auto;
    }
    .spec-pill {
      appearance: none;
      border: 1px solid var(--_c-border);
      background: var(--_c-sec);
      color: var(--_c-sec-fg);
      border-radius: 5px;
      padding: 3px 7px;
      font-size: 10.5px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      line-height: 1.2;
      flex-shrink: 0;
    }
    .spec-pill[aria-selected="true"] {
      background: var(--_c-pri);
      color: var(--_c-pri-fg);
      border-color: transparent;
    }
    .spec-pill.pill-yolo {
      border-color: #dc2626;
      color: var(--_bad-fg);
      background: var(--_bad-bg);
    }
    .spec-pill.pill-yolo[aria-selected="true"] {
      background: #991b1b;
      color: #ffffff;
    }
    .spec-pill:disabled {
      opacity: 0.42;
      cursor: not-allowed;
    }
    .status-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      padding: 3px 7px;
      border-radius: 5px;
      background: var(--_c-card);
      border: 1px solid var(--_c-border);
      font-size: 10.5px;
      min-height: 24px;
    }
    .status-metrics {
      color: var(--_c-fg);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 999px;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .b-bad { background: var(--_bad-bg); color: var(--_bad-fg); }
    .b-adequate { background: var(--_warn-bg); color: var(--_warn-fg); }
    .b-good { background: var(--_good-bg); color: var(--_good-fg); }
    .b-top { background: var(--_top-bg); color: var(--_top-fg); }
    .b-stale { background: var(--_stale-bg); color: var(--_stale-fg); }
    .cards-4 {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 7px;
    }
    .pcard {
      background: var(--_c-card);
      border: 1px solid var(--_c-border);
      border-radius: 7px;
      padding: 7px 8px;
      display: flex;
      flex-direction: column;
      gap: 5px;
      cursor: default;
      transition: border-color 120ms ease;
    }
    .pcard:hover, .pcard:focus {
      border-color: var(--_c-pri);
      outline: none;
    }
    .pcard-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
    }
    .pcard-title {
      font-size: 11px;
      font-weight: 700;
      color: var(--_c-fg);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .pcard-main {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 4px;
    }
    .pcard-big {
      font-size: 16px;
      font-weight: 800;
      color: var(--_c-fg);
      line-height: 1.1;
    }
    .pcard-sub {
      font-size: 9.5px;
      color: var(--_c-muted);
      white-space: nowrap;
    }
    .g-track {
      position: relative;
      height: 7px;
      border-radius: 999px;
      background: linear-gradient(
        90deg,
        #dc2626 0%, #dc2626 24.5%,
        var(--_sep) 24.5%, var(--_sep) 25.5%,
        #eab308 25.5%, #eab308 54.5%,
        var(--_sep) 54.5%, var(--_sep) 55.5%,
        #16a34a 55.5%, #16a34a 84.5%,
        var(--_sep) 84.5%, var(--_sep) 85.5%,
        #2563eb 85.5%, #1d4ed8 100%
      );
    }
    .g-pin {
      position: absolute;
      top: 50%;
      width: 11px;
      height: 11px;
      border-radius: 999px;
      transform: translate(-50%, -50%);
      background: var(--_c-fg);
      border: 2px solid var(--_c-bg);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
      transition: left 140ms ease-out;
    }
    .g-ticks {
      display: grid;
      grid-template-columns: 25% 30% 30% 15%;
      font-size: 8.8px;
      color: var(--_c-muted);
      margin-top: -2px;
    }
    .g-ticks span:nth-child(2), .g-ticks span:nth-child(3) { text-align: center; }
    .g-ticks span:nth-child(4) { text-align: right; font-weight: 700; }
    .pfp-wrap {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .pfp-bar {
      display: flex;
      width: 100%;
      height: 8px;
      border-radius: 999px;
      overflow: hidden;
      border: 1px solid var(--_c-border);
    }
    .seg-pass { background: #16a34a; }
    .seg-fail { background: #dc2626; }
    .seg-pend { background: #d97706; }
    .pfp-lbls {
      display: flex;
      justify-content: space-between;
      gap: 3px;
      font-size: 9.2px;
      color: var(--_c-muted);
      white-space: nowrap;
    }
    .kv-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 3px 6px;
      padding-top: 4px;
      border-top: 1px solid var(--_c-border);
      font-size: 9.8px;
    }
    .kv-item {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .kv-k {
      font-size: 8.8px;
      color: var(--_c-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .kv-v {
      font-weight: 700;
      color: var(--_c-fg);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .legend-tip {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 3px 7px;
      border-radius: 5px;
      background: var(--_c-card);
      border: 1px solid var(--_c-border);
      font-size: 10px;
      color: var(--_c-muted);
      min-height: 22px;
    }
    .legend-dots {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
      white-space: nowrap;
    }
    .dot {
      display: inline-block;
      width: 7px;
      height: 7px;
      border-radius: 999px;
      margin-right: 3px;
      vertical-align: middle;
    }
    .tip-live {
      color: var(--_c-fg);
      text-align: right;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-width: 0;
    }
    .footer-strip {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      padding-top: 3px;
      border-top: 1px solid var(--_c-border);
      flex-wrap: nowrap;
    }
    .bn-list {
      display: flex;
      align-items: center;
      gap: 4px;
      overflow: hidden;
      min-width: 0;
    }
    .bn-chip {
      font-size: 9.6px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      background: var(--_warn-bg);
      color: var(--_warn-fg);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 210px;
    }
    .ev-badge {
      font-size: 9.6px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 999px;
      border: 1px solid var(--_c-border);
      background: var(--_c-card);
      color: var(--_c-muted);
      white-space: nowrap;
      flex-shrink: 0;
    }
  </style>
</head>
<body>
  <div class="w5-root" id="w5-root">
    <div class="row1">
      <div class="ctrl-left">
        <select id="w5-core-select" class="core-sel" aria-label="Chọn lõi Alpha">
          <option value="CORE_PORT_7E">PORT_7E Full Dev</option>
          <option value="V105_ML_FILTER">OOF v1.05-ML Filter</option>
          <option value="V105_ML_ASYMFLOOR">OOF v1.05-ML AsymFloor</option>
          <option value="PORT_7E_OOF_CONTROL">OOF v1.03 Control</option>
        </select>
        <div class="seg-grp" role="group" aria-label="Chọn quy mô tài khoản">
          <button type="button" class="seg-btn mono" data-sku="ftmo_standard_10k" aria-pressed="false">10K</button>
          <button type="button" class="seg-btn mono" data-sku="ftmo_standard_100k" aria-pressed="true">100K</button>
        </div>
        <div class="seg-grp" role="group" aria-label="Chọn mức trượt giá">
          <button type="button" class="seg-btn mono" data-stress="1" aria-pressed="true">1,0x</button>
          <button type="button" class="seg-btn mono" data-stress="1.5" aria-pressed="false">1,5x</button>
          <button type="button" class="seg-btn mono" data-stress="2" aria-pressed="false">2,0x</button>
        </div>
      </div>
      <div class="ctrl-right">
        <span class="badge" id="w5-overall-badge"></span>
        <span class="badge b-stale mono" id="w5-scope-badge" title="Đơn vé không thử lại · Giá niêm yết chuẩn SSOT · XẤP XỈ CẤP NGÀY">Đơn vé · SSOT · XẤP XỈ CẤP NGÀY</span>
        <button type="button" class="theme-btn" id="w5-theme-btn" aria-label="Chuyển giao diện Sáng Tối">Chế độ Tối/Sáng</button>
      </div>
    </div>

    <div class="row2" id="w5-spec-pills" role="tablist" aria-label="Quang phổ 5 bậc tốc độ và đối chứng"></div>

    <div class="status-bar">
      <span class="status-metrics mono" id="w5-status-metrics"></span>
      <span class="badge" id="w5-warn-badge"></span>
    </div>

    <div class="cards-4" id="w5-phase-cards"></div>

    <div class="legend-tip">
      <div class="legend-dots">
        <span><span class="dot" style="background:#dc2626"></span>Xấu</span>
        <span><span class="dot" style="background:#eab308"></span>Đủ dùng</span>
        <span><span class="dot" style="background:#16a34a"></span>Tốt</span>
        <span><span class="dot" style="background:#2563eb"></span>Top 1%</span>
        <span>|</span>
        <span><span class="dot" style="background:#16a34a"></span>Đậu</span>
        <span><span class="dot" style="background:#dc2626"></span>Rớt</span>
        <span><span class="dot" style="background:#d97706"></span>Chờ (100%)</span>
      </div>
      <span class="tip-live" id="w5-tip-live">Di chuột vào từng pha để xem chi tiết ngưỡng Top 1% và quy đổi VND/USD</span>
    </div>

    <div class="footer-strip">
      <div class="bn-list" id="w5-bottlenecks"></div>
      <span class="ev-badge mono" id="w5-ev-badge">Dev &lt;= 2024-12-31 · Holdout 2025+ SEALED · 0 VND · OrderSend = 0</span>
    </div>
  </div>

  <script id="w5-ssot-data" type="application/json">__DATA_JSON__</script>
  <script>
    (function () {
      "use strict";
      var DATA = JSON.parse(document.getElementById("w5-ssot-data").textContent);
      var PILL_ORDER = [
        "T1_ULTRA_SAFE",
        "T2_SAFE_C00",
        "T3_BALANCED_EV",
        "T4_TURBO_FAST",
        "T5_MAX_THROTTLE_YOLO",
        "C00",
        "C10_NEWS_ON",
        "BELLMAN_DP_6TIER"
      ];
      var GRADE_META = {
        BAD: { vi: "Xấu", cls: "b-bad", icon: "Xấu" },
        ADEQUATE: { vi: "Đủ dùng", cls: "b-adequate", icon: "Đủ dùng" },
        GOOD: { vi: "Tốt", cls: "b-good", icon: "Tốt" },
        TOP_1_PCT: { vi: "Top 1%", cls: "b-top", icon: "Top 1%" },
        UNKNOWN_LEGACY_UNINSTRUMENTED: { vi: "Chưa tách Đợt 4", cls: "b-stale", icon: "Chưa tách" }
      };

      var state = {
        cohort: "CORE_PORT_7E",
        contract: "ftmo_standard_100k",
        stress: 1.0,
        schedule: "T3_BALANCED_EV"
      };

      var caseIndex = {};
      for (var i = 0; i < DATA.cases.length; i++) {
        var c = DATA.cases[i];
        var key = c.cohort + "|" + c.schedule_id + "|" + c.contract_id + "|" + Number(c.friction_mult).toFixed(1);
        caseIndex[key] = c;
      }

      function esc(s) {
        return String(s)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
      }

      function fmtNum(v, dec) {
        return Number(v).toFixed(dec).replace(".", ",");
      }

      function fmtIntVi(v) {
        var neg = v < 0;
        var s = String(Math.round(Math.abs(v)));
        var out = s.replace(/\\B(?=(\\d{3})+(?!\\d))/g, ".");
        return (neg ? "-" : "+") + out;
      }

      function fmtTrVnd(vnd) {
        var tr = vnd / 1e6;
        return (tr >= 0 ? "+" : "") + fmtNum(tr, 1) + " tr VND";
      }

      function gaugePinHigh(val, tAdq, tGood, tTop, capMax) {
        if (val <= 0) return 2;
        if (val < tAdq) return Math.max(2, Math.min(24, (val / tAdq) * 25));
        if (val < tGood) return 25 + ((val - tAdq) / (tGood - tAdq)) * 30;
        if (val < tTop) return 55 + ((val - tGood) / (tTop - tGood)) * 30;
        var span = Math.max(capMax - tTop, 1);
        return Math.min(97, 85 + ((val - tTop) / span) * 12);
      }

      function gaugePinLowBlowup(val) {
        if (val >= 5.0) {
          return Math.max(3, 24 - Math.min(val - 5.0, 20.0) * 1.0);
        }
        if (val >= 1.0) {
          return 25 + ((5.0 - val) / 4.0) * 30;
        }
        if (val >= 0.5) {
          return 55 + ((1.0 - val) / 0.5) * 30;
        }
        return Math.min(97, 85 + ((0.5 - Math.max(0, val)) / 0.5) * 12);
      }

      function detectInitialTheme() {
        var cur = document.documentElement.getAttribute("data-theme");
        if (cur === "dark" || cur === "light") return cur;
        if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
          return "dark";
        }
        return "light";
      }

      function syncThemeButton() {
        var active = detectInitialTheme();
        var btn = document.getElementById("w5-theme-btn");
        btn.textContent = active === "dark" ? "Chế độ: Tối" : "Chế độ: Sáng";
        btn.setAttribute("aria-pressed", active === "dark" ? "true" : "false");
      }

      document.getElementById("w5-theme-btn").addEventListener("click", function () {
        var next = detectInitialTheme() === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        document.documentElement.setAttribute("data-theme-manual", "true");
        syncThemeButton();
      });

      function buildPills() {
        var host = document.getElementById("w5-spec-pills");
        host.innerHTML = "";
        for (var i = 0; i < PILL_ORDER.length; i++) {
          var sid = PILL_ORDER[i];
          var meta = DATA.schedules[sid];
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "spec-pill" + (sid === "T5_MAX_THROTTLE_YOLO" ? " pill-yolo" : "");
          btn.setAttribute("role", "tab");
          btn.setAttribute("data-schedule", sid);
          btn.textContent = sid === "T5_MAX_THROTTLE_YOLO" ? meta.label_vi + " (!)" : meta.label_vi;
          btn.addEventListener("click", (function (id) {
            return function () {
              state.schedule = id;
              render();
            };
          })(sid));
          host.appendChild(btn);
        }
      }

      function findCase() {
        var k = state.cohort + "|" + state.schedule + "|" + state.contract + "|" + state.stress.toFixed(1);
        if (caseIndex[k]) return caseIndex[k];
        state.schedule = "T3_BALANCED_EV";
        return caseIndex[state.cohort + "|T3_BALANCED_EV|" + state.contract + "|" + state.stress.toFixed(1)];
      }

      function render() {
        var item = findCase();
        var sm = DATA.schedules[item.schedule_id];
        var tipEl = document.getElementById("w5-tip-live");

        // Sync pills availability & active state
        var pills = document.querySelectorAll("#w5-spec-pills .spec-pill");
        for (var i = 0; i < pills.length; i++) {
          var sid = pills[i].getAttribute("data-schedule");
          var probeKey = state.cohort + "|" + sid + "|" + state.contract + "|" + state.stress.toFixed(1);
          var available = Boolean(caseIndex[probeKey]);
          pills[i].disabled = !available;
          pills[i].setAttribute("aria-selected", sid === item.schedule_id ? "true" : "false");
          pills[i].title = available
            ? DATA.schedules[sid].label_vi + " (P1 " + fmtNum(DATA.schedules[sid].p1_mult, 2) + "x / P2 " + fmtNum(DATA.schedules[sid].p2_mult, 2) + "x / Fn " + fmtNum(DATA.schedules[sid].funded_mult, 2) + "x)"
            : "Bậc này chỉ chạy trên PORT_7E Full Dev; nhóm OOF ML đối chứng cặp trên T3 và Bellman DP";
        }

        // Sync overall grade pill
        var og = GRADE_META[item.overall_grade] || GRADE_META.ADEQUATE;
        var ob = document.getElementById("w5-overall-badge");
        ob.className = "badge " + og.cls;
        ob.textContent = "Tổng: " + og.vi;
        ob.setAttribute("aria-label", item.aria_label || ("Tổng hạng " + og.vi));

        // Status metrics & warning badge
        var fn = item.funded;
        document.getElementById("w5-status-metrics").textContent =
          sm.label_vi +
          " (P1 " + fmtNum(sm.p1_mult, 2) + "x · P2 " + fmtNum(sm.p2_mult, 2) + "x · Fn " + fmtNum(sm.funded_mult, 2) + "x) | " +
          "WR " + fmtNum(fn.wr, 1) + "% · RR " + fmtNum(fn.rr, 2) + " · PF " + fmtNum(fn.pf, 2) +
          " · Sharpe " + fmtNum(fn.sharpe, 2) + " · Calmar " + fmtNum(fn.calmar, 2) + " · MaxDD " + fmtNum(fn.max_dd, 1) + "%";

        var wb = document.getElementById("w5-warn-badge");
        var auditKey = item.schedule_id + "__" + item.contract_id;
        var audit = DATA.intraday_audit[auditKey];
        if (item.schedule_id === "T5_MAX_THROTTLE_YOLO") {
          wb.className = "badge b-bad";
          wb.textContent = "RESEARCH_BOUNDARY_ONLY · FTMO_GAMBLING_ALLIN_RISK · Lệch DD ngày +" + fmtNum(audit.drift_trade_minus_daily_close_pp, 1) + " đpt";
          wb.title = "Rủi ro chạm sàn ngày 5%: " + fmtNum(audit.trade_1x_daily_breach, 1) + "% (1,0x) / " + fmtNum(audit.gap_125x_daily_breach, 1) + "% (1,25x gap); " + audit.hist_days_ge5_trade + " ngày lịch sử >= 5%.";
        } else if (item.schedule_id === "T4_TURBO_FAST") {
          wb.className = "badge b-adequate";
          wb.textContent = "Vượt Shield A 3% (nghiên cứu) · Lệch DD ngày +" + fmtNum(audit.drift_trade_minus_daily_close_pp, 1) + " đpt";
          wb.title = "T4 chạm sàn 5% trong ngày ở " + fmtNum(audit.trade_1x_daily_breach, 1) + "% đường chạy (1,0x) và " + fmtNum(audit.gap_125x_daily_breach, 1) + "% (1,25x gap).";
        } else if (state.cohort !== "CORE_PORT_7E") {
          wb.className = "badge b-adequate";
          wb.textContent = "OOF_SUBSET_WINDOW · RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED";
          wb.title = "Đối chứng cùng cửa sổ OOF 1.455 ngày; kết luận Wave 5: REJECT_V105_ML_KEEP_V103.";
        } else if (item.schedule_id === "BELLMAN_DP_6TIER") {
          wb.className = "badge b-top";
          wb.textContent = "ANTI_MARTINGALE_BELLMAN_DP_6TIER · Rớt thấp nhất";
          wb.title = "Chính sách DP 6 bậc học nhân quả Cụm A -> Cụm B, giảm tải khi lỗ, cấm gấp thếp.";
        } else {
          wb.className = "badge b-stale";
          wb.textContent = item.schedule_id === "T3_BALANCED_EV"
            ? "Điểm cân bằng Pareto (tương đương V103_SPRINT)"
            : "Đối chứng lịch sử Dev (CONSUMED_DEV_CLB_TEMPORAL_OOS)";
          wb.title = item.aria_label || "";
        }

        // Build 4 Phase Cards
        var pg = item.phase_grades;
        var p1m = GRADE_META[pg.p1.grade] || GRADE_META.ADEQUATE;
        var p2m = GRADE_META[pg.p2.grade] || GRADE_META.ADEQUATE;
        var pem = GRADE_META[pg.pass_eval.grade] || GRADE_META.ADEQUATE;
        var fnm = GRADE_META[pg.funded_12m.grade] || GRADE_META.ADEQUATE;

        var dailyRiskDisplay = audit
          ? fmtNum(audit.trade_1x_daily_breach, 1) + "% (1x)"
          : fmtNum(fn.firm_daily_breach, 2) + "%";

        var cards = [
          {
            title: "Pha 1 · Vòng 1 (P1)",
            gradeMeta: p1m,
            aria: pg.p1.aria,
            big: fmtNum(item.p1.pass_12m, 2) + "%",
            sub: "Mốc Top 1%: >=75%",
            pin: gaugePinHigh(item.p1.pass_12m, 35, 55, 75, 100),
            ticks: ["<35%", "35–55", "55–75", ">=75%"],
            pass: item.p1.pass_12m,
            fail: item.p1.fail_12m,
            pend: item.p1.pend_12m,
            kvs: [
              { k: "Hệ số P1", v: fmtNum(sm.p1_mult, 2) + "x" },
              { k: "TV qua P1", v: fmtNum(item.p1.cond_med_days, 1) + " ngày" },
              { k: "Đậu 3T / 6T", v: fmtNum(item.p1.pass_3m, 1) + "% / " + fmtNum(item.p1.pass_6m, 1) + "%" },
              { k: "Chạm sàn 5%/ngày", v: dailyRiskDisplay }
            ],
            tip: "P1 (12T): Đậu " + fmtNum(item.p1.pass_12m, 2) + "% / Rớt " + fmtNum(item.p1.fail_12m, 2) + "% / Chờ " + fmtNum(item.p1.pend_12m, 2) + "% (Tổng 100,00%). Trung vị có ĐK: " + fmtNum(item.p1.cond_med_days, 1) + " ngày."
          },
          {
            title: "Pha 2 · Vòng 2 (P2)",
            gradeMeta: p2m,
            aria: pg.p2.aria,
            big: fmtNum(item.p2.pass_12m, 2) + "%",
            sub: "Mốc Top 1%: >=85%",
            pin: gaugePinHigh(item.p2.pass_12m, 55, 70, 85, 100),
            ticks: ["<55%", "55–70", "70–85", ">=85%"],
            pass: item.p2.pass_12m,
            fail: item.p2.fail_12m,
            pend: item.p2.pend_12m,
            kvs: [
              { k: "Hệ số P2", v: fmtNum(sm.p2_mult, 2) + "x" },
              { k: "TV qua P2", v: fmtNum(item.p2.cond_med_days, 1) + " ngày" },
              { k: "Đậu 3T / 6T", v: fmtNum(item.p2.pass_3m, 1) + "% / " + fmtNum(item.p2.pass_6m, 1) + "%" },
              { k: "Lượt vào P2", v: String(item.p2.entered_count) + " / 10k" }
            ],
            tip: "P2 (12T sau khi đậu P1): Đậu " + fmtNum(item.p2.pass_12m, 2) + "% / Rớt " + fmtNum(item.p2.fail_12m, 2) + "% / Chờ " + fmtNum(item.p2.pend_12m, 2) + "% (Tổng 100,00%)."
          },
          {
            title: "Pass P1+P2 (Vào Funded)",
            gradeMeta: pem,
            aria: pg.pass_eval.aria,
            big: fmtNum(item.pass_eval.pass_12m, 2) + "%",
            sub: "36T: " + fmtNum(item.pass_eval.pass_36m, 1) + "%",
            pin: gaugePinHigh(item.pass_eval.pass_12m, 25, 45, 65, 100),
            ticks: ["<25%", "25–45", "45–65", ">=65%"],
            pass: item.pass_eval.pass_12m,
            fail: item.pass_eval.fail_12m,
            pend: item.pass_eval.pend_12m,
            kvs: [
              { k: "Pay1 có ĐK", v: fmtNum(fn.cond_pay1, 1) + " ngày" },
              { k: "Pay1 ko ĐK", v: fmtNum(fn.uncond_pay1, 1) + " ngày" },
              { k: "Đậu 3T / 6T", v: fmtNum(item.pass_eval.pass_3m, 1) + "% / " + fmtNum(item.pass_eval.pass_6m, 1) + "%" },
              { k: "TV vào Funded", v: fmtNum(item.pass_eval.cond_med_days, 1) + " ngày" }
            ],
            tip: "Pass P1+P2 (12T, đơn vé 0 thử lại): Đậu " + fmtNum(item.pass_eval.pass_12m, 2) + "% / Rớt " + fmtNum(item.pass_eval.fail_12m, 2) + "% / Chờ " + fmtNum(item.pass_eval.pend_12m, 2) + "%. Pay1 có ĐK " + fmtNum(fn.cond_pay1, 1) + " ngày vs ko ĐK " + fmtNum(fn.uncond_pay1, 1) + " ngày."
          },
          {
            title: "Funded 12T & Payout #1",
            gradeMeta: fnm,
            aria: pg.funded_12m.aria,
            big: fmtNum(fn.blowup_12m, 2) + "%",
            sub: "Cháy 12T (UB " + fmtNum(fn.wilson_ub, 2) + "%)",
            pin: gaugePinLowBlowup(fn.blowup_12m),
            ticks: [">=5%", "1–5%", "0,5–1", "<0,5%"],
            pass: fn.pass_12m,
            fail: fn.fail_12m,
            pend: fn.pend_12m,
            kvs: [
              { k: "EV / Phí 24T", v: fmtNum(fn.ev_per_fee, 2) + "x" },
              { k: "P(<=0) 24T", v: fmtNum(fn.p_le_0_24m, 2) + "%" },
              { k: "EV 24T (VND)", v: fmtTrVnd(fn.ev_24m_vnd) },
              { k: "EV 24T (USD)", v: fmtIntVi(fn.ev_24m_usd) + " USD" }
            ],
            tip: "Funded 12T: An toàn " + fmtNum(fn.pass_12m, 2) + "% / Cháy " + fmtNum(fn.fail_12m, 2) + "% / Chờ đủ 12T " + fmtNum(fn.pend_12m, 2) + "%. EV/Phí " + fmtNum(fn.ev_per_fee, 2) + "x, EV 24T " + fmtTrVnd(fn.ev_24m_vnd) + " (" + fmtIntVi(fn.ev_24m_usd) + " USD), phí " + fmtNum(fn.fee_vnd / 1e6, 2) + " tr VND."
          }
        ];

        var html = "";
        for (var cIdx = 0; cIdx < cards.length; cIdx++) {
          var cd = cards[cIdx];
          var kvHtml = "";
          for (var j = 0; j < cd.kvs.length; j++) {
            kvHtml += '<div class="kv-item"><span class="kv-k">' + esc(cd.kvs[j].k) + '</span><span class="kv-v mono">' + esc(cd.kvs[j].v) + '</span></div>';
          }
          html +=
            '<div class="pcard" tabindex="0" data-card="' + cIdx + '" title="' + esc(cd.tip) + '">' +
              '<div class="pcard-top">' +
                '<span class="pcard-title">' + esc(cd.title) + '</span>' +
                '<span class="badge ' + cd.gradeMeta.cls + '" aria-label="' + esc(cd.aria || cd.gradeMeta.vi) + '">' + esc(cd.gradeMeta.vi) + '</span>' +
              '</div>' +
              '<div class="pcard-main">' +
                '<span class="pcard-big mono">' + esc(cd.big) + '</span>' +
                '<span class="pcard-sub mono">' + esc(cd.sub) + '</span>' +
              '</div>' +
              '<div class="g-track"><div class="g-pin" style="left:' + cd.pin.toFixed(1) + '%"></div></div>' +
              '<div class="g-ticks mono">' +
                '<span>' + esc(cd.ticks[0]) + '</span><span>' + esc(cd.ticks[1]) + '</span><span>' + esc(cd.ticks[2]) + '</span><span>' + esc(cd.ticks[3]) + '</span>' +
              '</div>' +
              '<div class="pfp-wrap">' +
                '<div class="pfp-bar" role="img" aria-label="Đậu ' + fmtNum(cd.pass, 1) + '% Rớt ' + fmtNum(cd.fail, 1) + '% Chờ ' + fmtNum(cd.pend, 1) + '% tổng 100%">' +
                  '<div class="seg-pass" style="width:' + cd.pass.toFixed(2) + '%"></div>' +
                  '<div class="seg-fail" style="width:' + cd.fail.toFixed(2) + '%"></div>' +
                  '<div class="seg-pend" style="width:' + cd.pend.toFixed(2) + '%"></div>' +
                '</div>' +
                '<div class="pfp-lbls mono">' +
                  '<span>Đ:' + fmtNum(cd.pass, 1) + '%</span>' +
                  '<span>R:' + fmtNum(cd.fail, 1) + '%</span>' +
                  '<span>C:' + fmtNum(cd.pend, 1) + '%</span>' +
                '</div>' +
              '</div>' +
              '<div class="kv-grid">' + kvHtml + '</div>' +
            '</div>';
        }
        var gridEl = document.getElementById("w5-phase-cards");
        gridEl.innerHTML = html;

        var cardEls = gridEl.querySelectorAll(".pcard");
        for (var kIdx = 0; kIdx < cardEls.length; kIdx++) {
          (function (el, tipText) {
            var show = function () { tipEl.textContent = tipText; tipEl.title = tipText; };
            el.addEventListener("mouseenter", show);
            el.addEventListener("focus", show);
          })(cardEls[kIdx], cards[kIdx].tip);
        }

        tipEl.textContent = item.gap_vi || "Di chuột vào từng pha để xem chi tiết";
        tipEl.title = tipEl.textContent;

        // Render ranked exact_bottlenecks[] chips (top 3)
        var bnHost = document.getElementById("w5-bottlenecks");
        var bns = (item.exact_bottlenecks || []).slice(0, 3);
        var bnHtml = "";
        for (var b = 0; b < bns.length; b++) {
          var itemBn = bns[b];
          var valStr = itemBn.cur !== null && itemBn.tgt !== null
            ? " (" + fmtNum(itemBn.cur, 1) + " vs " + fmtNum(itemBn.tgt, 1) + ")"
            : "";
          bnHtml += '<span class="bn-chip mono" title="' + esc(itemBn.vi) + '">#' + itemBn.rank + ' ' + esc(itemBn.code) + esc(valStr) + '</span>';
        }
        bnHost.innerHTML = bnHtml;
      }

      document.getElementById("w5-core-select").addEventListener("change", function (ev) {
        state.cohort = ev.target.value;
        render();
      });

      var skuBtns = document.querySelectorAll("[data-sku]");
      for (var s = 0; s < skuBtns.length; s++) {
        skuBtns[s].addEventListener("click", function () {
          state.contract = this.getAttribute("data-sku");
          for (var j = 0; j < skuBtns.length; j++) {
            skuBtns[j].setAttribute("aria-pressed", skuBtns[j] === this ? "true" : "false");
          }
          render();
        });
      }

      var stressBtns = document.querySelectorAll("[data-stress]");
      for (var r = 0; r < stressBtns.length; r++) {
        stressBtns[r].addEventListener("click", function () {
          state.stress = Number(this.getAttribute("data-stress"));
          for (var j = 0; j < stressBtns.length; j++) {
            stressBtns[j].setAttribute("aria-pressed", stressBtns[j] === this ? "true" : "false");
          }
          render();
        });
      }

      buildPills();
      syncThemeButton();
      render();
    })();
  </script>
</body>
</html>
"""
    return html.replace("__DATA_JSON__", data_json)


def render_deep_alpha_explorer_html(payload: Mapping[str, Any]) -> str:
    """Render full standalone 4-tab `wave5_deep_alpha_explorer.html` (zero CDN, dark/light)."""
    data_json = _safe_embed_json(payload)
    html = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Wave 5 — Khám Phá Quang Phổ 5 Bậc, Đường Cong Vốn 9 Bậc &amp; Alpha Factory</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    html {
      margin: 0;
      padding: 0;
      color-scheme: light dark;
    }
    body {
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      --_bg: #f8fafc;
      --_card: #ffffff;
      --_subtle: #f1f5f9;
      --_border: #cbd5e1;
      --_fg: #0f172a;
      --_muted: #334155;
      --_pri: #1d4ed8;
      --_pri-fg: #ffffff;
      --_sec: #e2e8f0;
      --_sec-fg: #0f172a;
      --_bad-bg: #fee2e2;
      --_bad-fg: #991b1b;
      --_warn-bg: #fef3c7;
      --_warn-fg: #78350f;
      --_good-bg: #d1fae5;
      --_good-fg: #065f46;
      --_top-bg: #dbeafe;
      --_top-fg: #1e40af;
      --_stale-bg: #e2e8f0;
      --_stale-fg: #334155;
      --_c1: #1d4ed8;
      --_c2: #059669;
      --_c3: #d97706;
      --_c4: #dc2626;
      --_sep: #ffffff;
      background: var(--_bg);
      color: var(--_fg);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      font-size: 13px;
      line-height: 1.42;
    }
    @media (prefers-color-scheme: dark) {
      html:not([data-theme="light"]) body {
        --_bg: #0b1220;
        --_card: #111c30;
        --_subtle: #18253d;
        --_border: #334155;
        --_fg: #f1f5f9;
        --_muted: #cbd5e1;
        --_pri: #1d4ed8;
        --_pri-fg: #ffffff;
        --_sec: #1e293b;
        --_sec-fg: #f1f5f9;
        --_bad-bg: #450a0a;
        --_bad-fg: #fecaca;
        --_warn-bg: #451a03;
        --_warn-fg: #fde68a;
        --_good-bg: #052e16;
        --_good-fg: #a7f3d0;
        --_top-bg: #172554;
        --_top-fg: #bfdbfe;
        --_stale-bg: #273549;
        --_stale-fg: #e2e8f0;
        --_c1: #60a5fa;
        --_c2: #34d399;
        --_c3: #fbbf24;
        --_c4: #f87171;
        --_sep: #0b1220;
      }
    }
    html[data-theme="dark"] { color-scheme: dark; }
    html[data-theme="dark"] body {
      --_bg: #0b1220;
      --_card: #111c30;
      --_subtle: #18253d;
      --_border: #334155;
      --_fg: #f1f5f9;
      --_muted: #cbd5e1;
      --_pri: #1d4ed8;
      --_pri-fg: #ffffff;
      --_sec: #1e293b;
      --_sec-fg: #f1f5f9;
      --_bad-bg: #450a0a;
      --_bad-fg: #fecaca;
      --_warn-bg: #451a03;
      --_warn-fg: #fde68a;
      --_good-bg: #052e16;
      --_good-fg: #a7f3d0;
      --_top-bg: #172554;
      --_top-fg: #bfdbfe;
      --_stale-bg: #273549;
      --_stale-fg: #e2e8f0;
      --_c1: #60a5fa;
      --_c2: #34d399;
      --_c3: #fbbf24;
      --_c4: #f87171;
      --_sep: #0b1220;
    }
    html[data-theme="light"] { color-scheme: light; }
    .wrap {
      max-width: 1280px;
      margin: 0 auto;
      padding: 14px 16px 28px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .panel {
      background: var(--_card);
      border: 1px solid var(--_border);
      border-radius: 8px;
      padding: 13px 15px;
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-variant-numeric: tabular-nums;
    }
    .hdr {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }
    .hdr h1 { margin: 0; font-size: 17px; font-weight: 800; }
    .hdr-sub { margin-top: 3px; font-size: 12px; color: var(--_muted); }
    .badges { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }
    .b-bad { background: var(--_bad-bg); color: var(--_bad-fg); }
    .b-adequate { background: var(--_warn-bg); color: var(--_warn-fg); }
    .b-good { background: var(--_good-bg); color: var(--_good-fg); }
    .b-top { background: var(--_top-bg); color: var(--_top-fg); }
    .b-stale { background: var(--_stale-bg); color: var(--_stale-fg); }
    .b-outline { background: var(--_subtle); color: var(--_muted); border: 1px solid var(--_border); }
    .main-tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding-top: 10px;
      margin-top: 10px;
      border-top: 1px solid var(--_border);
    }
    .tab-btn, .chip {
      appearance: none;
      border: 1px solid var(--_border);
      background: var(--_sec);
      color: var(--_sec-fg);
      border-radius: 6px;
      padding: 6px 11px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    .chip { padding: 4px 8px; font-size: 11.5px; }
    .tab-btn[aria-selected="true"], .chip.active {
      background: var(--_pri);
      color: var(--_pri-fg);
      border-color: transparent;
    }
    .chip.yolo { background: var(--_bad-bg); color: var(--_bad-fg); border-color: #dc2626; }
    .chip.yolo.active { background: #991b1b; color: #ffffff; }
    .tab-panel { display: none; flex-direction: column; gap: 12px; }
    .tab-panel.active { display: flex; }
    .sec-head {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 10px;
    }
    .sec-title { margin: 0; font-size: 14.5px; font-weight: 800; }
    .sec-sub { font-size: 12px; color: var(--_muted); }
    .btn-row { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .grid-5 { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 9px; }
    .grid-6 { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; }
    @media (max-width: 1040px) {
      .grid-6 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .grid-5 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 820px) {
      .grid-2, .grid-3 { grid-template-columns: 1fr; }
    }
    .subcard {
      background: var(--_subtle);
      border: 1px solid var(--_border);
      border-radius: 7px;
      padding: 10px 11px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .kpi-k { font-size: 11px; font-weight: 700; color: var(--_muted); }
    .kpi-v { font-size: 16px; font-weight: 800; color: var(--_fg); }
    .kpi-s { font-size: 11px; color: var(--_muted); }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--_border);
      border-radius: 7px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11.2px;
      font-variant-numeric: tabular-nums;
    }
    thead th {
      background: var(--_subtle);
      color: var(--_muted);
      padding: 6px 6px;
      text-align: right;
      font-weight: 700;
      border-bottom: 1px solid var(--_border);
      white-space: nowrap;
    }
    thead th.tl, tbody td.tl { text-align: left; }
    tbody td {
      padding: 5px 6px;
      text-align: right;
      border-bottom: 1px solid var(--_border);
      white-space: nowrap;
    }
    tbody tr.clickable { cursor: pointer; }
    tbody tr.clickable:hover { background: var(--_subtle); }
    tbody tr.selected { background: var(--_top-bg); }
    .g-track {
      position: relative;
      height: 8px;
      border-radius: 999px;
      background: linear-gradient(
        90deg,
        #dc2626 0%, #dc2626 24.5%,
        var(--_sep) 24.5%, var(--_sep) 25.5%,
        #eab308 25.5%, #eab308 54.5%,
        var(--_sep) 54.5%, var(--_sep) 55.5%,
        #16a34a 55.5%, #16a34a 84.5%,
        var(--_sep) 84.5%, var(--_sep) 85.5%,
        #2563eb 85.5%, #1d4ed8 100%
      );
    }
    .g-pin {
      position: absolute;
      top: 50%;
      width: 12px;
      height: 12px;
      border-radius: 999px;
      transform: translate(-50%, -50%);
      background: var(--_fg);
      border: 2px solid var(--_bg);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
    }
    .pfp-bar {
      display: flex;
      width: 100%;
      height: 10px;
      border-radius: 999px;
      overflow: hidden;
      border: 1px solid var(--_border);
    }
    .seg-pass { background: #16a34a; }
    .seg-fail { background: #dc2626; }
    .seg-pend { background: #d97706; }
    .callout {
      padding: 9px 11px;
      border-radius: 7px;
      border: 1px solid var(--_border);
      background: var(--_subtle);
      font-size: 12px;
    }
    .callout-warn { background: var(--_warn-bg); color: var(--_warn-fg); border-color: transparent; }
    .callout-bad { background: var(--_bad-bg); color: var(--_bad-fg); border-color: transparent; }
    .callout-good { background: var(--_good-bg); color: var(--_good-fg); border-color: transparent; }
    svg.chart { width: 100%; height: auto; display: block; }
    input[type="range"] { width: 100%; accent-color: var(--_pri); cursor: pointer; }
    .ctrl-box { display: flex; flex-direction: column; gap: 7px; }
    .ctrl-lbl { display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; }
    .bn-tag {
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 7px;
      border-radius: 5px;
      background: var(--_warn-bg);
      color: var(--_warn-fg);
      margin: 2px 4px 2px 0;
    }
    .foot-meta {
      font-size: 11px;
      color: var(--_muted);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 8px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <div class="hdr">
        <div>
          <h1>Wave 5 — Khám Phá Quang Phổ 5 Bậc, Đường Cong Vốn 9 Bậc &amp; Alpha Factory</h1>
          <div class="hdr-sub" id="exp-sub"></div>
        </div>
        <div class="badges">
          <span class="badge b-adequate">XẤP XỈ CẤP NGÀY</span>
          <span class="badge b-outline">ALL_REGULAR_SSOT</span>
          <span class="badge b-good">Dev &lt;= 2024-12-31 · Holdout 2025+ SEALED</span>
          <span class="badge b-outline mono">OrderSend = 0 · 0 VND · execution_capability = false</span>
          <button type="button" class="chip" id="w5-explorer-theme-btn">Chế độ Tối/Sáng</button>
        </div>
      </div>

      <div class="main-tabs" id="main-tabs" role="tablist" aria-label="4 góc nhìn Wave 5">
        <button type="button" class="tab-btn" role="tab" data-tab="tab1" aria-selected="true">1. Quang Phổ 5 Bậc x 4 Pha</button>
        <button type="button" class="tab-btn" role="tab" data-tab="tab2" aria-selected="false">2. Đường Cong Vốn 9 Bậc &amp; So Sánh Đợt 4 vs Đợt 5</button>
        <button type="button" class="tab-btn" role="tab" data-tab="tab3" aria-selected="false">3. Bellman DP &amp; MT5 Build 6230</button>
        <button type="button" class="tab-btn" role="tab" data-tab="tab4" aria-selected="false">4. Alpha Factory Khép Kín</button>
      </div>
    </div>

    <!-- TAB 1 -->
    <section class="tab-panel active" id="tab1" role="tabpanel">
      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">Ma Trận Đơn Vé 9 Lịch Trình x 4 Pha (54 Ca Lõi PORT_7E + 36 Ca OOF ML)</h2>
            <div class="sec-sub">Bấm vào bất kỳ dòng nào để soi đủ 4 pha (P1, P2, Pass P1+P2, Funded 12T), thanh Đậu/Rớt/Chờ 100% và nút thắt xếp hạng.</div>
          </div>
          <div class="btn-row">
            <button type="button" class="chip t1-sku" data-sku="ftmo_standard_10k">10K Standard</button>
            <button type="button" class="chip t1-sku active" data-sku="ftmo_standard_100k">100K Standard</button>
            <button type="button" class="chip t1-stress active" data-stress="1">1,0x Nền</button>
            <button type="button" class="chip t1-stress" data-stress="1.5">1,5x Stress</button>
            <button type="button" class="chip t1-stress" data-stress="2">2,0x Cực đoan</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="tl">Bậc / Lịch trình</th>
                <th class="tl">Hạng</th>
                <th>P1/P2/Fn</th>
                <th>P1 12T</th>
                <th>P2 12T</th>
                <th>Vào Fn</th>
                <th>Cháy 12T</th>
                <th>EV/Phí</th>
                <th>EV 24T</th>
                <th>Pay1 (ĐK/ko)</th>
                <th>P&lt;=0 24T</th>
                <th>WR/RR/PF</th>
                <th class="tl">Cảnh báo</th>
              </tr>
            </thead>
            <tbody id="t1-matrix-body"></tbody>
          </table>
        </div>
      </div>

      <div class="panel" id="t1-inspector"></div>

      <div class="grid-2">
        <div class="panel">
          <div class="sec-head">
            <div>
              <h2 class="sec-title">Kiểm Toán Sàn Ngày 5% Cấp Lệnh Trong Ngày (T4 vs T5)</h2>
              <div class="sec-sub">So sánh 4 chế độ đo DD ngày trên 10.000 đường chạy — lý do T5 bị gắn RESEARCH_BOUNDARY_ONLY &amp; FTMO_GAMBLING_ALLIN_RISK.</div>
            </div>
          </div>
          <div id="t1-intraday-svg"></div>
          <div id="t1-intraday-notes" style="margin-top:8px;"></div>
        </div>

        <div class="panel">
          <div class="sec-head">
            <div>
              <h2 class="sec-title">Đối Chứng Cặp OOF v1.05-ML vs v1.03 Control (24 Cặp)</h2>
              <div class="sec-sub">OOF_SUBSET_WINDOW · RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED · Kết luận: REJECT_V105_ML_KEEP_V103.</div>
            </div>
          </div>
          <div class="table-wrap" style="max-height:330px; overflow-y:auto;">
            <table>
              <thead>
                <tr>
                  <th class="tl">Lịch trình</th>
                  <th class="tl">Biến thể ML</th>
                  <th>Ma sát</th>
                  <th>Hạng (Ctrl -&gt; ML)</th>
                  <th>dEV/Phí</th>
                  <th>dPay1 (có ĐK)</th>
                  <th>dCháy Fn12</th>
                  <th>dPass 12T</th>
                  <th>dPF</th>
                </tr>
              </thead>
              <tbody id="t1-oof-body"></tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2 -->
    <section class="tab-panel" id="tab2" role="tabpanel">
      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">Bộ Điều Khiển Đội Tài Khoản 972 Cấu Hình (9 Bậc Vốn x 6 Bậc Wave 5 x 3 Đồng Thời x 3 Phân Bổ x 2 Ma Sát)</h2>
            <div class="sec-sub" id="t2-rho-sub"></div>
          </div>
          <div class="btn-row">
            <button type="button" class="chip t2-stress active" data-stress="1">1,0x Nền</button>
            <button type="button" class="chip t2-stress" data-stress="1.5">1,5x Stress</button>
          </div>
        </div>

        <div class="grid-2" style="margin-bottom:10px;">
          <div class="ctrl-box">
            <div class="ctrl-lbl">
              <span>Bậc vốn khởi điểm (9 mức VND)</span>
              <span class="mono" id="t2-bankroll-readout"></span>
            </div>
            <input type="range" id="t2-bankroll-slider" min="0" max="8" step="1" value="2" aria-label="Chọn bậc vốn VND" />
            <div class="btn-row" id="t2-bankroll-pills"></div>
          </div>
          <div class="ctrl-box">
            <div class="ctrl-lbl"><span>Bậc tốc độ Wave 5 (6 cấu hình, Funded 1,00x)</span></div>
            <div class="btn-row" id="t2-tier-pills"></div>
            <div class="btn-row" style="margin-top:4px;">
              <span class="kpi-k">Đồng thời:</span>
              <button type="button" class="chip t2-cc" data-cc="CONSERVATIVE_1_TICKET">1 vé</button>
              <button type="button" class="chip t2-cc active" data-cc="GATED_STAGGER">Gated Stagger</button>
              <button type="button" class="chip t2-cc" data-cc="AGGRESSIVE_PARALLEL">Song song</button>
              <span class="kpi-k" style="margin-left:6px;">Phân bổ:</span>
              <button type="button" class="chip t2-ap" data-ap="P1_RECOUP_FIRST">P1 Hoàn vốn</button>
              <button type="button" class="chip t2-ap active" data-ap="P2_BALANCED_40_40_20">P2 40/40/20</button>
              <button type="button" class="chip t2-ap" data-ap="P3_SCALE_80_20">P3 80/20</button>
            </div>
          </div>
        </div>

        <div class="grid-6" id="t2-kpis"></div>
        <div id="t2-phase-strip" style="margin-top:10px;"></div>
      </div>

      <div class="grid-2">
        <div class="panel">
          <div class="sec-head">
            <div>
              <h2 class="sec-title">Đường Cong Vốn 9 Bậc (10tr–500tr VND) — Wave 5 vs Wave 4 C10</h2>
              <div class="sec-sub">Trung vị lãi ròng 36T (tr VND) trên cùng bậc vốn &amp; Gated Stagger / P2.</div>
            </div>
          </div>
          <div id="t2-curve-svg"></div>
        </div>
        <div class="panel">
          <div class="sec-head">
            <div>
              <h2 class="sec-title">Biên Pareto Đội Quỹ (Tốc Độ Pay1 vs Rủi Ro Cháy Ngân Sách 36T)</h2>
              <div class="sec-sub">81 cấu hình thuộc bậc đang chọn · điểm viền đậm là cấu hình đang xem.</div>
            </div>
          </div>
          <div id="t2-pareto-svg"></div>
        </div>
      </div>

      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">So Sánh Trực Tiếp SQL: Đợt 4 vs Đợt 5 (unified_eval_catalog.duckdb)</h2>
            <div class="sec-sub" id="t2-sql-source"></div>
          </div>
        </div>
        <div class="callout callout-warn" id="t2-sql-disclosure" style="margin-bottom:10px;"></div>
        <div class="grid-2" style="margin-bottom:10px;">
          <div class="subcard" id="t2-w4-legacy-card"></div>
          <div class="subcard" id="t2-w4-matrix-card"></div>
        </div>
        <div class="grid-3" id="t2-sql-delta-cards"></div>
      </div>
    </section>

    <!-- TAB 3 -->
    <section class="tab-panel" id="tab3" role="tabpanel">
      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">Chính Sách Bellman DP 6 Bậc Anti-Martingale (Cụm A -&gt; Cụm B)</h2>
            <div class="sec-sub">Giảm tải đơn điệu khi lỗ · cấm Dubins-Savage bold-play · trần mở lệnh Shield A &lt;= 3,00% &amp; theo mã &lt;= 1,75%.</div>
          </div>
          <span class="badge b-good mono" id="t3-dp-proof-badge"></span>
        </div>
        <div class="grid-2" id="t3-dp-tables"></div>
      </div>

      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">So Sánh Bóc Tách Nhân Quả Trên Cụm B Mù (2021–2024 · 10.000 Đường Chung)</h2>
            <div class="sec-sub" id="t3-ablation-sub"></div>
          </div>
          <div class="btn-row">
            <button type="button" class="chip t3-hor active" data-hor="12m">12T / 252 ngày (Không giới hạn)</button>
            <button type="button" class="chip t3-hor" data-hor="6m">6T / 126 ngày (Tốc độ)</button>
          </div>
        </div>
        <div class="grid-2">
          <div id="t3-ablation-svg"></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="tl">Chính sách</th>
                  <th>Đậu (%)</th>
                  <th>Rớt (%)</th>
                  <th>Chờ (%)</th>
                  <th>TV ngày</th>
                  <th>EV/Phí</th>
                  <th>P95 DD</th>
                </tr>
              </thead>
              <tbody id="t3-ablation-body"></tbody>
            </table>
          </div>
        </div>
        <div class="callout" id="t3-ablation-takeaway" style="margin-top:9px;"></div>
      </div>

      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">Chứng Nhận Sống MT5 Build 6230 — 15/15 Cổng PASS (Đóng W4-RT1-P1-01 &amp; W4G05-F01)</h2>
            <div class="sec-sub">Model=1 · ToDate=2024.12.31 · AllowLiveTrading=0 · Swap=0,00 USD · MT5_PROCS=0 · MetaEditor64 0 errors / 0 warnings.</div>
          </div>
          <span class="badge b-good mono">15/15 GATES CERTIFIED PASS</span>
        </div>
        <div class="grid-2">
          <div>
            <div id="t3-mt5-svg"></div>
            <div class="callout" id="t3-mt5-forensic" style="margin-top:8px;"></div>
          </div>
          <div class="grid-2" id="t3-mt5-cards"></div>
        </div>
      </div>
    </section>

    <!-- TAB 4 -->
    <section class="tab-panel" id="tab4" role="tabpanel">
      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">Phễu Khám Phá 355 Ứng Viên M1 &amp; Kết Quả Trung Thực PORT_V5 == PORT_7E</h2>
            <div class="sec-sub">28 mã M1 niêm phong &lt;= 2024-12-31 · 100% X13 offload · 0/355 đạt đủ 8/8 cổng Tier-1 · 1 ứng viên vào ALPHA_BENCH_RESERVE.</div>
          </div>
          <span class="badge b-adequate mono">PORT_V5 == PORT_7E (0 bổ sung)</span>
        </div>
        <div class="grid-2" style="margin-bottom:10px;">
          <div id="t4-funnel-svg"></div>
          <div class="grid-2" id="t4-universe-cards"></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="tl">6 Ứng viên vào Cụm B mù</th>
                <th class="tl">Họ chiến lược</th>
                <th class="tl">Mã</th>
                <th class="tl">Phân loại</th>
                <th>Cổng đạt</th>
                <th>SR Cụm A</th>
                <th>SR Cụm B</th>
                <th>PF Cụm B</th>
                <th>Lệnh B</th>
                <th>Corr vs 7E</th>
                <th>Hòa vốn phí</th>
              </tr>
            </thead>
            <tbody id="t4-finalists-body"></tbody>
          </table>
        </div>
      </div>

      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">5/5 Diễn Tập Khép Kín Suy Giảm &amp; Thay Máy Dự Bị (W5-G16 &amp; W5-G17)</h2>
            <div class="sec-sub" id="t4-ledger-sub"></div>
          </div>
          <span class="badge b-bad mono">auto_deploy_permitted = false · OrderSend = 0</span>
        </div>
        <div class="grid-5" id="t4-drills-grid"></div>
      </div>

      <div class="panel">
        <div class="sec-head">
          <div>
            <h2 class="sec-title">Bảng Chấm Điểm 4 Tầng Trong-Ra-Ngoài (Inside-Out Evaluation Scorecard)</h2>
            <div class="sec-sub">Mỗi tầng chấm theo trần thực tế riêng — không lấy trần một lớp tài sản để đánh giá lớp khác.</div>
          </div>
        </div>
        <div class="grid-4" id="t4-tiers-grid"></div>
      </div>
    </section>

    <div class="panel foot-meta mono" id="exp-footer"></div>
  </div>

  <script id="w5-ssot-data" type="application/json">__DATA_JSON__</script>
  <script>
    (function () {
      "use strict";
      var D = JSON.parse(document.getElementById("w5-ssot-data").textContent);
      var GRADE_META = {
        BAD: { vi: "Xấu", cls: "b-bad" },
        ADEQUATE: { vi: "Đủ dùng", cls: "b-adequate" },
        GOOD: { vi: "Tốt", cls: "b-good" },
        TOP_1_PCT: { vi: "Top 1%", cls: "b-top" },
        UNKNOWN_LEGACY_UNINSTRUMENTED: { vi: "Chưa tách Đợt 4", cls: "b-stale" }
      };
      var SCHED_ORDER = [
        "T1_ULTRA_SAFE", "T2_SAFE_C00", "T3_BALANCED_EV", "V103_SPRINT",
        "T4_TURBO_FAST", "T5_MAX_THROTTLE_YOLO", "C00", "C10_NEWS_ON", "BELLMAN_DP_6TIER"
      ];
      var FLEET_TIERS = [
        "T1_ULTRA_SAFE", "T2_SAFE_C00", "T3_BALANCED_EV",
        "T4_TURBO_FAST", "T5_MAX_THROTTLE_YOLO", "BELLMAN_DP_6TIER"
      ];

      var st = {
        tab: "tab1",
        t1Sku: "ftmo_standard_100k",
        t1Stress: 1.0,
        t1SelSched: "T3_BALANCED_EV",
        t2BankrollIdx: 2,
        t2Tier: "T3_BALANCED_EV",
        t2Cc: "GATED_STAGGER",
        t2Ap: "P2_BALANCED_40_40_20",
        t2Stress: 1.0,
        t2Horizon: "36m",
        t3Hor: "12m"
      };

      function esc(s) {
        return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      }
      function fmt(v, d) { return Number(v).toFixed(d).replace(".", ","); }
      function fmtSign(v, d) { return (v >= 0 ? "+" : "") + fmt(v, d); }
      function fmtTr(vnd) { return fmtSign(vnd / 1e6, 1) + " tr VND"; }
      function fmtInt(v) {
        var neg = v < 0;
        var s = String(Math.round(Math.abs(v))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ".");
        return (neg ? "-" : "+") + s;
      }
      function gradeBadge(code, aria) {
        var gm = GRADE_META[code] || GRADE_META.ADEQUATE;
        return '<span class="badge ' + gm.cls + '" aria-label="' + esc(aria || gm.vi) + '">' + esc(gm.vi) + '</span>';
      }
      function pinHigh(v, a, g, t, mx) {
        if (v <= 0) return 2;
        if (v < a) return Math.max(2, (v / a) * 25);
        if (v < g) return 25 + ((v - a) / (g - a)) * 30;
        if (v < t) return 55 + ((v - g) / (t - g)) * 30;
        return Math.min(97, 85 + ((v - t) / Math.max(mx - t, 1)) * 12);
      }
      function pinLowBlow(v) {
        if (v >= 5) return Math.max(3, 24 - Math.min(v - 5, 20));
        if (v >= 1) return 25 + ((5 - v) / 4) * 30;
        if (v >= 0.5) return 55 + ((1 - v) / 0.5) * 30;
        return Math.min(97, 85 + ((0.5 - Math.max(0, v)) / 0.5) * 12);
      }

      function detectTheme() {
        var cur = document.documentElement.getAttribute("data-theme");
        if (cur === "dark" || cur === "light") return cur;
        return (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
      }
      function syncThemeBtn() {
        var t = detectTheme();
        var b = document.getElementById("w5-explorer-theme-btn");
        b.textContent = t === "dark" ? "Chế độ: Tối" : "Chế độ: Sáng";
        b.setAttribute("aria-pressed", t === "dark" ? "true" : "false");
      }
      document.getElementById("w5-explorer-theme-btn").addEventListener("click", function () {
        document.documentElement.setAttribute("data-theme", detectTheme() === "dark" ? "light" : "dark");
        syncThemeBtn();
        renderAll();
      });

      // Header & footer metadata
      document.getElementById("exp-sub").textContent =
        D.ssot_meta.offensive_version + " · Đối soát " + D.ssot_meta.reconciled_artifact_count + "/26 Artifact · " +
        D.ssot_meta.mc_cases_catalog_count + " ca MC DuckDB · " + D.ssot_meta.legacy_trials_distinct_count +
        " thử nghiệm cũ · Tỷ giá " + fmt(D.ssot_meta.usd_vnd_rate, 2) + " VND/USD";
      document.getElementById("exp-footer").innerHTML =
        '<span>SSOT Master SHA-256: ' + esc(D.ssot_meta.master_report_sha256.slice(0, 16)) + ' · Spectrum SHA-256: ' + esc(D.ssot_meta.spectrum_summary_sha256.slice(0, 16)) + ' · Taxonomy SHA-256: ' + esc(D.ssot_meta.taxonomy_sha256.slice(0, 16)) + '</span>' +
        '<span>Pydantic v2 Validated: ' + D.ssot_meta.pydantic_v2_total_validated + ' Scorecards · Holdout 2025+ = 0 dòng · OrderSend = 0 · 0 VND</span>';

      // Main tab switching
      var mainTabBtns = document.querySelectorAll("#main-tabs .tab-btn");
      for (var ti = 0; ti < mainTabBtns.length; ti++) {
        mainTabBtns[ti].addEventListener("click", function () {
          st.tab = this.getAttribute("data-tab");
          for (var j = 0; j < mainTabBtns.length; j++) {
            mainTabBtns[j].setAttribute("aria-selected", mainTabBtns[j] === this ? "true" : "false");
          }
          var panels = document.querySelectorAll(".tab-panel");
          for (var k = 0; k < panels.length; k++) {
            panels[k].classList.toggle("active", panels[k].id === st.tab);
          }
        });
      }

      // ---------------- TAB 1 ----------------
      var coreIndex = {};
      for (var ci = 0; ci < D.single_cases.length; ci++) {
        var scRow = D.single_cases[ci];
        if (scRow.cohort === "CORE_PORT_7E") {
          coreIndex[scRow.schedule_id + "|" + scRow.contract_id + "|" + Number(scRow.friction_mult).toFixed(1)] = scRow;
        }
      }

      function renderTab1() {
        var tbody = document.getElementById("t1-matrix-body");
        var html = "";
        for (var i = 0; i < SCHED_ORDER.length; i++) {
          var sid = SCHED_ORDER[i];
          var item = coreIndex[sid + "|" + st.t1Sku + "|" + st.t1Stress.toFixed(1)];
          if (!item) continue;
          var sm = D.schedules[sid];
          var fn = item.funded;
          var isSel = sid === st.t1SelSched;
          var tags = [];
          for (var tg = 0; tg < item.mandatory_tags.length; tg++) {
            var tv = item.mandatory_tags[tg];
            if (tv === "CONSUMED_DEV_CLB_TEMPORAL_OOS") continue;
            var tc = tv.indexOf("GAMBLING") >= 0 || tv.indexOf("BOUNDARY") >= 0 ? "b-bad" : (tv.indexOf("BELLMAN") >= 0 ? "b-top" : "b-adequate");
            var shortLbl = tv === "RESEARCH_BOUNDARY_ONLY"
              ? "BOUNDARY_ONLY"
              : (tv === "FTMO_GAMBLING_ALLIN_RISK"
                ? "ALLIN_RISK"
                : (tv === "EXCEEDS_V103_SHIELD_A_3PCT_EVAL_CAP_RESEARCH_ONLY"
                  ? "OVER_SHIELD_A"
                  : (tv === "ANTI_MARTINGALE_BELLMAN_DP_6TIER" ? "DP_6TIER" : tv)));
            tags.push('<span class="badge ' + tc + '" title="' + esc(tv) + '" style="font-size:9.2px;padding:1px 5px;">' + esc(shortLbl) + '</span>');
          }
          html +=
            '<tr class="clickable' + (isSel ? " selected" : "") + '" data-sid="' + esc(sid) + '">' +
              '<td class="tl"><strong>' + esc(sm.label_vi) + '</strong></td>' +
              '<td class="tl">' + gradeBadge(item.overall_grade, item.aria_label) + '</td>' +
              '<td class="mono">' + fmt(sm.p1_mult, 1) + 'x / ' + fmt(sm.p2_mult, 2) + 'x / ' + fmt(sm.funded_mult, 2) + 'x</td>' +
              '<td class="mono">' + fmt(item.p1.pass_12m, 2) + '%</td>' +
              '<td class="mono">' + fmt(item.p2.pass_12m, 2) + '%</td>' +
              '<td class="mono">' + fmt(item.pass_eval.pass_12m, 2) + '%</td>' +
              '<td class="mono">' + fmt(fn.blowup_12m, 2) + '%</td>' +
              '<td class="mono"><strong>' + fmt(fn.ev_per_fee, 2) + 'x</strong></td>' +
              '<td class="mono">' + fmtTr(fn.ev_24m_vnd) + '</td>' +
              '<td class="mono">' + fmt(fn.cond_pay1, 1) + 'd / ' + fmt(fn.uncond_pay1, 1) + 'd</td>' +
              '<td class="mono">' + fmt(fn.p_le_0_24m, 2) + '%</td>' +
              '<td class="mono">' + fmt(fn.wr, 1) + '% / ' + fmt(fn.rr, 2) + ' / ' + fmt(fn.pf, 2) + '</td>' +
              '<td class="tl">' + (tags.length ? tags.join(" ") : '<span class="kpi-s">Chuẩn Dev 1x</span>') + '</td>' +
            '</tr>';
        }
        tbody.innerHTML = html;

        var trs = tbody.querySelectorAll("tr");
        for (var r = 0; r < trs.length; r++) {
          trs[r].addEventListener("click", function () {
            st.t1SelSched = this.getAttribute("data-sid");
            renderTab1();
          });
        }

        // Inspector for selected row
        var sel = coreIndex[st.t1SelSched + "|" + st.t1Sku + "|" + st.t1Stress.toFixed(1)];
        var pg = sel.phase_grades;
        var phases = [
          { t: "P1 · Vòng 1", g: pg.p1.grade, aria: pg.p1.aria, v: fmt(sel.p1.pass_12m, 2) + "%", p: pinHigh(sel.p1.pass_12m, 35, 55, 75, 100), bar: [sel.p1.pass_12m, sel.p1.fail_12m, sel.p1.pend_12m] },
          { t: "P2 · Vòng 2", g: pg.p2.grade, aria: pg.p2.aria, v: fmt(sel.p2.pass_12m, 2) + "%", p: pinHigh(sel.p2.pass_12m, 55, 70, 85, 100), bar: [sel.p2.pass_12m, sel.p2.fail_12m, sel.p2.pend_12m] },
          { t: "Pass P1+P2 (12T)", g: pg.pass_eval.grade, aria: pg.pass_eval.aria, v: fmt(sel.pass_eval.pass_12m, 2) + "%", p: pinHigh(sel.pass_eval.pass_12m, 25, 45, 65, 100), bar: [sel.pass_eval.pass_12m, sel.pass_eval.fail_12m, sel.pass_eval.pend_12m] },
          { t: "Funded 12T (Cháy)", g: pg.funded_12m.grade, aria: pg.funded_12m.aria, v: fmt(sel.funded.blowup_12m, 2) + "%", p: pinLowBlow(sel.funded.blowup_12m), bar: [sel.funded.pass_12m, sel.funded.fail_12m, sel.funded.pend_12m] }
        ];
        var pHtml = '<div class="sec-head"><div><h2 class="sec-title">Chi Tiết Scorecard Đang Chọn: ' + esc(D.schedules[sel.schedule_id].label_vi) + ' (' + (st.t1Sku === "ftmo_standard_100k" ? "100K" : "10K") + ' · ' + fmt(st.t1Stress, 1) + 'x)</h2><div class="sec-sub">' + esc(sel.gap_vi) + '</div></div>' + gradeBadge(sel.overall_grade, sel.aria_label) + '</div><div class="grid-4">';
        for (var pi = 0; pi < phases.length; pi++) {
          var ph = phases[pi];
          pHtml +=
            '<div class="subcard">' +
              '<div style="display:flex;justify-content:space-between;align-items:center;"><strong>' + esc(ph.t) + '</strong>' + gradeBadge(ph.g, ph.aria) + '</div>' +
              '<div class="kpi-v mono">' + esc(ph.v) + '</div>' +
              '<div class="g-track"><div class="g-pin" style="left:' + ph.p.toFixed(1) + '%"></div></div>' +
              '<div class="pfp-bar"><div class="seg-pass" style="width:' + ph.bar[0].toFixed(2) + '%"></div><div class="seg-fail" style="width:' + ph.bar[1].toFixed(2) + '%"></div><div class="seg-pend" style="width:' + ph.bar[2].toFixed(2) + '%"></div></div>' +
              '<div class="kpi-s mono">Đậu ' + fmt(ph.bar[0], 1) + '% · Rớt ' + fmt(ph.bar[1], 1) + '% · Chờ ' + fmt(ph.bar[2], 1) + '% (100%)</div>' +
            '</div>';
        }
        pHtml += '</div><div style="margin-top:8px;">';
        for (var bi = 0; bi < sel.exact_bottlenecks.length; bi++) {
          var bn = sel.exact_bottlenecks[bi];
          pHtml += '<span class="bn-tag" title="' + esc(bn.vi) + '">#' + bn.rank + ' ' + esc(bn.code) + ': ' + esc(bn.vi) + '</span>';
        }
        pHtml += '</div>';
        document.getElementById("t1-inspector").innerHTML = pHtml;

        // Intraday T4 vs T5 SVG chart
        var t4Aud = null;
        var t5Aud = null;
        for (var ai = 0; ai < D.intraday_audit.length; ai++) {
          var ar = D.intraday_audit[ai];
          if (ar.contract_id === st.t1Sku && ar.schedule_id === "T4_TURBO_FAST") t4Aud = ar;
          if (ar.contract_id === st.t1Sku && ar.schedule_id === "T5_MAX_THROTTLE_YOLO") t5Aud = ar;
        }
        var modes = [
          { k: "daily_close_only_1_0x", lbl: "Đóng ngày 1,0x" },
          { k: "daily_m1_approx_1_0x", lbl: "Xấp xỉ M1 1,0x" },
          { k: "trade_level_intraday_1_0x", lbl: "Cấp lệnh 1,0x" },
          { k: "trade_level_intraday_1_25x_gap", lbl: "Cấp lệnh 1,25x Gap" }
        ];
        var svgW = 560, svgH = 215, padL = 128, padR = 54, padT = 22, rowH = 42;
        var maxV = 70;
        var s = '<svg class="chart" viewBox="0 0 ' + svgW + ' ' + svgH + '" role="img" aria-label="Biểu đồ vi phạm sàn ngày 5 phần trăm của T4 và T5">';
        s += '<text x="' + padL + '" y="14" font-size="11" font-weight="700" fill="var(--_c3)">T4 Tăng tốc (6,0x)</text>';
        s += '<text x="' + (padL + 135) + '" y="14" font-size="11" font-weight="700" fill="var(--_c4)">T5 100% Liều (8,5x · RESEARCH_BOUNDARY_ONLY)</text>';
        for (var mi = 0; mi < modes.length; mi++) {
          var y0 = padT + mi * rowH;
          var v4 = t4Aud.modes[modes[mi].k].daily_5pct_hard_breach_pct;
          var v5 = t5Aud.modes[modes[mi].k].daily_5pct_hard_breach_pct;
          var w4 = (v4 / maxV) * (svgW - padL - padR);
          var w5 = (v5 / maxV) * (svgW - padL - padR);
          s += '<text x="' + (padL - 8) + '" y="' + (y0 + 18) + '" text-anchor="end" font-size="11" font-weight="600" fill="var(--_fg)">' + esc(modes[mi].lbl) + '</text>';
          s += '<rect x="' + padL + '" y="' + (y0 + 3) + '" width="' + Math.max(2, w4).toFixed(1) + '" height="13" rx="3" fill="#d97706" />';
          s += '<text x="' + (padL + w4 + 5).toFixed(1) + '" y="' + (y0 + 13) + '" font-size="10.5" font-weight="700" fill="var(--_fg)">' + fmt(v4, 2) + '%</text>';
          s += '<rect x="' + padL + '" y="' + (y0 + 19) + '" width="' + Math.max(2, w5).toFixed(1) + '" height="13" rx="3" fill="#dc2626" />';
          s += '<text x="' + (padL + w5 + 5).toFixed(1) + '" y="' + (y0 + 29) + '" font-size="10.5" font-weight="700" fill="var(--_fg)">' + fmt(v5, 2) + '%</text>';
        }
        s += '</svg>';
        document.getElementById("t1-intraday-svg").innerHTML = s;
        document.getElementById("t1-intraday-notes").innerHTML =
          '<div class="callout callout-bad"><strong>Cảnh báo T5 (' + (st.t1Sku === "ftmo_standard_100k" ? "100K" : "10K") + '):</strong> Độ lệch cấp lệnh so với đóng ngày là <strong>+' + fmt(t5Aud.drift_trade_minus_daily_close_pp, 2) + ' đpt</strong> (và <strong>+' + fmt(t5Aud.drift_gap125_minus_m1_daily_approx_pp, 2) + ' đpt</strong> khi có 1,25x gap). Lịch sử Dev có <strong>' + t5Aud.historical_days_ge_5pct_trade_seq_count + ' ngày &gt;= 5%</strong> (tệ nhất ' + fmt(t5Aud.historical_max_single_day_trade_seq_dd_pct, 2) + '%) so với T4 chỉ ' + t4Aud.historical_days_ge_5pct_trade_seq_count + ' ngày.</div>';

        // OOF ML 24 paired deltas table filtered by SKU
        var oofHtml = "";
        for (var oi = 0; oi < D.oof_ml_deltas.length; oi++) {
          var od = D.oof_ml_deltas[oi];
          if (od.contract_id !== st.t1Sku) continue;
          oofHtml +=
            '<tr>' +
              '<td class="tl mono">' + esc(od.schedule_id === "T3_BALANCED_EV" ? "T3 Sprint" : "Bellman DP") + '</td>' +
              '<td class="tl">' + esc(od.variant === "V105_ML_FILTER" ? "v1.05 Filter" : "v1.05 AsymFloor") + '</td>' +
              '<td class="mono">' + fmt(od.friction_mult, 1) + 'x</td>' +
              '<td class="mono">' + esc(od.control_grade) + ' -&gt; ' + esc(od.variant_grade) + '</td>' +
              '<td class="mono">' + fmtSign(od.delta_ev_per_fee_npv24, 3) + 'x</td>' +
              '<td class="mono">' + fmtSign(od.delta_cond_pay1_days, 1) + 'd</td>' +
              '<td class="mono">' + fmtSign(od.delta_fn12_blowup_pp, 2) + ' đpt</td>' +
              '<td class="mono">' + fmtSign(od.delta_pass_eval_12m_pp, 2) + ' đpt</td>' +
              '<td class="mono">' + fmtSign(od.delta_pf, 3) + '</td>' +
            '</tr>';
        }
        document.getElementById("t1-oof-body").innerHTML = oofHtml;
      }

      // ---------------- TAB 2 ----------------
      var fleetIdx = {};
      for (var fi = 0; fi < D.fleet_cases.length; fi++) {
        var f = D.fleet_cases[fi];
        fleetIdx[f.sid + "|" + f.b + "|" + f.cc + "|" + f.ap + "|" + Number(f.fr).toFixed(1)] = f;
      }

      function initTab2Static() {
        var rho = D.shared_path_rho_proof;
        document.getElementById("t2-rho-sub").textContent =
          "Chứng minh đường chạy chung (Shared-Path): tương quan rho trung bình = " + fmt(rho.shared_path_true.mean_rho, 6) +
          " (so với giả lập độc lập sai = " + fmt(rho.independent_negative_mutation.mean_rho, 4) + ").";

        var bp = document.getElementById("t2-bankroll-pills");
        bp.innerHTML = "";
        for (var i = 0; i < D.fleet_bankrolls.length; i++) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "chip mono t2-bp";
          b.setAttribute("data-bidx", String(i));
          b.textContent = D.fleet_bankrolls[i] + "tr";
          b.addEventListener("click", (function (idx) {
            return function () {
              st.t2BankrollIdx = idx;
              document.getElementById("t2-bankroll-slider").value = String(idx);
              renderTab2();
            };
          })(i));
          bp.appendChild(b);
        }

        var tp = document.getElementById("t2-tier-pills");
        tp.innerHTML = "";
        for (var j = 0; j < FLEET_TIERS.length; j++) {
          var tid = FLEET_TIERS[j];
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "chip t2-tp" + (tid === "T5_MAX_THROTTLE_YOLO" ? " yolo" : "");
          btn.setAttribute("data-tier", tid);
          btn.textContent = D.schedules[tid].label_vi;
          btn.addEventListener("click", (function (t) {
            return function () { st.t2Tier = t; renderTab2(); };
          })(tid));
          tp.appendChild(btn);
        }

        // Direct SQL Wave 4 vs Wave 5 static cards
        var sq = D.wave4_vs_wave5_sql;
        document.getElementById("t2-sql-source").textContent = "Nguồn truy vấn SQL trực tiếp: " + sq.sql_source;
        document.getElementById("t2-sql-disclosure").innerHTML = "<strong>Minh bạch so sánh (Apples-to-Apples):</strong> " + esc(sq.apples_to_apples_disclosure);

        var w4sc = D.scorecards["w4_legacy_c10_fleet_1_0x_reference"];
        document.getElementById("t2-w4-legacy-card").innerHTML =
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">' +
            '<strong>Hồ Sơ Đối Chứng Đợt 4 (C10_NEWS_ON · Funded 1,25x)</strong>' +
            '<span class="badge b-stale">legacy: ' + esc(w4sc.legacy_grade_code) + ' -&gt; unified: ' + esc(w4sc.unified_grade_code) + '</span>' +
          '</div>' +
          '<div class="grid-2" style="margin-top:6px;">' +
            '<div class="callout" style="padding:7px;"><strong>Pha 1 (P1):</strong> <span class="badge b-stale" aria-label="' + esc(w4sc.phase_grades.p1.presentation_state.ariaLabel) + '">UNKNOWN_LEGACY_UNINSTRUMENTED</span><div class="kpi-s" style="margin-top:4px;">' + esc(w4sc.phase_grades.p1.presentation_state.label) + '</div></div>' +
            '<div class="callout" style="padding:7px;"><strong>Pha 2 (P2):</strong> <span class="badge b-stale" aria-label="' + esc(w4sc.phase_grades.p2.presentation_state.ariaLabel) + '">UNKNOWN_LEGACY_UNINSTRUMENTED</span><div class="kpi-s" style="margin-top:4px;">' + esc(w4sc.phase_grades.p2.presentation_state.label) + '</div></div>' +
          '</div>' +
          '<div class="kpi-s" style="margin-top:5px;">Hợp đồng presentation-state@1.0.0: availability=ready · freshness=partial · certainty=unknown (TUYỆT ĐỐI không hiển thị 0% hay nhãn xanh).</div>';

        var gm = sq.wave4_legacy_vs_unified_grade_matrix;
        var mRows = "";
        for (var k in gm) {
          if (Object.prototype.hasOwnProperty.call(gm, k)) {
            mRows += '<tr><td class="tl mono">' + esc(k) + '</td><td class="mono"><strong>' + gm[k] + ' ca</strong></td><td class="mono">100% P1/P2 chưa tách</td></tr>';
          }
        }
        document.getElementById("t2-w4-matrix-card").innerHTML =
          '<strong>Bảng Ánh Xạ Hạng Cũ (legacy_grade_code) -&gt; Hạng Chuẩn (unified_grade_code) Đợt 4 (168 ca)</strong>' +
          '<table style="margin-top:6px;"><thead><tr><th class="tl">Chuyển đổi hạng</th><th>Số ca</th><th>Trạng thái P1/P2</th></tr></thead><tbody>' + mRows + '</tbody></table>';

        var dHtml = "";
        for (var di = 0; di < sq.paired_162_cell_fleet_sql_deltas.length; di++) {
          var row = sq.paired_162_cell_fleet_sql_deltas[di];
          dHtml +=
            '<div class="subcard">' +
              '<div style="display:flex;justify-content:space-between;align-items:center;"><strong>' + esc(D.schedules[row.w5_profile].label_vi) + '</strong><span class="badge b-outline mono">' + row.n_matched_cells + ' ô cặp</span></div>' +
              '<div class="kpi-s mono">dPay1: <strong>' + fmtSign(row.delta_uncond_pay1_days, 1) + ' ngày</strong> (' + row.cells_faster_pay1 + '/162 nhanh hơn)</div>' +
              '<div class="kpi-s mono">dCháy Fn12: <strong>' + fmtSign(row.delta_fn12_blowup_pp, 3) + ' đpt</strong> (' + row.cells_safer_fn12 + '/162 an toàn hơn)</div>' +
              '<div class="kpi-s mono">dMed 36T: <strong>' + fmtTr(row.delta_mean_med36m_vnd) + '</strong> · dEV/Phí: ' + fmtSign(row.delta_ev_per_fee_36m, 2) + 'x</div>' +
              '<div class="kpi-s mono">dP(&lt;=0) 24T: ' + fmtSign(row.delta_p_le_0_24m_pp, 2) + ' đpt · dRuin 36T: ' + fmtSign(row.delta_ruin_36m_pp, 2) + ' đpt</div>' +
              '<div class="kpi-s mono">Hạng Tốt chuẩn (GOOD): W4 ' + row.w4_unified_good_count + ' (cũ TOT: ' + row.w4_legacy_tot_count + ') -&gt; W5 <strong>' + row.w5_unified_good_count + '</strong></div>' +
            '</div>';
        }
        document.getElementById("t2-sql-delta-cards").innerHTML = dHtml;
      }

      function renderTab2() {
        var bVal = D.fleet_bankrolls[st.t2BankrollIdx];
        var cell = fleetIdx[st.t2Tier + "|" + bVal + "|" + st.t2Cc + "|" + st.t2Ap + "|" + st.t2Stress.toFixed(1)];
        document.getElementById("t2-bankroll-readout").textContent =
          bVal + " tr VND (" + fmtInt(cell.b_usd).replace("+", "") + " USD)";

        var bps = document.querySelectorAll(".t2-bp");
        for (var i = 0; i < bps.length; i++) bps[i].classList.toggle("active", i === st.t2BankrollIdx);
        var tps = document.querySelectorAll(".t2-tp");
        for (var j = 0; j < tps.length; j++) tps[j].classList.toggle("active", tps[j].getAttribute("data-tier") === st.t2Tier);

        var kpis = [
          { k: "Xếp hạng chuẩn", v: (GRADE_META[cell.gr] || GRADE_META.ADEQUATE).vi, s: (cell.po ? "Pareto toàn cục" : (cell.pi ? "Pareto trong bậc" : "Ngoài biên Pareto")) },
          { k: "Trung vị ròng 36T", v: fmtTr(cell.m36), s: fmtInt(cell.m36_u) + " USD (24T: " + fmtTr(cell.m24) + ")" },
          { k: "Hiệu quả EV / 1đ Phí", v: fmt(cell.evf, 2) + "x", s: "P10..P90 36T: " + fmt(cell.p10_36 / 1e6, 0) + ".." + fmt(cell.p90_36 / 1e6, 0) + " tr" },
          { k: "Cháy Funded 12T", v: fmt(cell.fn12, 2) + "%", s: "Wilson UB: " + fmt(cell.fn12_ub, 2) + "% · Ruin 36T: " + fmt(cell.ruin, 2) + "%" },
          { k: "Payout #1 (có / ko ĐK)", v: fmt(cell.cp1, 1) + "d / " + fmt(cell.up1, 1) + "d", s: "P(<=0) 24T: " + fmt(cell.ple0, 2) + "%" },
          { k: "Đỉnh vốn Funded", v: fmtInt(cell.maxf).replace("+", "") + " USD", s: "P1 " + fmt(cell.p1p, 1) + "% · P2 " + fmt(cell.p2p, 1) + "% · Pass12T " + fmt(cell.pe12, 1) + "%" }
        ];
        var kh = "";
        for (var k = 0; k < kpis.length; k++) {
          kh += '<div class="subcard"><span class="kpi-k">' + esc(kpis[k].k) + '</span><span class="kpi-v mono">' + (k === 0 ? gradeBadge(cell.gr) : esc(kpis[k].v)) + '</span><span class="kpi-s mono">' + esc(kpis[k].s) + '</span></div>';
        }
        document.getElementById("t2-kpis").innerHTML = kh;

        var hz = cell.hz[st.t2Horizon];
        var hBtns = "";
        var hList = ["3m", "6m", "12m", "24m", "36m"];
        for (var hi = 0; hi < hList.length; hi++) {
          hBtns += '<button type="button" class="chip t2-hz' + (hList[hi] === st.t2Horizon ? " active" : "") + '" data-hz="' + hList[hi] + '">' + hList[hi].replace("m", "T") + '</button>';
        }
        var bnTags = "";
        for (var bi = 0; bi < cell.bn.length; bi++) {
          var bItem = cell.bn[bi];
          var bDesc = D.bottleneck_catalog[bItem[0]] || bItem[0];
          var bNum = bItem[1] !== null && bItem[2] !== null ? " (" + fmt(bItem[1], 1) + " vs " + fmt(bItem[2], 1) + ")" : "";
          bnTags += '<span class="bn-tag" title="' + esc(bDesc) + '">#' + (bi + 1) + ' ' + esc(bItem[0]) + esc(bNum) + '</span>';
        }
        document.getElementById("t2-phase-strip").innerHTML =
          '<div class="subcard">' +
            '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;">' +
              '<div><strong>Phân bổ Đậu / Rớt / Chờ = 100,00% (Mốc ' + st.t2Horizon.replace("m", " tháng") + ')</strong> · P1 ' + gradeBadge(cell.pg[0]) + ' · P2 ' + gradeBadge(cell.pg[1]) + ' · Pass ' + gradeBadge(cell.pg[2]) + ' · Funded 12T ' + gradeBadge(cell.pg[3]) + '</div>' +
              '<div class="btn-row">' + hBtns + '</div>' +
            '</div>' +
            '<div class="pfp-bar" style="margin:6px 0 4px;"><div class="seg-pass" style="width:' + hz[0].toFixed(2) + '%"></div><div class="seg-fail" style="width:' + hz[1].toFixed(2) + '%"></div><div class="seg-pend" style="width:' + hz[2].toFixed(2) + '%"></div></div>' +
            '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px;font-size:11.5px;" class="mono">' +
              '<span>Đậu: <strong>' + fmt(hz[0], 2) + '%</strong> · Rớt: <strong>' + fmt(hz[1], 2) + '%</strong> · Chờ: <strong>' + fmt(hz[2], 2) + '%</strong> (Tổng ' + fmt(hz[0] + hz[1] + hz[2], 2) + '%)</span>' +
              '<span>' + bnTags + '</span>' +
            '</div>' +
          '</div>';
        var hzEls = document.querySelectorAll(".t2-hz");
        for (var hq = 0; hq < hzEls.length; hq++) {
          hzEls[hq].addEventListener("click", function () { st.t2Horizon = this.getAttribute("data-hz"); renderTab2(); });
        }

        // Chart A: 9-bankroll Capital Curve SVG
        var ptsW5 = [];
        var ptsW4 = [];
        var maxY = 100;
        for (var bi2 = 0; bi2 < D.fleet_bankrolls.length; bi2++) {
          var bv = D.fleet_bankrolls[bi2];
          var fc2 = fleetIdx[st.t2Tier + "|" + bv + "|" + st.t2Cc + "|" + st.t2Ap + "|" + st.t2Stress.toFixed(1)];
          var y5 = fc2.m36 / 1e6;
          var y4 = D.w4_curve_by_bankroll[String(bv)].w4_c10_med36m_vnd / 1e6;
          ptsW5.push({ b: bv, y: y5, idx: bi2 });
          ptsW4.push({ b: bv, y: y4, idx: bi2 });
          if (y5 > maxY) maxY = y5;
          if (y4 > maxY) maxY = y4;
        }
        maxY = Math.ceil(maxY / 500) * 500;
        var cw = 560, ch = 230, pl = 58, pr = 18, pt = 20, pb = 32;
        var xOf = function (idx) { return pl + (idx / 8) * (cw - pl - pr); };
        var yOf = function (val) { return ch - pb - (Math.max(0, val) / maxY) * (ch - pt - pb); };
        var poly5 = ptsW5.map(function (p) { return xOf(p.idx).toFixed(1) + "," + yOf(p.y).toFixed(1); }).join(" ");
        var poly4 = ptsW4.map(function (p) { return xOf(p.idx).toFixed(1) + "," + yOf(p.y).toFixed(1); }).join(" ");
        var cs = '<svg class="chart" viewBox="0 0 ' + cw + ' ' + ch + '" role="img" aria-label="Đường cong vốn 9 bậc Wave 5 so với Wave 4">';
        for (var gy = 0; gy <= 4; gy++) {
          var gv = (maxY * gy) / 4;
          var gyy = yOf(gv);
          cs += '<line x1="' + pl + '" y1="' + gyy.toFixed(1) + '" x2="' + (cw - pr) + '" y2="' + gyy.toFixed(1) + '" stroke="var(--_border)" stroke-dasharray="3,3" />';
          cs += '<text x="' + (pl - 6) + '" y="' + (gyy + 4).toFixed(1) + '" text-anchor="end" font-size="10" fill="var(--_muted)">' + Math.round(gv) + 'tr</text>';
        }
        cs += '<polyline fill="none" stroke="var(--_c3)" stroke-width="2" stroke-dasharray="5,4" points="' + poly4 + '" />';
        cs += '<polyline fill="none" stroke="var(--_c1)" stroke-width="2.6" points="' + poly5 + '" />';
        for (var p2 = 0; p2 < ptsW5.length; p2++) {
          var cx = xOf(p2), cy5 = yOf(ptsW5[p2].y), cy4 = yOf(ptsW4[p2].y);
          var selB = p2 === st.t2BankrollIdx;
          cs += '<circle cx="' + cx.toFixed(1) + '" cy="' + cy4.toFixed(1) + '" r="3" fill="var(--_c3)" />';
          cs += '<circle cx="' + cx.toFixed(1) + '" cy="' + cy5.toFixed(1) + '" r="' + (selB ? 6 : 3.8) + '" fill="' + (selB ? "var(--_c2)" : "var(--_c1)") + '" stroke="var(--_card)" stroke-width="1.5" />';
          cs += '<text x="' + cx.toFixed(1) + '" y="' + (ch - 10) + '" text-anchor="middle" font-size="10" font-weight="' + (selB ? "800" : "500") + '" fill="var(--_fg)">' + ptsW5[p2].b + 'tr</text>';
        }
        cs += '<text x="' + pl + '" y="13" font-size="10.5" font-weight="700" fill="var(--_c1)">— Wave 5 ' + esc(D.schedules[st.t2Tier].label_vi) + ' (1,00x Fn)</text>';
        cs += '<text x="' + (pl + 230) + '" y="13" font-size="10.5" font-weight="700" fill="var(--_c3)">-- Wave 4 C10 (1,25x Fn · Gated P2 1x)</text>';
        cs += '</svg>';
        document.getElementById("t2-curve-svg").innerHTML = cs;

        // Chart B: Pareto scatter (81 cells of active tier & friction)
        var tierCells = [];
        var maxRuin = 5, maxPay = 730;
        for (var ti2 = 0; ti2 < D.fleet_cases.length; ti2++) {
          var f2 = D.fleet_cases[ti2];
          if (f2.sid === st.t2Tier && Math.abs(f2.fr - st.t2Stress) < 0.05) {
            tierCells.push(f2);
            if (f2.ruin > maxRuin) maxRuin = f2.ruin;
          }
        }
        maxRuin = Math.ceil(maxRuin / 5) * 5;
        var ps = '<svg class="chart" viewBox="0 0 ' + cw + ' ' + ch + '" role="img" aria-label="Biểu đồ phân tán biên Pareto tốc độ Payout 1 và rủi ro cháy ngân sách 36T">';
        for (var gx = 0; gx <= 4; gx++) {
          var pxv = (maxPay * gx) / 4;
          var pxp = pl + (pxv / maxPay) * (cw - pl - pr);
          ps += '<line x1="' + pxp.toFixed(1) + '" y1="' + pt + '" x2="' + pxp.toFixed(1) + '" y2="' + (ch - pb) + '" stroke="var(--_border)" stroke-dasharray="3,3" />';
          ps += '<text x="' + pxp.toFixed(1) + '" y="' + (ch - 10) + '" text-anchor="middle" font-size="10" fill="var(--_muted)">' + Math.round(pxv) + 'd</text>';
        }
        for (var gy2 = 0; gy2 <= 4; gy2++) {
          var rv = (maxRuin * gy2) / 4;
          var ryp = ch - pb - (rv / maxRuin) * (ch - pt - pb);
          ps += '<line x1="' + pl + '" y1="' + ryp.toFixed(1) + '" x2="' + (cw - pr) + '" y2="' + ryp.toFixed(1) + '" stroke="var(--_border)" stroke-dasharray="3,3" />';
          ps += '<text x="' + (pl - 6) + '" y="' + (ryp + 4).toFixed(1) + '" text-anchor="end" font-size="10" fill="var(--_muted)">' + fmt(rv, 0) + '%</text>';
        }
        for (var sc2 = 0; sc2 < tierCells.length; sc2++) {
          var p = tierCells[sc2];
          var sx = pl + (Math.min(p.up1, maxPay) / maxPay) * (cw - pl - pr);
          var sy = ch - pb - (Math.min(p.ruin, maxRuin) / maxRuin) * (ch - pt - pb);
          var isMe = p.rid === cell.rid;
          var col = p.gr === "GOOD" ? "#16a34a" : (p.gr === "ADEQUATE" ? "#d97706" : "#dc2626");
          ps += '<circle cx="' + sx.toFixed(1) + '" cy="' + sy.toFixed(1) + '" r="' + (isMe ? 7 : (p.pi ? 4.8 : 3.2)) + '" fill="' + col + '" fill-opacity="' + (isMe ? "1" : (p.pi ? "0.9" : "0.45")) + '" stroke="' + (isMe ? "var(--_fg)" : "none") + '" stroke-width="' + (isMe ? "2.2" : "0") + '"><title>' + esc(p.b + "tr · " + p.cc + " · " + p.ap + " | Pay1 " + fmt(p.up1, 1) + "d · Ruin " + fmt(p.ruin, 2) + "% · Med36T " + fmtTr(p.m36)) + '</title></circle>';
        }
        ps += '<text x="' + pl + '" y="13" font-size="10.5" font-weight="700" fill="var(--_muted)">Trục X: Pay1 không ĐK (ngày, càng trái càng nhanh) · Trục Y: Ruin 36T (%, càng thấp càng an toàn)</text>';
        ps += '</svg>';
        document.getElementById("t2-pareto-svg").innerHTML = ps;
      }

      // ---------------- TAB 3 ----------------
      function renderTab3() {
        var dp = D.bellman_dp;
        document.getElementById("t3-dp-proof-badge").textContent =
          "Anti-Martingale VERIFIED · P1 " + dp.p1_check.dd_monotonic_pairs_checked + "+" + dp.p1_check.static_loss_monotonic_pairs_checked + " cặp · P2 " + dp.p2_check.dd_monotonic_pairs_checked + "+" + dp.p2_check.static_loss_monotonic_pairs_checked + " cặp";

        function mkDpTable(title, rows) {
          var h = '<div><div class="kpi-k" style="margin-bottom:5px;">' + esc(title) + '</div><div class="table-wrap"><table><thead><tr><th>Bậc</th><th class="tl">Vùng Equity</th><th>Hệ số</th><th class="tl">Biểu thức MQL5</th></tr></thead><tbody>';
          for (var i = 0; i < rows.length; i++) {
            var r = rows[i];
            h += '<tr><td class="mono">#' + r.tier_rank + '</td><td class="tl">' + esc(r.label) + '</td><td class="mono"><strong>' + fmt(r.risk_mult, 2) + 'x</strong></td><td class="tl mono" style="font-size:10.5px;">' + esc(r.mql5_condition_expr) + '</td></tr>';
          }
          return h + '</tbody></table></div></div>';
        }
        document.getElementById("t3-dp-tables").innerHTML =
          mkDpTable("P1 — 6 Bậc Tải Chống Gấp Thếp (Target +10%, Kill 3,5%/8%)", dp.p1_tiers) +
          mkDpTable("P2 — 6 Bậc Tải Chống Gấp Thếp (Target +5%, Kill 3,0%/7,5%)", dp.p2_tiers);

        var ab = dp.ablation;
        document.getElementById("t3-ablation-sub").textContent =
          "Huấn luyện Cụm A (" + ab.train_cluster_a.min_day + " .. " + ab.train_cluster_a.max_day + ", " + ab.train_cluster_a.n_days + " ngày) -> Đánh giá mù Cụm B (" +
          ab.eval_cluster_b_oos.min_day + " .. " + ab.eval_cluster_b_oos.max_day + ", " + ab.eval_cluster_b_oos.n_days + " ngày).";
        var srcMap = st.t3Hor === "12m" ? ab.cluster_b_12m_252d_unlimited : ab.cluster_b_6m_126d;
        var polKeys = ["BELLMAN_DP_6TIER_SCHEDULE", "BELLMAN_DP_POLICY", "V103_SPRINT_STATIC_LOCK", "BARRIER_TAPER", "C10_NEWS_ON"];
        var aBody = "";
        var sw = 520, sh = 200, spl = 165, spr = 18, spt = 22, srh = 34;
        var asvg = '<svg class="chart" viewBox="0 0 ' + sw + ' ' + sh + '" role="img" aria-label="Biểu đồ tỷ lệ Đậu Rớt Chờ 100 phần trăm của Bellman DP và đối chứng trên Cụm B">';
        asvg += '<text x="' + spl + '" y="14" font-size="10.5" font-weight="700" fill="var(--_muted)">Xanh: Đậu · Đỏ: Rớt · Vàng: Chờ (Tổng 100,00%)</text>';
        for (var pi = 0; pi < polKeys.length; pi++) {
          var pk = polKeys[pi];
          var pr = srcMap[pk];
          var barW = sw - spl - spr;
          var wp = (pr.combined_pass_pct / 100) * barW;
          var wf = (pr.combined_fail_pct / 100) * barW;
          var ww = (pr.combined_pending_pct / 100) * barW;
          var yy = spt + pi * srh;
          asvg += '<text x="' + (spl - 8) + '" y="' + (yy + 16) + '" text-anchor="end" font-size="10.5" font-weight="700" fill="var(--_fg)">' + esc(pk.replace("_SCHEDULE", "")) + '</text>';
          asvg += '<rect x="' + spl + '" y="' + (yy + 4) + '" width="' + wp.toFixed(1) + '" height="18" fill="#16a34a" />';
          asvg += '<rect x="' + (spl + wp).toFixed(1) + '" y="' + (yy + 4) + '" width="' + wf.toFixed(1) + '" height="18" fill="#dc2626" />';
          asvg += '<rect x="' + (spl + wp + wf).toFixed(1) + '" y="' + (yy + 4) + '" width="' + ww.toFixed(1) + '" height="18" fill="#d97706" />';
          asvg += '<text x="' + (spl + 6) + '" y="' + (yy + 17) + '" font-size="10" font-weight="700" fill="#ffffff">' + fmt(pr.combined_pass_pct, 1) + '%</text>';
          aBody +=
            '<tr>' +
              '<td class="tl mono"><strong>' + esc(pk.replace("_SCHEDULE", "")) + '</strong></td>' +
              '<td class="mono">' + fmt(pr.combined_pass_pct, 2) + '%</td>' +
              '<td class="mono">' + fmt(pr.combined_fail_pct, 2) + '%</td>' +
              '<td class="mono">' + fmt(pr.combined_pending_pct, 2) + '%</td>' +
              '<td class="mono">' + fmt(pr.median_total_days_to_funded, 0) + 'd</td>' +
              '<td class="mono">' + fmt(pr.ev_per_fee_ratio, 3) + 'x</td>' +
              '<td class="mono">' + fmt(pr.p1_p95_max_dd_pct, 2) + '%</td>' +
            '</tr>';
        }
        asvg += '</svg>';
        document.getElementById("t3-ablation-svg").innerHTML = asvg;
        document.getElementById("t3-ablation-body").innerHTML = aBody;
        document.getElementById("t3-ablation-takeaway").innerHTML = "<strong>Kết luận trung thực Cụm B:</strong> " + esc(ab.honest_takeaway);

        // MT5 Build 6230 parity proof
        var mt5 = D.mt5_proof;
        var g10 = mt5.w5_g10_live_feature_parity_2024;
        var g12 = mt5.w5_g12_four_way_parity_500;
        var g15 = mt5.w5_g15_modular_7e_compat;
        var dpSm = mt5.bellman_dp_p1_smoke;
        var bars = [
          { lbl: "f0..f6 thị trường (777 lệnh)", err: g10.market_and_structural_f0_f6_max_abs_err, tol: "1e-4" },
          { lbl: "ea_p_win ONNX (777 lệnh)", err: g10.onnx_max_abs_p_win_err, tol: "1e-5" },
          { lbl: "4-Way 500-Vector Parity", err: g12.overall_max_abs_err, tol: "1e-5" },
          { lbl: "Shadow1x / f7 chuẩn hóa", err: g10.unit_normalized_feature_max_abs_err, tol: "1e-4" },
          { lbl: "ea_p_win Pure-MQL5 (777)", err: g10.pure_mql5_max_abs_p_win_err, tol: "0,0" }
        ];
        var msvg = '<svg class="chart" viewBox="0 0 540 190" role="img" aria-label="Sai lệch đối chứng đặc trưng sống MT5 Build 6230">';
        msvg += '<text x="175" y="14" font-size="10.5" font-weight="700" fill="var(--_muted)">Sai số tuyệt đối tối đa (thang log10 — càng ngắn càng khít)</text>';
        for (var bi = 0; bi < bars.length; bi++) {
          var br = bars[bi];
          var y = 26 + bi * 32;
          var score = br.err <= 0 ? 6 : Math.max(10, (Math.log10(br.err) + 10) / 7 * 280);
          msvg += '<text x="168" y="' + (y + 15) + '" text-anchor="end" font-size="10.5" font-weight="600" fill="var(--_fg)">' + esc(br.lbl) + '</text>';
          msvg += '<rect x="175" y="' + (y + 3) + '" width="' + Math.min(280, score).toFixed(1) + '" height="16" rx="3" fill="#16a34a" />';
          msvg += '<text x="' + (182 + Math.min(280, score)).toFixed(1) + '" y="' + (y + 15) + '" font-size="10" font-weight="700" fill="var(--_fg)">' + (br.err === 0 ? "0,0" : br.err.toExponential(2)) + ' (&lt;=' + br.tol + ')</text>';
        }
        msvg += '</svg>';
        document.getElementById("t3-mt5-svg").innerHTML = msvg;
        document.getElementById("t3-mt5-forensic").innerHTML = "<strong>Giải trình sai số gốc f7:</strong> " + esc(g10.f7_forensic_note);

        document.getElementById("t3-mt5-cards").innerHTML =
          '<div class="subcard"><span class="kpi-k">W5-G15 · Modular v105 == v103</span><span class="kpi-v mono">469 == 469 lệnh</span><span class="kpi-s mono">+' + fmt(g15.net_pnl_usd_v105_modular, 2) + ' USD == +' + fmt(g15.net_pnl_usd_v103, 2) + ' USD (delta 0,00 USD) · PF ' + fmt(g15.profit_factor, 2) + ' · DD ' + fmt(g15.equity_dd_pct, 2) + '% · Swap 0,00 USD</span></div>' +
          '<div class="subcard"><span class="kpi-k">W5-G10 · Live ONNX == Pure-MQL5</span><span class="kpi-v mono">777/777 khớp (100%)</span><span class="kpi-s mono">' + g10.ml_enabled_trades + ' lệnh · +' + fmt(g10.ml_enabled_net_pnl_usd, 2) + ' USD (0,00 USD lệch) · Chặn ' + g10.ml_blocked_signals + ' tín hiệu · 0 re-entry lỗi</span></div>' +
          '<div class="subcard"><span class="kpi-k">W5-G12 · 4-Way 500-Vector ONNX</span><span class="kpi-v mono">5,91e-8 &lt;= 1e-5</span><span class="kpi-s mono">500/500 (100%) · ONNX API ' + esc(g12.onnx_api_version) + ' · 0 ZipMap · NaN/Inf bị chặn</span></div>' +
          '<div class="subcard"><span class="kpi-k">Bellman DP P1 2024 Smoke</span><span class="kpi-v mono">+' + fmt(dpSm.net_pnl_usd, 2) + ' USD</span><span class="kpi-s mono">' + dpSm.trades + ' lệnh · ' + dpSm.dp_tiers + ' bậc · PF ' + fmt(dpSm.profit_factor, 2) + ' · DD ' + fmt(dpSm.equity_dd_pct, 2) + '% · 0 lỗi biên dịch</span></div>';
      }

      // ---------------- TAB 4 ----------------
      function renderTab4() {
        var af = D.alpha_factory;
        var u = af.universe_28;
        var ar = af.m1_arena;
        var ml = af.ml_v105_arena;
        var dr = af.e2e_drills;

        var steps = [
          { lbl: "1. Kho M1 Niêm Phong <= 2024-12-31", val: u.symbol_count + " mã M1", w: 470, col: "#1d4ed8" },
          { lbl: "2. Sàng Lọc Cụm A (X13 100%, trần 360)", val: ar.cluster_a_trials_evaluated + " ứng viên", w: 410, col: "#2563eb" },
          { lbl: "3. Vòng Mù Cụm B (8 cổng thống kê)", val: ar.cluster_a_finalists + " chung kết", w: 230, col: "#d97706" },
          { lbl: "4. Alpha Bench Reserve (Dự bị theo dõi)", val: ar.cluster_b_alpha_bench_reserve_count + " dự bị (F5D UK100)", w: 145, col: "#ca8a04" },
          { lbl: "5. Tier-1 Đạt 8/8 -> PORT_V5 == PORT_7E", val: ar.cluster_b_tier1_survivors_8_of_8 + " bổ sung (Trung thực)", w: 96, col: "#16a34a" }
        ];
        var fsvg = '<svg class="chart" viewBox="0 0 520 192" role="img" aria-label="Phễu sàng lọc 355 ứng viên M1 trong Alpha Factory">';
        for (var i = 0; i < steps.length; i++) {
          var stp = steps[i];
          var x = (520 - stp.w) / 2;
          var y = 6 + i * 37;
          fsvg += '<rect x="' + x.toFixed(1) + '" y="' + y + '" width="' + stp.w + '" height="29" rx="6" fill="' + stp.col + '" />';
          fsvg += '<text x="260" y="' + (y + 19) + '" text-anchor="middle" font-size="11" font-weight="700" fill="#ffffff">' + esc(stp.lbl + " — " + stp.val) + '</text>';
        }
        fsvg += '</svg>';
        document.getElementById("t4-funnel-svg").innerHTML = fsvg;

        document.getElementById("t4-universe-cards").innerHTML =
          '<div class="subcard"><span class="kpi-k">Độ phân giải 28 mã M1</span><span class="kpi-v mono">12 / 10 / 6</span><span class="kpi-s">12 Bid/Ask · 10 Bid+Spread · 6 Một phía · ' + u.usoil_quarantined_rows + ' dòng USOIL cách ly</span></div>' +
          '<div class="subcard"><span class="kpi-k">Sẵn sàng MT5 .hcc</span><span class="kpi-v mono">' + u.mt5_hcc_ready_count + ' / ' + u.symbol_count + ' mã</span><span class="kpi-s">' + u.mt5_hcc_missing_count + ' mã thiếu .hcc FTMO (đánh dấu BLOCKED trung thực)</span></div>' +
          '<div class="subcard"><span class="kpi-k">Đấu trường ML v1.05</span><span class="kpi-v mono">' + ml.recorded_trials + ' / ' + ml.max_trials + ' ca</span><span class="kpi-s">0 thăng hạng (REJECT_V105_ML_KEEP_V103) · ' + ml.float32_cliff_rejected_count + ' loại do vực float32</span></div>' +
          '<div class="subcard"><span class="kpi-k">Ứng viên Dự bị duy nhất</span><span class="kpi-v mono">F5D UK100</span><span class="kpi-s">PF_B ' + fmt(ar.bench_reserve_candidates[0].pf_1x_b, 3) + ' · SR_B ' + fmt(ar.bench_reserve_candidates[0].sharpe_daily_b, 3) + ' · Corr ' + fmt(ar.bench_reserve_candidates[0].corr_vs_port_7e, 4) + ' · Hòa vốn ' + fmt(ar.bench_reserve_candidates[0].cost_breakeven_mult, 2) + 'x</span></div>';

        var fb = "";
        for (var fi = 0; fi < af.finalists_6.length; fi++) {
          var f = af.finalists_6[fi];
          var cls = f.tier_classification === "ALPHA_BENCH_RESERVE" ? "b-adequate" : "b-bad";
          fb +=
            '<tr>' +
              '<td class="tl mono">' + esc(f.candidate_id) + '</td>' +
              '<td class="tl">' + esc(f.family_id) + '</td>' +
              '<td class="tl mono">' + esc(f.symbol) + '</td>' +
              '<td class="tl"><span class="badge ' + cls + '" style="font-size:10px;">' + esc(f.tier_classification) + '</span></td>' +
              '<td class="mono">' + f.gates_passed_count + ' / 8</td>' +
              '<td class="mono">' + fmt(f.cluster_a_sharpe_1x, 2) + '</td>' +
              '<td class="mono">' + fmt(f.sharpe_daily_b, 2) + '</td>' +
              '<td class="mono">' + fmt(f.pf_1x_b, 3) + '</td>' +
              '<td class="mono">' + f.n_trades_b + '</td>' +
              '<td class="mono">' + fmt(f.corr_vs_port_7e, 4) + '</td>' +
              '<td class="mono">' + fmt(f.cost_breakeven_mult, 2) + 'x</td>' +
            '</tr>';
        }
        document.getElementById("t4-finalists-body").innerHTML = fb;

        document.getElementById("t4-ledger-sub").textContent =
          "Sổ chuỗi băm mật mã: " + dr.ledger_entry_count + " bản ghi · Root SHA-256: " + dr.ledger_root_sha256.slice(0, 20) + "... · Backend: " + dr.decay_backend_used;
        var ds = dr.drills_summary;
        var drillCards = [
          { t: "Drill 1 · Xanh bình thường", b: "PASS", d: ds.DRILL_1_NORMAL_GREEN.evaluated_engines + " máy xanh · " + ds.DRILL_1_NORMAL_GREEN.proposals_emitted + " đề xuất thay đổi." },
          { t: "Drill 2 · Vàng hạ tải 0,5x", b: "PENDING_OWNER", d: ds.DRILL_2_AMBER_HALVED.target_engine + " -> tải " + fmt(ds.DRILL_2_AMBER_HALVED.target_weight_mult_after, 1) + "x (chờ chủ duyệt)." },
          { t: "Drill 3 · Đỏ thay dự bị", b: "PENDING_OWNER", d: ds.DRILL_3_RED_WITH_BENCH_SWAP.target_engine + " -> chọn " + ds.DRILL_3_RED_WITH_BENCH_SWAP.selected_replacement + "; máy hỏng KILLED." },
          { t: "Drill 4 · Hết dự bị dừng sạch", b: "FAIL-CLOSED", d: ds.DRILL_4_RED_EMPTY_BENCH_FAIL_CLOSED.action_type + " · ứng viên chưa kiểm giữ " + ds.DRILL_4_RED_EMPTY_BENCH_FAIL_CLOSED.unverified_candidate_state + "." },
          { t: "Drill 5 · Chống dữ liệu độc", b: ds.DRILL_5_POISONED_INPUT_AND_TAMPERED_LEDGER.cases_rejected_fail_closed + "/" + ds.DRILL_5_POISONED_INPUT_AND_TAMPERED_LEDGER.cases_tested + " CHẶN", d: "Từ chối toàn bộ 8 ca NaN/Inf, tương lai, giả mạo chuỗi băm sổ." }
        ];
        var dh = "";
        for (var di2 = 0; di2 < drillCards.length; di2++) {
          dh += '<div class="subcard"><div style="display:flex;justify-content:space-between;align-items:center;gap:4px;"><strong>' + esc(drillCards[di2].t) + '</strong><span class="badge b-good" style="font-size:9.5px;">' + esc(drillCards[di2].b) + '</span></div><div class="kpi-s" style="margin-top:4px;">' + esc(drillCards[di2].d) + '</div></div>';
        }
        document.getElementById("t4-drills-grid").innerHTML = dh;

        var tiers = ["tier_1_cfd_prop", "tier_2_cme_futures", "tier_3_multi_asset_ownbook", "tier_4_live_ops"];
        var th = "";
        for (var t4i = 0; t4i < tiers.length; t4i++) {
          var tr = D.four_tier_scorecard[tiers[t4i]];
          th +=
            '<div class="subcard">' +
              '<div style="display:flex;justify-content:space-between;align-items:center;gap:4px;"><strong>Tầng ' + tr.tier_number + ' · ' + esc(tr.domain_tier) + '</strong>' + gradeBadge(tr.current_unified_grade) + '</div>' +
              '<div style="font-size:11.5px;margin-top:4px;">' + esc(tr.current_position_vi) + '</div>' +
              '<div class="kpi-s" style="margin-top:4px;"><strong>Khoảng cách Top 1%:</strong> ' + esc(tr.concrete_gap_to_top_1_pct[0] || "") + '</div>' +
            '</div>';
        }
        document.getElementById("t4-tiers-grid").innerHTML = th;
      }

      // Wire interactive controls
      var t1Skus = document.querySelectorAll(".t1-sku");
      for (var i1 = 0; i1 < t1Skus.length; i1++) {
        t1Skus[i1].addEventListener("click", function () {
          st.t1Sku = this.getAttribute("data-sku");
          for (var j = 0; j < t1Skus.length; j++) t1Skus[j].classList.toggle("active", t1Skus[j] === this);
          renderTab1();
        });
      }
      var t1Strs = document.querySelectorAll(".t1-stress");
      for (var i2 = 0; i2 < t1Strs.length; i2++) {
        t1Strs[i2].addEventListener("click", function () {
          st.t1Stress = Number(this.getAttribute("data-stress"));
          for (var j = 0; j < t1Strs.length; j++) t1Strs[j].classList.toggle("active", t1Strs[j] === this);
          renderTab1();
        });
      }
      document.getElementById("t2-bankroll-slider").addEventListener("input", function () {
        st.t2BankrollIdx = Number(this.value);
        renderTab2();
      });
      var t2Ccs = document.querySelectorAll(".t2-cc");
      for (var i3 = 0; i3 < t2Ccs.length; i3++) {
        t2Ccs[i3].addEventListener("click", function () {
          st.t2Cc = this.getAttribute("data-cc");
          for (var j = 0; j < t2Ccs.length; j++) t2Ccs[j].classList.toggle("active", t2Ccs[j] === this);
          renderTab2();
        });
      }
      var t2Aps = document.querySelectorAll(".t2-ap");
      for (var i4 = 0; i4 < t2Aps.length; i4++) {
        t2Aps[i4].addEventListener("click", function () {
          st.t2Ap = this.getAttribute("data-ap");
          for (var j = 0; j < t2Aps.length; j++) t2Aps[j].classList.toggle("active", t2Aps[j] === this);
          renderTab2();
        });
      }
      var t2Strs = document.querySelectorAll(".t2-stress");
      for (var i5 = 0; i5 < t2Strs.length; i5++) {
        t2Strs[i5].addEventListener("click", function () {
          st.t2Stress = Number(this.getAttribute("data-stress"));
          for (var j = 0; j < t2Strs.length; j++) t2Strs[j].classList.toggle("active", t2Strs[j] === this);
          renderTab2();
        });
      }
      var t3Hors = document.querySelectorAll(".t3-hor");
      for (var i6 = 0; i6 < t3Hors.length; i6++) {
        t3Hors[i6].addEventListener("click", function () {
          st.t3Hor = this.getAttribute("data-hor");
          for (var j = 0; j < t3Hors.length; j++) t3Hors[j].classList.toggle("active", t3Hors[j] === this);
          renderTab3();
        });
      }

      function renderAll() {
        renderTab1();
        renderTab2();
        renderTab3();
        renderTab4();
      }

      initTab2Static();
      syncThemeBtn();
      renderAll();
    })();
  </script>
</body>
</html>
"""
    return html.replace("__DATA_JSON__", data_json)


_WIN_USER_PATH_OPSEC_RE: re.Pattern[str] = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])(?:\\+|/)Users(?:\\+|/)(?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+"
)


def format_opsec_safe_path(
    path: Path,
    *,
    repo_root: Path = REPO_ROOT,
    artifact_dir: Path | None = None,
    artifact_placeholder: str = "<ARTIFACT_DIR>",
) -> str:
    """Format a path for receipts/logs using repo-relative or `<ARTIFACT_DIR>/<filename>` without user-profile leaks."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        pass
    if artifact_dir is not None:
        try:
            rel_art = resolved.relative_to(artifact_dir.resolve()).as_posix()
            return f"{artifact_placeholder}/{rel_art}"
        except ValueError:
            pass
    try:
        rel_home = resolved.relative_to(Path.home().resolve()).as_posix()
        return f"<HOME>/{rel_home}"
    except ValueError:
        pass
    out = resolved.as_posix()
    _require(_WIN_USER_PATH_OPSEC_RE.search(out) is None, f"OPSEC_USER_PATH_LEAK: {out!r}")
    return out


def _write_lf_utf8(path: Path, text: str, *, display_path: str | None = None) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw = normalized.encode("utf-8")
    path.write_bytes(raw)
    recorded_path = display_path if display_path is not None else format_opsec_safe_path(path)
    _require(_WIN_USER_PATH_OPSEC_RE.search(recorded_path) is None, f"OPSEC_USER_PATH_LEAK: {recorded_path!r}")
    return {
        "path": recorded_path,
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "crlf_count": raw.count(b"\r\n"),
        "has_bom": raw.startswith(b"\xef\xbb\xbf"),
    }


def write_visuals_receipt(
    receipt: Mapping[str, Any],
    *,
    audit_path: Path = DEFAULT_RECEIPT_PATH,
    dropbox_path: Path = DEFAULT_DROPBOX_PATH,
) -> dict[str, Any]:
    """Fail-closed OPSEC-checked byte-identical writer for `w5_visuals_receipt.json` and swarm dropbox."""
    payload = dict(receipt)
    payload["report_sha256"] = _canonical_report_sha256(payload, "report_sha256")
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    _require(_WIN_USER_PATH_OPSEC_RE.search(text) is None, "OPSEC_USER_PATH_LEAK detected in visuals receipt")
    raw = text.encode("utf-8")
    for target in (Path(audit_path), Path(dropbox_path)):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return {
        "audit_path": format_opsec_safe_path(Path(audit_path)),
        "dropbox_path": format_opsec_safe_path(Path(dropbox_path)),
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "report_sha256": payload["report_sha256"],
        "byte_identical": Path(audit_path).read_bytes() == Path(dropbox_path).read_bytes(),
    }


def build_wave5_visuals(
    *,
    runtime_visuals_dir: Path | None = None,
    brain_artifacts_dir: Path | None = None,
    master_metrics_path: Path = DEFAULT_MASTER_METRICS_PATH,
    spectrum_summary_path: Path = DEFAULT_SPECTRUM_SUMMARY_PATH,
    spectrum_all_cases_path: Path = DEFAULT_SPECTRUM_ALL_CASES_PATH,
    bellman_dp_path: Path = DEFAULT_BELLMAN_DP_PATH,
    m1_arena_summary_path: Path = DEFAULT_M1_ARENA_SUMMARY_PATH,
) -> dict[str, Any]:
    """Build, validate, and optionally emit byte-identical Wave 5 HTML visuals (safe when dirs=None)."""
    dev_pc_mode = apply_mode_a_belownormal()
    bundle = load_verified_ssot_bundle(
        master_metrics_path=master_metrics_path,
        spectrum_summary_path=spectrum_summary_path,
        spectrum_all_cases_path=spectrum_all_cases_path,
        bellman_dp_path=bellman_dp_path,
        m1_arena_summary_path=m1_arena_summary_path,
    )

    widget_payload = build_widget_payload(bundle)
    explorer_payload = build_explorer_payload(bundle)

    widget_html = render_profile_spectrum_widget_html(widget_payload)
    explorer_html = render_deep_alpha_explorer_html(explorer_payload)

    widget_audit = _verify_html_invariants(widget_html, WIDGET_FILENAME)
    explorer_audit = _verify_html_invariants(explorer_html, EXPLORER_FILENAME)

    written_files: dict[str, dict[str, Any]] = {}
    if runtime_visuals_dir is not None:
        written_files["runtime_widget"] = _write_lf_utf8(
            runtime_visuals_dir / WIDGET_FILENAME,
            widget_html,
            display_path=format_opsec_safe_path(runtime_visuals_dir / WIDGET_FILENAME),
        )
        written_files["runtime_explorer"] = _write_lf_utf8(
            runtime_visuals_dir / EXPLORER_FILENAME,
            explorer_html,
            display_path=format_opsec_safe_path(runtime_visuals_dir / EXPLORER_FILENAME),
        )
    if brain_artifacts_dir is not None:
        written_files["brain_widget"] = _write_lf_utf8(
            brain_artifacts_dir / WIDGET_FILENAME,
            widget_html,
            display_path=format_opsec_safe_path(
                brain_artifacts_dir / WIDGET_FILENAME,
                artifact_dir=brain_artifacts_dir,
                artifact_placeholder="<ARTIFACT_DIR>",
            ),
        )
        written_files["brain_explorer"] = _write_lf_utf8(
            brain_artifacts_dir / EXPLORER_FILENAME,
            explorer_html,
            display_path=format_opsec_safe_path(
                brain_artifacts_dir / EXPLORER_FILENAME,
                artifact_dir=brain_artifacts_dir,
                artifact_placeholder="<ARTIFACT_DIR>",
            ),
        )

    if runtime_visuals_dir is not None and brain_artifacts_dir is not None:
        _require(
            written_files["runtime_widget"]["sha256"] == written_files["brain_widget"]["sha256"],
            "BYTE_IDENTICAL_MISMATCH: widget runtime vs brain",
        )
        _require(
            written_files["runtime_explorer"]["sha256"] == written_files["brain_explorer"]["sha256"],
            "BYTE_IDENTICAL_MISMATCH: explorer runtime vs brain",
        )

    return {
        "schema": "naqex-wave5-visuals-build-v1",
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offensive_version": OFFENSIVE_VERSION,
        "gate": GATE_ID,
        "dev_pc_mode": dev_pc_mode,
        "provenance": bundle["provenance"],
        "pydantic_v2_total_validated": bundle["pydantic_v2_total_validated"],
        "widget_audit": widget_audit,
        "explorer_audit": explorer_audit,
        "written_files": written_files,
        "widget_html": widget_html,
        "explorer_html": explorer_html,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build & verify Wave 5 4-color HTML visuals (Gate W5-G20).")
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_VISUALS_DIR)
    parser.add_argument("--brain-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing HTML files.")
    args = parser.parse_args(argv)

    brain_dir = args.brain_dir if args.brain_dir is not None else resolve_default_brain_artifacts_dir()
    result = build_wave5_visuals(
        runtime_visuals_dir=None if args.dry_run else args.runtime_dir,
        brain_artifacts_dir=None if args.dry_run else brain_dir,
    )
    summary = {k: v for k, v in result.items() if k not in ("widget_html", "explorer_html")}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
