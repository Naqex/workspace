"""Contract and negative-mutation tests for `evaluation_taxonomy.json` and `evaluation-scorecard@1.0.0`.

Hard invariants verified (ZERO bare asserts, 100% safe under `python -O`, ZERO mutations to `.runtime/`):
  1. `evaluation_taxonomy.json` passes Pydantic v2 validation AND `[ARCH-06]` strict unit-suffix checks.
  2. All 9 continuous half-open metric intervals cover `(-inf, +inf)` with ZERO dead zones and ZERO overlaps.
  3. All required enums, 4 inside-out tiers x 5 phases, pricing regimes, eval scopes, and `blindness_tier_mapping`
     exist while `ftmo_specs_28.json` stays byte-for-byte untouched.
  4. `UI/contracts/evaluation-scorecard/1.0.0/CONTRACT.md` & `schema.json` match the Pydantic v2 export
     and `UI/docs/TRADING-UI-CONTRACT.md` preserves existing M1 rules while linking the candidate contract.
  5. Negative mutation tests reject NaN, Inf, bool-as-number, dead zones, overlaps, invalid 100%-partitions,
     missing `presentation-state@1.0.0` labels/reasonCodes, Holdout/OrderSend violations, and `[ARCH-06]` bugs.
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
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.wave5 import evaluation_catalog as ec  # noqa: E402

from tooling import check_architecture as arch  # noqa: E402

FTMO_SPECS_IMMUTABLE_SHA256 = "f49e8a4a458b6f3c0f67c8f6b67247355576534dcb607d9fbab4803897c348f7"
CONTRACT_MD_PATH = REPO_ROOT / "UI" / "contracts" / "evaluation-scorecard" / "1.0.0" / "CONTRACT.md"
SCHEMA_JSON_PATH = REPO_ROOT / "UI" / "contracts" / "evaluation-scorecard" / "1.0.0" / "schema.json"
TRADING_UI_CONTRACT_PATH = REPO_ROOT / "UI" / "docs" / "TRADING-UI-CONTRACT.md"


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_raw_taxonomy() -> dict[str, Any]:
    return json.loads(ec.DEFAULT_TAXONOMY_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. SSOT Taxonomy, [ARCH-06], Continuous Intervals & Immutables
# ---------------------------------------------------------------------------


class TestEvaluationTaxonomySSOT:
    def test_taxonomy_loads_and_passes_arch_06_strict(self) -> None:
        cfg, sha = ec.load_evaluation_taxonomy()
        _check(len(sha) == 64, "taxonomy sha256 must be 64 hex chars")
        _check(cfg.holdout_rows_analysed == 0, "holdout_rows_analysed must be 0")
        _check(cfg.order_send_count == 0, "order_send_count must be 0")
        _check(cfg.holdout_cutoff_date == "2024-12-31", "holdout_cutoff_date must be 2024-12-31")

        # Verify ARCH-06 strictly passes on the real SSOT directory
        violations = arch.check_arch_06_ssot_unit_suffixes(REPO_ROOT)
        _check(not violations, f"[ARCH-06] violations found: {[v.format_line() for v in violations]}")

        # Verify canonical enums match W5-G03 contract
        _check(
            cfg.grade_bands == ("BAD", "ADEQUATE", "GOOD", "TOP_1_PCT", "UNKNOWN_LEGACY_UNINSTRUMENTED"),
            f"unexpected grade_bands: {cfg.grade_bands}",
        )
        _check(
            cfg.evidence_stages
            == ("DEV_IS", "DEV_BLIND_OOS", "DEV_CONSUMED_OOS", "HOLDOUT_SEALED_ONCE", "SHADOW_DEMO", "LIVE_REAL"),
            f"unexpected evidence_stages: {cfg.evidence_stages}",
        )
        _check(
            cfg.data_resolutions == ("TICK_REAL", "M1_BID_ASK", "M1_BID_SPREAD", "M1_SINGLE_SIDE", "APPROX_DAILY"),
            f"unexpected data_resolutions: {cfg.data_resolutions}",
        )
        _check(
            cfg.pricing_regimes == ("ALL_REGULAR_SSOT", "BLACK_FRIDAY_PROMO"),
            f"unexpected pricing_regimes: {cfg.pricing_regimes}",
        )
        _check(
            cfg.eval_scopes == ("SINGLE_TICKET", "MULTI_ACCOUNT_FLEET"),
            f"unexpected eval_scopes: {cfg.eval_scopes}",
        )
        _check(
            cfg.risk_spectrum_tiers
            == ("T1_ULTRA_SAFE", "T2_CONSERVATIVE", "T3_BALANCED", "T4_AGGRESSIVE_SPRINT", "T5_MAX_THROTTLE_YOLO"),
            f"unexpected risk_spectrum_tiers: {cfg.risk_spectrum_tiers}",
        )
        _check(
            set(cfg.alpha_lifecycle_states)
            == {
                "DISCOVERED",
                "CLUSTER_A_PASS",
                "BLIND_B_VERIFIED",
                "BENCH_READY",
                "SHADOW_INCUBATION",
                "ACTIVE_1X",
                "DECAY_AMBER_0_5X",
                "RETIRED",
                "KILLED",
            },
            f"unexpected alpha_lifecycle_states: {cfg.alpha_lifecycle_states}",
        )
        _check(len(cfg.bottleneck_codes) >= 15, "bottleneck_codes must be comprehensive")

    def test_all_nine_metrics_partition_entire_real_line_zero_dead_zones(self) -> None:
        cfg, _ = ec.load_evaluation_taxonomy()
        expected_metrics = (
            "profit_factor",
            "calmar",
            "sharpe",
            "ev_per_fee",
            "funded_12m_blowup",
            "ruin_36m",
            "p_le_zero_24m",
            "payout_1_cal_days",
            "slippage_breakeven",
        )
        _check(set(expected_metrics).issubset(set(cfg.metric_intervals.keys())), "missing required metric_intervals")

        for mid in expected_metrics:
            spec = cfg.metric_intervals[mid]
            boundaries = [b.upper_bound for b in spec.bands[:-1] if b.upper_bound is not None]
            _check(len(boundaries) == 3, f"{mid} must have 3 interior cutpoints")
            probes = [-1e9, -100.0, -1e-9, 0.0, 1e-9, 100.0, 1e9]
            for bnd in boundaries:
                probes.extend([bnd - 1e-9, bnd, bnd + 1e-9])
            for x in probes:
                band = ec.classify_metric_interval(mid, x, cfg)
                _check(band in ("BAD", "ADEQUATE", "GOOD", "TOP_1_PCT"), f"{mid}({x}) -> invalid {band}")

            # Verify exact boundary transitions (left half-open: [lo, hi))
            for idx, bnd in enumerate(boundaries):
                left_grade = spec.classify(bnd - 1e-9)
                at_grade = spec.classify(bnd)
                _check(
                    left_grade == spec.bands[idx].grade,
                    f"{mid} below boundary {bnd}: expected {spec.bands[idx].grade}, got {left_grade}",
                )
                _check(
                    at_grade == spec.bands[idx + 1].grade,
                    f"{mid} at boundary {bnd}: expected {spec.bands[idx + 1].grade}, got {at_grade}",
                )

    def test_four_inside_out_tiers_and_five_phases_and_blindness_mapping(self) -> None:
        cfg, _ = ec.load_evaluation_taxonomy()
        for tier in ("T1_CFD_PROP", "T2_CME_FUTURES", "T3_MULTI_ASSET_OWNBOOK", "T4_LIVE_OPS"):
            _check(tier in cfg.domain_tier_thresholds, f"missing tier {tier}")
            phases = cfg.domain_tier_thresholds[tier].phases
            _check(
                set(phases.keys()) == {"p1", "p2", "pass_eval", "funded_12m", "overall_36m"},
                f"{tier} must declare all 5 phases",
            )

        _check(ec.map_blindness_tier("OLD12", cfg) == "DEV_CLB_CONSUMED_12OLD", "OLD12 mapping mismatch")
        _check(
            ec.map_blindness_tier("DEV_CLB_CONSUMED_12OLD", cfg) == "DEV_CLB_CONSUMED_12OLD",
            "DEV_CLB_CONSUMED_12OLD mapping mismatch",
        )
        _check(
            ec.map_blindness_tier("NEW9_D1_VIEWED_M1_UNSEEN", cfg) == "M1_UNSEEN_D1_VIEWED",
            "NEW9 mapping mismatch",
        )
        _check(
            ec.map_blindness_tier("TRUE_BLIND_CLB_NEW7_CROSSES", cfg) == "M1_UNSEEN_D1_VIEWED",
            "TRUE_BLIND_CLB_NEW7_CROSSES mapping mismatch",
        )
        with pytest.raises(ValueError, match="UNKNOWN_BLINDNESS_TIER"):
            ec.map_blindness_tier("INVENTED_TIER", cfg)

        # Verify immutable ftmo_specs_28.json was NOT mutated
        ftmo_path = REPO_ROOT / "tooling" / "ai-engines" / "configs" / "ssot" / "ftmo_specs_28.json"
        _check(
            _sha256_file(ftmo_path) == FTMO_SPECS_IMMUTABLE_SHA256,
            "IMMUTABLE VIOLATION: ftmo_specs_28.json digest changed!",
        )


# ---------------------------------------------------------------------------
# 2. UI Design System Contract Parity & Hygiene (W5-G04)
# ---------------------------------------------------------------------------


class TestEvaluationScorecardUIContract:
    def test_contract_md_and_schema_json_match_pydantic_export(self) -> None:
        _check(CONTRACT_MD_PATH.is_file(), f"missing {CONTRACT_MD_PATH}")
        _check(SCHEMA_JSON_PATH.is_file(), f"missing {SCHEMA_JSON_PATH}")
        _check(TRADING_UI_CONTRACT_PATH.is_file(), f"missing {TRADING_UI_CONTRACT_PATH}")

        contract_bytes = CONTRACT_MD_PATH.read_bytes()
        _check(b"\r\n" not in contract_bytes, "CONTRACT.md must have 0 CRLF")
        _check(not contract_bytes.startswith(b"\xef\xbb\xbf"), "CONTRACT.md must have 0 BOM")
        contract_text = contract_bytes.decode("utf-8")
        lower_txt = contract_text.lower()
        _check(
            "status:** `candidate`" in lower_txt or "status: candidate" in lower_txt,
            "must declare candidate status",
        )
        _check("TRADING-UI-CONTRACT.md#L19" in contract_text, "must reference TRADING-UI-CONTRACT.md:19")
        _check("AGENTS.md#L26" in contract_text, "must reference UI/AGENTS.md:26")
        _check("presentation-state/1.0.0/CONTRACT.md" in contract_text, "must reference presentation-state@1.0.0")
        _check("$" not in contract_text, "CONTRACT.md prose must contain 0 bare dollar signs")

        # Schema parity: on-disk schema.json MUST match Pydantic v2 export exactly
        schema_bytes = SCHEMA_JSON_PATH.read_bytes()
        _check(b"\r\n" not in schema_bytes, "schema.json must have 0 CRLF")
        _check(not schema_bytes.startswith(b"\xef\xbb\xbf"), "schema.json must have 0 BOM")
        disk_schema = json.loads(schema_bytes.decode("utf-8"))
        expected_schema = ec.export_scorecard_json_schema()
        _check(disk_schema == expected_schema, "UI schema.json drifted from EvaluationScorecard Pydantic v2 export!")
        _check(disk_schema["$schema"] == ec.JSON_SCHEMA_DRAFT_2020_12, "schema.json must declare Draft 2020-12")
        _check(
            disk_schema.get("description", "").startswith("Candidate trading-domain UI & backend scorecard contract"),
            f"schema.json top-level description was overwritten: {disk_schema.get('description')!r}",
        )

        # Draft 2020-12 numeric bounds compliance: ZERO non-standard 'ge'/'le'/'gt'/'lt' keys,
        # and standard 'minimum'/'maximum' keywords emitted on all 13 bounded numeric constraints.
        forbidden_bound_hits: list[str] = []
        min_max_hits: list[str] = []

        def _walk_schema_bounds(node: Any, path_str: str) -> None:
            if isinstance(node, dict):
                for key, val in node.items():
                    child_path = f"{path_str}.{key}" if path_str else str(key)
                    if key in ("ge", "le", "gt", "lt"):
                        forbidden_bound_hits.append(child_path)
                    elif key in ("minimum", "maximum"):
                        min_max_hits.append(child_path)
                    _walk_schema_bounds(val, child_path)
            elif isinstance(node, list):
                for idx, item in enumerate(node):
                    _walk_schema_bounds(item, f"{path_str}[{idx}]")

        _walk_schema_bounds(disk_schema, "")
        _check(
            len(forbidden_bound_hits) == 0,
            f"Non-standard Draft 2020-12 numeric bound keys found in schema.json: {forbidden_bound_hits}",
        )
        _check(
            len(min_max_hits) == 13,
            f"Expected 13 standard minimum/maximum bounds in schema.json, got {len(min_max_hits)}: {min_max_hits}",
        )
        sev_prop = disk_schema["$defs"]["BottleneckItem"]["properties"]["severity_rank"]
        _check(sev_prop.get("minimum") == 1, f"severity_rank must emit minimum=1: {sev_prop}")
        hp_props = disk_schema["$defs"]["HorizonPartitionPct"]["properties"]
        for pct_key in ("pass_pct", "fail_pct", "pending_pct"):
            _check(
                hp_props[pct_key].get("minimum") == 0.0 and hp_props[pct_key].get("maximum") == 100.0,
                f"HorizonPartitionPct.{pct_key} must emit minimum=0.0 & maximum=100.0: {hp_props[pct_key]}",
            )
        pg_props = disk_schema["$defs"]["PhaseGradeDetail"]["properties"]
        for rate_key in ("pass_rate_pct", "fail_rate_pct", "pending_rate_pct"):
            num_branch = next((b for b in pg_props[rate_key]["anyOf"] if b.get("type") == "number"), {})
            _check(
                num_branch.get("minimum") == 0.0 and num_branch.get("maximum") == 100.0,
                f"PhaseGradeDetail.{rate_key} must emit minimum=0.0 & maximum=100.0: {pg_props[rate_key]}",
            )

        # TRADING-UI-CONTRACT.md additive reference without disturbing M1 sections
        tui_bytes = TRADING_UI_CONTRACT_PATH.read_bytes()
        _check(b"\r\n" not in tui_bytes, "TRADING-UI-CONTRACT.md must have 0 CRLF")
        tui_text = tui_bytes.decode("utf-8")
        _check("## M1 identity and context contract" in tui_text, "existing M1 identity section must stay intact")
        _check("## M1 acceptance oracles" in tui_text, "existing M1 acceptance section must stay intact")
        _check(
            "../contracts/evaluation-scorecard/1.0.0/CONTRACT.md" in tui_text,
            "TRADING-UI-CONTRACT.md must link evaluation-scorecard@1.0.0 CONTRACT.md",
        )

    def test_no_jsonschema_import_and_zero_bare_asserts_in_wave5_files(self) -> None:
        targets = (
            REPO_ROOT / "tooling" / "ai-engines" / "quant_factory" / "wave5" / "evaluation_catalog.py",
            Path(__file__).resolve(),
            Path(__file__).resolve().with_name("test_wave5_evaluation_catalog.py"),
        )
        for fp in targets:
            if not fp.is_file():
                continue
            raw = fp.read_bytes()
            _check(b"\r\n" not in raw, f"{fp.name} has CRLF line endings")
            _check(not raw.startswith(b"\xef\xbb\xbf"), f"{fp.name} has UTF-8 BOM")
            tree = ast.parse(raw.decode("utf-8"), filename=str(fp))
            for node in ast.walk(tree):
                _check(
                    not isinstance(node, ast.Assert),
                    f"bare assert forbidden in {fp.name}:{getattr(node, 'lineno', 0)}",
                )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        _check(not alias.name.startswith("jsonschema"), f"jsonschema import forbidden in {fp.name}")
                elif isinstance(node, ast.ImportFrom):
                    _check(
                        not (node.module or "").startswith("jsonschema"),
                        f"jsonschema import forbidden in {fp.name}",
                    )


# ---------------------------------------------------------------------------
# 3. Negative Mutation Tests (Fail-Closed Under `python -O`)
# ---------------------------------------------------------------------------


class TestNegativeMutationsFailClosed:
    @pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_nan_and_inf_metrics(self, bad_val: float) -> None:
        with pytest.raises(ValidationError):
            ec.EvaluationInputRecord(record_id="bad-nan", profit_factor=bad_val)
        with pytest.raises(ValueError, match="finite"):
            ec.classify_metric_interval("profit_factor", bad_val)

    @pytest.mark.parametrize("bad_bool", [True, False])
    def test_rejects_bool_disguised_as_metric_number(self, bad_bool: bool) -> None:
        with pytest.raises(ValidationError):
            ec.EvaluationInputRecord(record_id="bad-bool", sharpe=bad_bool)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            ec.HorizonPartitionPct(pass_pct=bad_bool, fail_pct=50.0, pending_pct=50.0)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="not bool"):
            ec.classify_metric_interval("calmar", bad_bool)  # type: ignore[arg-type]

    def test_rejects_dead_zone_and_overlap_in_taxonomy_intervals(self) -> None:
        # Dead zone mutation: leave gap [1.05, 1.10) in profit_factor
        raw_gap = _load_raw_taxonomy()
        raw_gap["metric_intervals"]["profit_factor"]["bands"][0]["upper_bound"] = 1.05
        with pytest.raises(ValidationError, match="DEAD_ZONE_OR_OVERLAP"):
            ec.EvaluationTaxonomyConfig.model_validate(raw_gap)

        # Overlap / closed-closed boundary mutation: both sides inclusive at 1.10
        raw_closed = _load_raw_taxonomy()
        raw_closed["metric_intervals"]["profit_factor"]["bands"][0]["upper_inclusive"] = True
        with pytest.raises(ValidationError, match="strictly half-open"):
            ec.EvaluationTaxonomyConfig.model_validate(raw_closed)

        # Open-open boundary mutation: point 1.10 falls in dead zone
        raw_open = _load_raw_taxonomy()
        raw_open["metric_intervals"]["profit_factor"]["bands"][1]["lower_inclusive"] = False
        with pytest.raises(ValidationError, match="strictly half-open"):
            ec.EvaluationTaxonomyConfig.model_validate(raw_open)

    @pytest.mark.parametrize(
        "p,f,w",
        [
            (50.0, 30.0, 19.5),
            (50.0, 30.0, 20.5),
            (101.0, 0.0, 0.0),
            (-1.0, 51.0, 50.0),
        ],
    )
    def test_rejects_invalid_partition_sum(self, p: float, f: float, w: float) -> None:
        with pytest.raises(ValidationError):
            ec.HorizonPartitionPct(pass_pct=p, fail_pct=f, pending_pct=w)

    def test_rejects_invalid_presentation_state_missing_labels_and_reason_codes(self) -> None:
        # freshness='partial' without label MUST fail
        with pytest.raises(ValidationError, match="label"):
            ec.PresentationState(availability="ready", freshness="partial", certainty="known")
        # certainty='unknown' without label MUST fail
        with pytest.raises(ValidationError, match="label"):
            ec.PresentationState(availability="ready", freshness="current", certainty="unknown")
        # availability='ready' without freshness/certainty MUST fail
        with pytest.raises(ValidationError, match="freshness"):
            ec.PresentationState(availability="ready", label="Ready")
        # availability='error' without reasonCode MUST fail
        with pytest.raises(ValidationError, match="reasonCode"):
            ec.PresentationState(availability="error", label="Failed to load")
        # availability='denied' without label MUST fail
        with pytest.raises(ValidationError, match="label"):
            ec.PresentationState(availability="denied", reasonCode="broker.denied")
        # availability='loading' without label MUST fail
        with pytest.raises(ValidationError, match="label"):
            ec.PresentationState(availability="loading")

    def test_rejects_holdout_and_order_send_violations(self) -> None:
        with pytest.raises(ValidationError):
            ec.EvaluationInputRecord(record_id="ho-leak", holdout_rows_analysed=1)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            ec.EvaluationInputRecord(record_id="live-order", order_send_count=1)  # type: ignore[arg-type]

    def test_arch_06_catches_dict_or_string_under_pct_key(self, tmp_path: Path) -> None:
        ssot_dir = tmp_path / "tooling" / "ai-engines" / "configs" / "ssot"
        ssot_dir.mkdir(parents=True)
        bad_doc = copy.deepcopy(_load_raw_taxonomy())
        bad_doc["broken_nested_pct"] = {"label": "not a number"}
        (ssot_dir / "evaluation_taxonomy.json").write_text(json.dumps(bad_doc), encoding="utf-8", newline="\n")
        violations = arch.check_arch_06_ssot_unit_suffixes(tmp_path)
        _check(len(violations) >= 1, "[ARCH-06] must catch string/dict under lowercase _pct key")
