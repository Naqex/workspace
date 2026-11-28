"""Verification & negative-mutation tests for Wave 5 HTML visuals (Gate W5-G20).

Hard invariants:
  - Uses `tmp_path` so pytest NEVER mutates production `.runtime/offensive5/visuals/*.html`
    or `brain/36cdea52-.../*.html`.
  - ZERO bare Python `assert` statements (`python -O` safe).
  - Validates embedded JSON payloads strictly via Pydantic v2 `EvaluationScorecard`
    (zero `jsonschema` runtime dependency).
  - Verifies zero external CDNs, zero bare dollar symbols, zero G12 prop-firm support nudges,
    zero CRLF, zero BOM, `data-theme="dark"|"light"` support, and verbatim SSOT metric parity.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.wave5 import build_wave5_visuals as bwv  # noqa: E402
from quant_factory.wave5.evaluation_catalog import (  # noqa: E402
    LEGACY_UNINSTRUMENTED_LABEL_VI,
    EvaluationScorecard,
)


def _check(cond: bool, msg: str) -> None:
    """Explicit check immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_embedded_json(html: str) -> dict[str, Any]:
    m = bwv.SCRIPT_DATA_RE.search(html)
    _check(m is not None, "missing <script id='w5-ssot-data' type='application/json'>")
    return json.loads(m.group(1))


def _make_minimal_valid_html() -> str:
    _, tax_sha = bwv.load_evaluation_taxonomy()
    sc = bwv.grade_evaluation_record(
        bwv.EvaluationInputRecord(
            record_id="unit_test_record",
            domain_tier="T1_CFD_PROP",
            eval_scope="SINGLE_TICKET",
            pricing_regime="ALL_REGULAR_SSOT",
            evidence_stage="DEV_CONSUMED_OOS",
            data_resolution="APPROX_DAILY",
            execution_status="MEASURED_DEMO_EXECUTION",
            ev_per_fee=5.5,
            funded_12m_blowup_pct=0.3,
            p_le_zero_24m_pct=25.0,
            payout_1_cal_days=220.0,
            p1_pass_rate_pct=80.0,
            p1_fail_rate_pct=15.0,
            p1_pending_rate_pct=5.0,
            p2_pass_rate_pct=85.0,
            p2_fail_rate_pct=10.0,
            p2_pending_rate_pct=5.0,
            pass_eval_12m_pct=68.0,
            holdout_rows_analysed=0,
            order_send_count=0,
        )
    )
    sc_dict = sc.model_dump(mode="json")
    sc_dict["taxonomy_sha256"] = tax_sha
    scorecards = {f"sc_{i}": sc_dict for i in range(9)}
    payload = {
        "ssot_meta": {
            "holdout_cutoff_date": "2024-12-31",
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "execution_capability": False,
            "spend_vnd": 0,
        },
        "scorecards": scorecards,
    }
    return (
        '<!DOCTYPE html><html lang="vi"><body>'
        f'<script id="w5-ssot-data" type="application/json">{bwv._safe_embed_json(payload)}</script>'
        "</body></html>\n"
    )


# ---------------------------------------------------------------------------
# 1. Offline Unit & Negative-Mutation Tests (CI-safe without local .runtime)
# ---------------------------------------------------------------------------


def test_zero_bare_asserts_in_visuals_module_and_tests() -> None:
    targets = [
        Path(bwv.__file__).resolve(),
        Path(__file__).resolve(),
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(not asserts, f"bare assert forbidden in {path.name}: lines {asserts}")
        opsec_hit = bwv._WIN_USER_PATH_OPSEC_RE.search(text)
        _check(opsec_hit is None, f"hardcoded user profile path forbidden in {path.name}: {opsec_hit}")


def test_dynamic_brain_dir_resolution_and_opsec_safe_receipt_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom_dir = tmp_path / "custom_brain"
    monkeypatch.setenv("NAQEX_ARTIFACTS_DIR", str(custom_dir))
    _check(
        bwv.resolve_default_brain_artifacts_dir() == custom_dir,
        "NAQEX_ARTIFACTS_DIR env override must resolve dynamically",
    )
    monkeypatch.delenv("NAQEX_ARTIFACTS_DIR", raising=False)
    fallback = bwv.resolve_default_brain_artifacts_dir()
    _check(
        fallback == Path.home() / ".gemini" / "antigravity" / "brain" / bwv.DEFAULT_CONVERSATION_ARTIFACT_ID,
        f"unexpected dynamic fallback dir: {fallback}",
    )
    safe_brain = bwv.format_opsec_safe_path(
        custom_dir / bwv.WIDGET_FILENAME,
        artifact_dir=custom_dir,
        artifact_placeholder="<ARTIFACT_DIR>",
    )
    _check(
        safe_brain == f"<ARTIFACT_DIR>/{bwv.WIDGET_FILENAME}",
        f"expected <ARTIFACT_DIR> placeholder path, got {safe_brain!r}",
    )
    _check(bwv._WIN_USER_PATH_OPSEC_RE.search(safe_brain) is None, "OPSEC leak in formatted artifact path")

    # write_visuals_receipt must fail closed on hardcoded user profile paths
    bad_receipt = {"deliverables": {"bad": {"brain_path": "C:" + "\\Users\\" + "Alice\\x.html"}}}
    with pytest.raises(bwv.VisualBuildError, match="OPSEC_USER_PATH_LEAK"):
        bwv.write_visuals_receipt(
            bad_receipt,
            audit_path=tmp_path / "audit.json",
            dropbox_path=tmp_path / "dropbox.json",
        )
    good_receipt = {"deliverables": {"ok": {"brain_path": f"<ARTIFACT_DIR>/{bwv.WIDGET_FILENAME}"}}}
    wr = bwv.write_visuals_receipt(
        good_receipt,
        audit_path=tmp_path / "audit_ok.json",
        dropbox_path=tmp_path / "dropbox_ok.json",
    )
    _check(wr["byte_identical"] is True, "visuals receipt copies must be byte-identical")


def test_mode_a_belownormal_policy_metadata() -> None:
    info = bwv.apply_mode_a_belownormal()
    _check(info["policy_mode"] == "MODE_A_OWNER_ACTIVE", f"unexpected mode: {info}")
    _check(info["priority_class_hex"] == "0x4000", f"unexpected priority: {info}")
    _check(info["gpu_budget_pct"] == 0, f"gpu_budget_pct must be 0: {info}")


def test_negative_mutations_fail_closed_on_html_invariants() -> None:
    clean_html = _make_minimal_valid_html()
    ok = bwv._verify_html_invariants(clean_html, "clean_unit")
    _check(ok["bare_dollar_count"] == 0, "clean html should have 0 bare dollar")
    _check(ok["embedded_scorecards_validated"] == 9, "expected 9 validated scorecards")

    # 1. Reject UTF-8 BOM
    with pytest.raises(bwv.VisualBuildError, match="BOM"):
        bwv._verify_html_invariants("\ufeff" + clean_html, "bom_case")

    # 2. Reject CRLF
    with pytest.raises(bwv.VisualBuildError, match="CRLF"):
        bwv._verify_html_invariants(clean_html.replace("\n", "\r\n"), "crlf_case")

    # 3. Reject bare dollar sign
    with pytest.raises(bwv.VisualBuildError, match="dollar"):
        bwv._verify_html_invariants(clean_html.replace("<body>", "<body>$100"), "dollar_case")

    # 4. Reject external CDN script/link
    with pytest.raises(bwv.VisualBuildError, match="CDN"):
        bwv._verify_html_invariants(
            clean_html.replace("<body>", '<body><script src="https://cdn.example.com/x.js"></script>'),
            "cdn_case",
        )

    # 5. Reject G12 prop-firm support nudge
    with pytest.raises(bwv.VisualBuildError, match="G12"):
        bwv._verify_html_invariants(
            clean_html.replace("<body>", "<body>Hãy email FTMO support để hỏi luật"),
            "g12_case",
        )

    # 6. Reject holdout violation inside embedded EvaluationScorecard (Pydantic v2)
    bad_payload = _extract_embedded_json(clean_html)
    mutated = copy.deepcopy(bad_payload)
    mutated["scorecards"]["sc_0"]["holdout_rows_analysed"] = 1
    bad_html = (
        '<!DOCTYPE html><html lang="vi"><body>'
        f'<script id="w5-ssot-data" type="application/json">{bwv._safe_embed_json(mutated)}</script>'
        "</body></html>\n"
    )
    with pytest.raises(ValidationError):
        bwv._verify_html_invariants(bad_html, "holdout_violation")

    # 7. Reject OrderSend violation inside embedded EvaluationScorecard (Pydantic v2)
    mutated2 = copy.deepcopy(bad_payload)
    mutated2["scorecards"]["sc_0"]["order_send_count"] = 1
    bad_html2 = (
        '<!DOCTYPE html><html lang="vi"><body>'
        f'<script id="w5-ssot-data" type="application/json">{bwv._safe_embed_json(mutated2)}</script>'
        "</body></html>\n"
    )
    with pytest.raises(ValidationError):
        bwv._verify_html_invariants(bad_html2, "ordersend_violation")


# ---------------------------------------------------------------------------
# 2. Full SSOT Build, Pydantic Validation & Production Parity (tmp_path only)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_build_wave5_visuals_in_tmp_path_and_verify_production_parity(tmp_path: Path) -> None:
    prod_runtime_widget = bwv.DEFAULT_RUNTIME_VISUALS_DIR / bwv.WIDGET_FILENAME
    prod_runtime_explorer = bwv.DEFAULT_RUNTIME_VISUALS_DIR / bwv.EXPLORER_FILENAME
    prod_brain_widget = bwv.DEFAULT_BRAIN_ARTIFACTS_DIR / bwv.WIDGET_FILENAME
    prod_brain_explorer = bwv.DEFAULT_BRAIN_ARTIFACTS_DIR / bwv.EXPLORER_FILENAME

    pre_hashes = {
        str(p): _sha256_file(p)
        for p in (prod_runtime_widget, prod_runtime_explorer, prod_brain_widget, prod_brain_explorer)
        if p.is_file()
    }

    out_runtime = tmp_path / "runtime_visuals"
    out_brain = tmp_path / "brain_visuals"
    res = bwv.build_wave5_visuals(
        runtime_visuals_dir=out_runtime,
        brain_artifacts_dir=out_brain,
    )

    _check(
        res["pydantic_v2_total_validated"] == 1072,
        f"expected 1072 scorecards, got {res['pydantic_v2_total_validated']}",
    )
    _check(res["widget_audit"]["bare_dollar_count"] == 0, "widget must have 0 bare dollar")
    _check(res["explorer_audit"]["bare_dollar_count"] == 0, "explorer must have 0 bare dollar")
    _check(res["widget_audit"]["external_cdn_count"] == 0, "widget must have 0 external CDNs")
    _check(res["explorer_audit"]["external_cdn_count"] == 0, "explorer must have 0 external CDNs")
    _check(res["widget_audit"]["g12_nudge_count"] == 0, "widget must have 0 G12 nudges")
    _check(res["explorer_audit"]["g12_nudge_count"] == 0, "explorer must have 0 G12 nudges")
    _check(res["widget_audit"]["crlf_count"] == 0 and not res["widget_audit"]["has_bom"], "widget LF/no-BOM fail")
    _check(res["explorer_audit"]["crlf_count"] == 0 and not res["explorer_audit"]["has_bom"], "explorer LF/no-BOM fail")

    # Byte-identical inside tmp_path & OPSEC-safe recorded paths
    _check(
        res["written_files"]["brain_widget"]["path"] == f"<ARTIFACT_DIR>/{bwv.WIDGET_FILENAME}",
        f"brain_widget path must use <ARTIFACT_DIR> placeholder: {res['written_files']['brain_widget']}",
    )
    _check(
        res["written_files"]["brain_explorer"]["path"] == f"<ARTIFACT_DIR>/{bwv.EXPLORER_FILENAME}",
        f"brain_explorer path must use <ARTIFACT_DIR> placeholder: {res['written_files']['brain_explorer']}",
    )
    for wf_key, wf_meta in res["written_files"].items():
        _check(
            bwv._WIN_USER_PATH_OPSEC_RE.search(wf_meta["path"]) is None,
            f"OPSEC leak in written_files[{wf_key}]: {wf_meta['path']!r}",
        )
    _check(
        _sha256_file(out_runtime / bwv.WIDGET_FILENAME) == _sha256_file(out_brain / bwv.WIDGET_FILENAME),
        "tmp widget copies must be byte-identical",
    )
    _check(
        _sha256_file(out_runtime / bwv.EXPLORER_FILENAME) == _sha256_file(out_brain / bwv.EXPLORER_FILENAME),
        "tmp explorer copies must be byte-identical",
    )

    # Inline widget CSS constraints: no h-screen/100vh, has data-theme & prefers-color-scheme
    w_html = res["widget_html"]
    _check("100vh" not in w_html and "h-screen" not in w_html, "inline widget must never use 100vh or h-screen")
    _check("prefers-color-scheme: dark" in w_html, "widget must keep prefers-color-scheme: dark default")
    _check('data-theme="dark"' in w_html and 'data-theme="light"' in w_html, "widget must support manual data-theme")
    _check("var(--foreground" in w_html and "var(--card" in w_html, "widget must respect host CSS variables")

    e_html = res["explorer_html"]
    _check("prefers-color-scheme: dark" in e_html, "explorer must keep prefers-color-scheme: dark default")
    _check('data-theme="dark"' in e_html and 'data-theme="light"' in e_html, "explorer must support manual data-theme")

    # Validate embedded JSON payloads against SSOT & Pydantic v2
    master = json.loads(bwv.DEFAULT_MASTER_METRICS_PATH.read_text(encoding="utf-8"))
    summary = json.loads(bwv.DEFAULT_SPECTRUM_SUMMARY_PATH.read_text(encoding="utf-8"))
    w_data = _extract_embedded_json(w_html)
    e_data = _extract_embedded_json(e_html)

    _check(len(w_data["cases"]) == 90, f"expected 90 single-ticket cases, got {len(w_data['cases'])}")
    _check(len(e_data["single_cases"]) == 90, f"expected 90 explorer single cases, got {len(e_data['single_cases'])}")
    _check(len(e_data["fleet_cases"]) == 972, f"expected 972 fleet cases, got {len(e_data['fleet_cases'])}")

    # Verify verbatim T3_BALANCED_EV 100K 1.0x against wave5_master_metrics.json
    t3_master = master["four_tier_inside_out_scorecard"]["tier_1_cfd_prop"]["wave5_reconciled_metrics"][
        "single_ticket_t3_balanced_100k_1x"
    ]
    t3_widget = next(
        c
        for c in w_data["cases"]
        if c["cohort"] == "CORE_PORT_7E"
        and c["schedule_id"] == "T3_BALANCED_EV"
        and c["contract_id"] == "ftmo_standard_100k"
        and math.isclose(c["friction_mult"], 1.0)
    )
    _check(math.isclose(t3_widget["p1"]["pass_12m"], t3_master["p1_pass_12m_pct"]), "T3 P1 mismatch")
    _check(math.isclose(t3_widget["p2"]["pass_12m"], t3_master["p2_pass_12m_pct"]), "T3 P2 mismatch")
    _check(math.isclose(t3_widget["pass_eval"]["pass_12m"], t3_master["pass_eval_12m_pct"]), "T3 PassEval mismatch")
    _check(math.isclose(t3_widget["funded"]["blowup_12m"], t3_master["fn12_blowup_pct"]), "T3 Fn12 blowup mismatch")
    _check(math.isclose(t3_widget["funded"]["ev_per_fee"], t3_master["ev_per_fee_npv24"]), "T3 EV/fee mismatch")
    _check(
        math.isclose(t3_widget["funded"]["uncond_pay1"], t3_master["uncond_med_pay1_cap730"]),
        "T3 uncond Pay1 mismatch",
    )

    # Verify T5 mandatory warning tags & intraday drift verbatim against mc_spectrum_summary.json
    t5_widget = next(
        c
        for c in w_data["cases"]
        if c["cohort"] == "CORE_PORT_7E"
        and c["schedule_id"] == "T5_MAX_THROTTLE_YOLO"
        and c["contract_id"] == "ftmo_standard_100k"
        and math.isclose(c["friction_mult"], 1.0)
    )
    _check("RESEARCH_BOUNDARY_ONLY" in t5_widget["mandatory_tags"], "T5 missing RESEARCH_BOUNDARY_ONLY")
    _check("FTMO_GAMBLING_ALLIN_RISK" in t5_widget["mandatory_tags"], "T5 missing FTMO_GAMBLING_ALLIN_RISK")
    t5_audit_summary = next(
        r
        for r in summary["intraday_trade_dd_audit"]
        if r["schedule_id"] == "T5_MAX_THROTTLE_YOLO" and r["contract_id"] == "ftmo_standard_100k"
    )
    _check(
        math.isclose(
            w_data["intraday_audit"]["T5_MAX_THROTTLE_YOLO__ftmo_standard_100k"]["drift_trade_minus_daily_close_pp"],
            t5_audit_summary["drift_trade_minus_daily_close_pp"],
        ),
        "T5 intraday drift mismatch",
    )

    # Verify canonical Wave 4 legacy UNKNOWN_LEGACY_UNINSTRUMENTED scorecard in explorer
    w4_sc = EvaluationScorecard.model_validate(e_data["scorecards"]["w4_legacy_c10_fleet_1_0x_reference"])
    _check(w4_sc.legacy_grade_code == "TOT", "Wave 4 legacy_grade_code must be TOT")
    _check(w4_sc.unified_grade_code == "ADEQUATE", "Wave 4 unified_grade_code must be ADEQUATE")
    _check(w4_sc.phase_grades["p1"].grade == "UNKNOWN_LEGACY_UNINSTRUMENTED", "Wave 4 P1 must be UNKNOWN")
    _check(w4_sc.phase_grades["p2"].grade == "UNKNOWN_LEGACY_UNINSTRUMENTED", "Wave 4 P2 must be UNKNOWN")
    _check(
        w4_sc.phase_grades["p1"].presentation_state.label == LEGACY_UNINSTRUMENTED_LABEL_VI,
        "Wave 4 P1 label must match canonical LEGACY_UNINSTRUMENTED_LABEL_VI",
    )

    # Verify Alpha Factory & MT5 Build 6230 verbatim claims in explorer
    _check(e_data["alpha_factory"]["m1_arena"]["cluster_a_trials_evaluated"] == 355, "M1 trials != 355")
    _check(e_data["alpha_factory"]["m1_arena"]["port_v5_equals_port_7e"] is True, "PORT_V5 != PORT_7E")
    _check(e_data["alpha_factory"]["e2e_drills"]["auto_deploy_permitted"] is False, "auto_deploy must be false")
    _check(e_data["alpha_factory"]["e2e_drills"]["drills_passed"] == 5, "drills_passed != 5")
    _check(e_data["mt5_proof"]["w5_g10_live_feature_parity_2024"]["matched_signals_total"] == 777, "MT5 matched != 777")
    _check(e_data["mt5_proof"]["w5_g15_modular_7e_compat"]["delta_net_pnl_usd"] == 0.0, "MT5 G15 delta != 0.0")

    # Verify 100.0% partitions on ALL 90 single-ticket cases & ALL 972 fleet cases
    for c in w_data["cases"]:
        for key in ("p1", "p2", "pass_eval", "funded"):
            tot = c[key]["pass_12m"] + c[key]["fail_12m"] + c[key]["pend_12m"]
            _check(abs(tot - 100.0) <= 0.05, f"single case {c['record_id']}.{key} sum={tot}")
    for fc in e_data["fleet_cases"]:
        for hk, arr in fc["hz"].items():
            tot = sum(arr)
            _check(abs(tot - 100.0) <= 0.05, f"fleet case {fc['rid']}.{hk} sum={tot}")

    # Verify production HTML files were NOT mutated by pytest AND match tmp build byte-for-byte
    for path_str, pre_sha in pre_hashes.items():
        p = Path(path_str)
        _check(_sha256_file(p) == pre_sha, f"pytest mutated production file: {p}")
    if prod_runtime_widget.is_file() and prod_brain_widget.is_file():
        _check(
            _sha256_file(prod_runtime_widget) == _sha256_file(prod_brain_widget) == res["widget_audit"]["sha256"],
            "production widget files must match deterministic build byte-for-byte",
        )
    if prod_runtime_explorer.is_file() and prod_brain_explorer.is_file():
        _check(
            _sha256_file(prod_runtime_explorer) == _sha256_file(prod_brain_explorer) == res["explorer_audit"]["sha256"],
            "production explorer files must match deterministic build byte-for-byte",
        )
