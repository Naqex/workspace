"""Wave 5 Unified Evaluation Taxonomy, Grader & Federated DuckDB Catalog (Gates W5-G03 & W5-G04).

Strictly offline Dev-only evaluation & ledger layer:
  - ORDER_SEND_CAPABLE = False, ORDER_SEND_COUNT = 0
  - HOLDOUT_CUTOFF_DATE = "2024-12-31", holdout_rows_analysed = 0
  - 100% Pydantic v2 validation (ZERO `jsonschema` dependency; works in minimal CI)
  - ZERO bare Python `assert` statements (`python -O` safe)
  - Federated Unified DuckDB Catalog backed by `SQLiteRunRegistry` SHA-256 hash chain
  - Exact 3 distinct legacy DuckDB sources (ZERO double counting):
      1) `.runtime/experiments/experiments.duckdb::experiments` (1,279)
      2) `.runtime/offensive4/ml/wave4_ml_m48.duckdb::wave4_ml_m48` (36)
      3) `.runtime/offensive4/frontier/wave4_frontier_m36.duckdb::wave4_frontier_trials` (27)
         (explicitly skips duplicate `experiments` table in `wave4_frontier_m36.duckdb`)
    Total = 1,342 distinct legacy trials.
  - Backfills all 168 Wave 4 Monte Carlo rows (`cases` 81 + `cases_stress_1_5x` 81 +
    `the5ers_reference_rows` 6) reading `profile_id` and `funded_mult` from `ssot_provenance` /
    `sku_funded_diagnostics_1_0x`, preserving BOTH `legacy_grade_code` and `unified_grade_code`,
    and marking missing P1/P2 splits as `UNKNOWN_LEGACY_UNINSTRUMENTED` with valid
    `presentation-state@1.0.0` metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import threading
import weakref
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tooling.run_registry.store import (  # noqa: E402
    JournalCorruptionError,
    Provenance,
    RunEvent,
    RunRecord,
    SQLiteRunRegistry,
    utc_now,
)

# ---------------------------------------------------------------------------
# Hard Safety Invariants & Default Paths
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DATE: str = "2024-12-31"
SCORECARD_CONTRACT_VERSION: str = "1.0.0"
SCORECARD_SCHEMA_ID: str = "https://annam.local/trading-ui/evaluation-scorecard/1.0.0/schema.json"
JSON_SCHEMA_DRAFT_2020_12: str = "https://json-schema.org/draft/2020-12/schema"

DEFAULT_TAXONOMY_PATH: Path = REPO_ROOT / "tooling" / "ai-engines" / "configs" / "ssot" / "evaluation_taxonomy.json"
DEFAULT_EXPERIMENTS_DIR: Path = REPO_ROOT / ".runtime" / "experiments"
DEFAULT_CATALOG_DUCKDB_PATH: Path = DEFAULT_EXPERIMENTS_DIR / "unified_eval_catalog.duckdb"
DEFAULT_CATALOG_REGISTRY_PATH: Path = DEFAULT_EXPERIMENTS_DIR / "unified_eval_registry.sqlite3"
DEFAULT_WAVE4_PARETO_PATH: Path = REPO_ROOT / ".runtime" / "offensive4" / "pareto" / "wave4_pareto_81cases_10k.json"
DEFAULT_SCORECARD_SCHEMA_PATH: Path = (
    REPO_ROOT / "UI" / "contracts" / "evaluation-scorecard" / "1.0.0" / "schema.json"
)

DEFAULT_LEGACY_SOURCES: tuple[dict[str, str], ...] = (
    {
        "source_key": "experiments_core",
        "db_rel_path": ".runtime/experiments/experiments.duckdb",
        "table_name": "experiments",
    },
    {
        "source_key": "wave4_ml_m48",
        "db_rel_path": ".runtime/offensive4/ml/wave4_ml_m48.duckdb",
        "table_name": "wave4_ml_m48",
    },
    {
        "source_key": "wave4_frontier_m36",
        "db_rel_path": ".runtime/offensive4/frontier/wave4_frontier_m36.duckdb",
        "table_name": "wave4_frontier_trials",
    },
)

LEGACY_UNINSTRUMENTED_LABEL_VI: str = "Chưa tách riêng P1/P2 ở dữ liệu Đợt 4"
MAX_FUTURE_TIMESTAMP_SKEW_SEC: int = 300

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE_RE = re.compile(r"^[a-z][a-z0-9_.-]*$")
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.:-]+")
_READONLY_SQL_START_RE = re.compile(r"^\s*(?:SELECT|WITH|EXPLAIN|DESCRIBE|SHOW)\b", re.IGNORECASE)
_FORBIDDEN_SQL_WRITE_RE = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|COPY|CALL|LOAD|INSTALL|EXPORT|IMPORT|MERGE|SET|PRAGMA)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Canonical Literal Types
# ---------------------------------------------------------------------------

GradeBand = Literal[
    "BAD",
    "ADEQUATE",
    "GOOD",
    "TOP_1_PCT",
    "UNKNOWN_LEGACY_UNINSTRUMENTED",
]
NumericGradeBand = Literal["BAD", "ADEQUATE", "GOOD", "TOP_1_PCT"]
EvidenceStage = Literal[
    "DEV_IS",
    "DEV_BLIND_OOS",
    "DEV_CONSUMED_OOS",
    "HOLDOUT_SEALED_ONCE",
    "SHADOW_DEMO",
    "LIVE_REAL",
]
DataResolution = Literal[
    "TICK_REAL",
    "M1_BID_ASK",
    "M1_BID_SPREAD",
    "M1_SINGLE_SIDE",
    "APPROX_DAILY",
]
PricingRegime = Literal["ALL_REGULAR_SSOT", "BLACK_FRIDAY_PROMO"]
EvalScope = Literal["SINGLE_TICKET", "MULTI_ACCOUNT_FLEET"]
DomainTier = Literal["T1_CFD_PROP", "T2_CME_FUTURES", "T3_MULTI_ASSET_OWNBOOK", "T4_LIVE_OPS"]
EvalPhase = Literal["p1", "p2", "pass_eval", "funded_12m", "overall_36m"]
ScorecardPhaseKey = Literal["p1", "p2", "pass_eval", "funded_12m"]
RiskSpectrumTier = Literal[
    "T1_ULTRA_SAFE",
    "T2_CONSERVATIVE",
    "T3_BALANCED",
    "T4_AGGRESSIVE_SPRINT",
    "T5_MAX_THROTTLE_YOLO",
]
AlphaLifecycleState = Literal[
    "DISCOVERED",
    "CLUSTER_A_PASS",
    "BLIND_B_VERIFIED",
    "BENCH_READY",
    "SHADOW_INCUBATION",
    "ACTIVE_1X",
    "DECAY_AMBER_0_5X",
    "RETIRED",
    "KILLED",
]
CanonicalBlindnessTier = Literal["DEV_CLB_CONSUMED_12OLD", "M1_UNSEEN_D1_VIEWED"]
MetricDirection = Literal["higher_is_better", "lower_is_better"]

GRADE_RANK: dict[str, int] = {
    "BAD": 0,
    "ADEQUATE": 1,
    "GOOD": 2,
    "TOP_1_PCT": 3,
    "UNKNOWN_LEGACY_UNINSTRUMENTED": -1,
}
RANK_TO_GRADE: dict[int, NumericGradeBand] = {
    0: "BAD",
    1: "ADEQUATE",
    2: "GOOD",
    3: "TOP_1_PCT",
}
GRADE_LABEL_VI: dict[str, str] = {
    "BAD": "Xấu",
    "ADEQUATE": "Đủ dùng",
    "GOOD": "Tốt",
    "TOP_1_PCT": "Top 1% thực tế",
    "UNKNOWN_LEGACY_UNINSTRUMENTED": "Chưa tách số liệu (Đợt cũ)",
}

# ---------------------------------------------------------------------------
# Strict Fail-Closed Validators (Zero bool coercion, Zero NaN/Inf)
# ---------------------------------------------------------------------------


def _reject_bool_and_coerce_finite_float(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected finite int/float (not bool), got {type(value).__name__}")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"value must be finite (NaN/Inf forbidden), got {value!r}")
    return out


def _validate_strict_int(value: Any) -> int:
    if type(value) is not int:
        raise ValueError(f"expected strict int (not bool/float/str), got {type(value).__name__}")
    return value


def _validate_sha256_hex(value: Any) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError("expected lowercase 64-character hex SHA-256")
    return value


def _validate_verified_utc_input(value: Any) -> str | datetime:
    if not isinstance(value, (str, datetime)):
        raise ValueError(f"timestamp must be ISO-8601 string or aware datetime, got {type(value).__name__}")
    if isinstance(value, str) and not value.strip():
        raise ValueError("timestamp string must not be empty")
    return value


def _validate_verified_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware UTC")
    as_utc = value.astimezone(UTC)
    max_allowed = datetime.now(UTC) + timedelta(seconds=MAX_FUTURE_TIMESTAMP_SKEW_SEC)
    if as_utc > max_allowed:
        raise ValueError(
            f"timestamp {as_utc.isoformat()} exceeds allowed future skew (+{MAX_FUTURE_TIMESTAMP_SKEW_SEC}s)"
        )
    return as_utc


def _validate_non_empty_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected non-empty string")
    return value.strip()


def _validate_reason_code(value: Any) -> str:
    if not isinstance(value, str) or _REASON_CODE_RE.fullmatch(value) is None:
        raise ValueError(f"reasonCode must match ^[a-z][a-z0-9_.-]*$, got {value!r}")
    return value


FiniteFloat = Annotated[float, BeforeValidator(_reject_bool_and_coerce_finite_float)]
PctFloat = Annotated[float, Field(ge=0.0, le=100.0), BeforeValidator(_reject_bool_and_coerce_finite_float)]
FracFloat = Annotated[float, Field(ge=0.0, le=1.0), BeforeValidator(_reject_bool_and_coerce_finite_float)]
StrictNonNegInt = Annotated[int, Field(ge=0), BeforeValidator(_validate_strict_int)]
StrictPosInt = Annotated[int, Field(ge=1), BeforeValidator(_validate_strict_int)]
Sha256Hex = Annotated[str, BeforeValidator(_validate_sha256_hex)]
NonEmptyText = Annotated[str, BeforeValidator(_validate_non_empty_text)]
ReasonCodeStr = Annotated[str, BeforeValidator(_validate_reason_code)]
VerifiedUtcDatetime = Annotated[
    datetime,
    BeforeValidator(_validate_verified_utc_input),
    AfterValidator(_validate_verified_utc),
]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_reg_id(raw: str, *, prefix: str = "ev", max_len: int = 120) -> str:
    cleaned = _SAFE_ID_RE.sub("_", raw.strip()).strip("_.:-")
    if not cleaned or not cleaned[0].isalnum():
        cleaned = f"{prefix}-{cleaned}" if cleaned else f"{prefix}-0"
    return cleaned[:max_len]


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


# ---------------------------------------------------------------------------
# Pydantic v2 Base & Presentation-State@1.0.0 Contract
# ---------------------------------------------------------------------------


class StrictCatalogModel(BaseModel):
    """Frozen, extra-forbidding, NaN/Inf-rejecting base model."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class PresentationState(StrictCatalogModel):
    """Exact Pydantic v2 mirror of `UI-Systems/core/contracts/presentation-state/1.0.0/schema.json`."""

    availability: Literal["loading", "ready", "empty", "unavailable", "error", "denied"]
    freshness: Literal["current", "stale", "partial", "unknown"] | None = None
    certainty: Literal["known", "uncertain", "unknown"] | None = None
    reasonCode: ReasonCodeStr | None = None
    label: NonEmptyText | None = None
    ariaLabel: NonEmptyText | None = None

    @model_validator(mode="after")
    def _enforce_presentation_state_rules(self) -> PresentationState:
        if self.availability == "ready":
            if self.freshness is None or self.certainty is None:
                raise ValueError("availability='ready' requires both freshness and certainty")
        if self.availability in ("error", "denied") and not self.reasonCode:
            raise ValueError(f"availability={self.availability!r} requires a non-empty reasonCode")
        if self.availability in ("loading", "empty", "unavailable", "error", "denied") and not self.label:
            raise ValueError(f"availability={self.availability!r} requires a non-empty label")
        if self.freshness in ("stale", "partial", "unknown") and not self.label:
            raise ValueError(f"freshness={self.freshness!r} requires a non-empty label")
        if self.certainty == "unknown" and not self.label:
            raise ValueError("certainty='unknown' requires a non-empty label (never render as numeric zero)")
        return self


# ---------------------------------------------------------------------------
# Pydantic v2 Taxonomy Models (Zero Dead Zones, Continuous Half-Open Intervals)
# ---------------------------------------------------------------------------


class MetricIntervalBand(StrictCatalogModel):
    grade: NumericGradeBand
    lower_bound: FiniteFloat | None = None
    lower_inclusive: bool
    upper_bound: FiniteFloat | None = None
    upper_inclusive: bool
    label_vi: NonEmptyText

    @model_validator(mode="after")
    def _validate_interval_endpoints(self) -> MetricIntervalBand:
        if self.lower_bound is None and self.lower_inclusive:
            raise ValueError("unbounded lower endpoint (-inf) must have lower_inclusive=False")
        if self.upper_bound is None and self.upper_inclusive:
            raise ValueError("unbounded upper endpoint (+inf) must have upper_inclusive=False")
        if self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound >= self.upper_bound:
                raise ValueError(
                    f"interval lower_bound ({self.lower_bound}) must be strictly < upper_bound ({self.upper_bound})"
                )
        return self

    def contains(self, value: float) -> bool:
        if self.lower_bound is not None:
            if self.lower_inclusive:
                if value < self.lower_bound:
                    return False
            elif value <= self.lower_bound:
                return False
        if self.upper_bound is not None:
            if self.upper_inclusive:
                if value > self.upper_bound:
                    return False
            elif value >= self.upper_bound:
                return False
        return True


class MetricIntervalSpec(StrictCatalogModel):
    metric_id: NonEmptyText
    display_name_vi: NonEmptyText
    unit: NonEmptyText
    direction: MetricDirection
    record_field: NonEmptyText
    bottleneck_code: NonEmptyText
    bands: tuple[MetricIntervalBand, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def _validate_contiguous_partition(self) -> MetricIntervalSpec:
        expected_grades = (
            ("BAD", "ADEQUATE", "GOOD", "TOP_1_PCT")
            if self.direction == "higher_is_better"
            else ("TOP_1_PCT", "GOOD", "ADEQUATE", "BAD")
        )
        actual_grades = tuple(b.grade for b in self.bands)
        if actual_grades != expected_grades:
            raise ValueError(
                f"{self.metric_id}: bands order {actual_grades!r} must match {expected_grades!r} for {self.direction}"
            )
        if self.bands[0].lower_bound is not None or self.bands[0].lower_inclusive:
            raise ValueError(f"{self.metric_id}: first band must open at -inf")
        if self.bands[-1].upper_bound is not None or self.bands[-1].upper_inclusive:
            raise ValueError(f"{self.metric_id}: last band must open at +inf")
        for idx in range(len(self.bands) - 1):
            left = self.bands[idx]
            right = self.bands[idx + 1]
            if left.upper_bound is None or right.lower_bound is None:
                raise ValueError(f"{self.metric_id}: interior boundary {idx} cannot be unbounded")
            if not math.isclose(left.upper_bound, right.lower_bound, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(
                    f"{self.metric_id}: DEAD_ZONE_OR_OVERLAP between band {idx} upper={left.upper_bound} "
                    f"and band {idx + 1} lower={right.lower_bound}"
                )
            if left.upper_inclusive == right.lower_inclusive:
                raise ValueError(
                    f"{self.metric_id}: boundary {left.upper_bound} must be strictly half-open "
                    f"(left.upper_inclusive={left.upper_inclusive} != right.lower_inclusive={right.lower_inclusive})"
                )
        return self

    def classify(self, value: float) -> NumericGradeBand:
        val = _reject_bool_and_coerce_finite_float(value)
        matches = [b.grade for b in self.bands if b.contains(val)]
        if len(matches) != 1:
            raise ValueError(f"{self.metric_id}: value {val!r} matched {len(matches)} bands ({matches!r})")
        return matches[0]

    def target_for_grade(self, target_grade: NumericGradeBand) -> float | None:
        for b in self.bands:
            if b.grade == target_grade:
                return b.lower_bound if self.direction == "higher_is_better" else b.upper_bound
        return None


class PhaseMetricThreshold(StrictCatalogModel):
    record_field: NonEmptyText
    direction: MetricDirection
    unit: NonEmptyText
    bottleneck_code: NonEmptyText
    adequate: FiniteFloat
    good: FiniteFloat
    top_1: FiniteFloat

    @model_validator(mode="after")
    def _validate_monotonic_cutoffs(self) -> PhaseMetricThreshold:
        if self.direction == "higher_is_better":
            if not (self.adequate < self.good < self.top_1):
                raise ValueError(
                    f"{self.record_field}: higher_is_better requires adequate < good < top_1 "
                    f"(got {self.adequate}, {self.good}, {self.top_1})"
                )
        else:
            if not (self.top_1 < self.good < self.adequate):
                raise ValueError(
                    f"{self.record_field}: lower_is_better requires top_1 < good < adequate "
                    f"(got {self.top_1}, {self.good}, {self.adequate})"
                )
        return self

    def classify(self, value: float) -> NumericGradeBand:
        val = _reject_bool_and_coerce_finite_float(value)
        if self.direction == "higher_is_better":
            if val < self.adequate:
                return "BAD"
            if val < self.good:
                return "ADEQUATE"
            if val < self.top_1:
                return "GOOD"
            return "TOP_1_PCT"
        if val < self.top_1:
            return "TOP_1_PCT"
        if val < self.good:
            return "GOOD"
        if val < self.adequate:
            return "ADEQUATE"
        return "BAD"


class PhaseThresholdSpec(StrictCatalogModel):
    applicable: bool
    metrics: dict[str, PhaseMetricThreshold] = Field(min_length=1)


class DomainTierThresholds(StrictCatalogModel):
    tier_id: DomainTier
    label_vi: NonEmptyText
    phases: dict[EvalPhase, PhaseThresholdSpec]

    @model_validator(mode="after")
    def _validate_all_five_phases(self) -> DomainTierThresholds:
        required: set[EvalPhase] = {"p1", "p2", "pass_eval", "funded_12m", "overall_36m"}
        if set(self.phases.keys()) != required:
            raise ValueError(f"{self.tier_id}: phases must match exact set {sorted(required)}")
        return self


class BlindnessTierMappingSpec(StrictCatalogModel):
    source_immutable_ref: NonEmptyText
    note: NonEmptyText
    canonical_tiers: tuple[CanonicalBlindnessTier, ...] = Field(min_length=2)
    raw_to_wave5: dict[str, CanonicalBlindnessTier]

    @model_validator(mode="after")
    def _validate_required_mappings(self) -> BlindnessTierMappingSpec:
        required_pairs = {
            "OLD12": "DEV_CLB_CONSUMED_12OLD",
            "DEV_CLB_CONSUMED_12OLD": "DEV_CLB_CONSUMED_12OLD",
            "NEW9_D1_VIEWED_M1_UNSEEN": "M1_UNSEEN_D1_VIEWED",
            "TRUE_BLIND_CLB_NEW7_CROSSES": "M1_UNSEEN_D1_VIEWED",
        }
        for raw, expected in required_pairs.items():
            if self.raw_to_wave5.get(raw) != expected:
                raise ValueError(f"blindness_tier_mapping must map {raw!r} -> {expected!r}")
        return self


class EvaluationTaxonomyConfig(StrictCatalogModel):
    """Root SSOT schema for `tooling/ai-engines/configs/ssot/evaluation_taxonomy.json`."""

    schema_version: Literal["naqex-ssot-evaluation-taxonomy-v1"] = "naqex-ssot-evaluation-taxonomy-v1"
    updated_utc: VerifiedUtcDatetime
    holdout_cutoff_date: Literal["2024-12-31"] = "2024-12-31"
    holdout_rows_analysed: Literal[0] = 0
    order_send_count: Literal[0] = 0

    grade_bands: tuple[GradeBand, ...]
    grade_band_specs: dict[GradeBand, dict[str, Any]]
    legacy_grade_mapping: dict[str, GradeBand]
    evidence_stages: tuple[EvidenceStage, ...]
    evidence_stage_specs: dict[EvidenceStage, dict[str, Any]]
    legacy_evidence_stage_mapping: dict[str, EvidenceStage]
    data_resolutions: tuple[DataResolution, ...]
    data_resolution_specs: dict[DataResolution, dict[str, Any]]
    legacy_resolution_mapping: dict[str, DataResolution]
    pricing_regimes: tuple[PricingRegime, ...]
    pricing_regime_specs: dict[PricingRegime, dict[str, Any]]
    legacy_pricing_regime_mapping: dict[str, PricingRegime]
    eval_scopes: tuple[EvalScope, ...]
    eval_scope_specs: dict[EvalScope, dict[str, Any]]
    domain_tiers: tuple[DomainTier, ...]
    eval_phases: tuple[EvalPhase, ...]
    risk_spectrum_tiers: tuple[RiskSpectrumTier, ...]
    risk_spectrum_tier_specs: dict[RiskSpectrumTier, dict[str, Any]]
    alpha_lifecycle_states: tuple[AlphaLifecycleState, ...]
    bottleneck_codes: tuple[NonEmptyText, ...]
    bottleneck_catalog: dict[str, dict[str, Any]]
    blindness_tier_mapping: BlindnessTierMappingSpec
    legacy_uninstrumented_presentation_state: PresentationState
    metric_intervals: dict[str, MetricIntervalSpec]
    domain_tier_thresholds: dict[DomainTier, DomainTierThresholds]

    @model_validator(mode="after")
    def _validate_cross_references(self) -> EvaluationTaxonomyConfig:
        required_metrics = {
            "profit_factor",
            "calmar",
            "sharpe",
            "ev_per_fee",
            "funded_12m_blowup",
            "ruin_36m",
            "p_le_zero_24m",
            "payout_1_cal_days",
            "slippage_breakeven",
        }
        missing_metrics = sorted(required_metrics - set(self.metric_intervals.keys()))
        if missing_metrics:
            raise ValueError(f"metric_intervals missing required metrics: {missing_metrics}")
        required_tiers: set[DomainTier] = {
            "T1_CFD_PROP",
            "T2_CME_FUTURES",
            "T3_MULTI_ASSET_OWNBOOK",
            "T4_LIVE_OPS",
        }
        if set(self.domain_tier_thresholds.keys()) != required_tiers:
            raise ValueError(f"domain_tier_thresholds must cover exact 4 tiers: {sorted(required_tiers)}")
        codes_set = set(self.bottleneck_codes)
        if codes_set != set(self.bottleneck_catalog.keys()):
            raise ValueError("bottleneck_codes and bottleneck_catalog keys must match exactly")
        for mid, spec in self.metric_intervals.items():
            if mid != spec.metric_id:
                raise ValueError(f"metric_intervals key {mid!r} != metric_id {spec.metric_id!r}")
            if spec.bottleneck_code not in codes_set:
                raise ValueError(f"unknown bottleneck_code {spec.bottleneck_code!r} in metric {mid!r}")
        for tier_id, tspec in self.domain_tier_thresholds.items():
            if tier_id != tspec.tier_id:
                raise ValueError(f"domain_tier_thresholds key {tier_id!r} != tier_id {tspec.tier_id!r}")
            for ph_name, pspec in tspec.phases.items():
                for mkey, mthr in pspec.metrics.items():
                    if mthr.bottleneck_code not in codes_set:
                        raise ValueError(
                            f"unknown bottleneck_code {mthr.bottleneck_code!r} in {tier_id}.{ph_name}.{mkey}"
                        )
        return self


@lru_cache(maxsize=4)
def _load_taxonomy_cached(path_str: str) -> tuple[EvaluationTaxonomyConfig, str]:
    p = Path(path_str)
    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)
    cfg = EvaluationTaxonomyConfig.model_validate(data)
    return cfg, _sha256_file(p)


def load_evaluation_taxonomy(path: Path = DEFAULT_TAXONOMY_PATH) -> tuple[EvaluationTaxonomyConfig, str]:
    """Load and fail-closed validate `evaluation_taxonomy.json` + return `(config, file_sha256)`."""
    resolved = Path(path).resolve()
    return _load_taxonomy_cached(str(resolved))


def map_blindness_tier(raw_tier: str, taxonomy: EvaluationTaxonomyConfig | None = None) -> CanonicalBlindnessTier:
    """Map raw `ftmo_specs_28.json` blindness tier or `OLD12` alias to canonical Wave 5 tier."""
    cfg = taxonomy if taxonomy is not None else load_evaluation_taxonomy()[0]
    key = _validate_non_empty_text(raw_tier)
    if key not in cfg.blindness_tier_mapping.raw_to_wave5:
        raise ValueError(f"UNKNOWN_BLINDNESS_TIER: {raw_tier!r}")
    return cfg.blindness_tier_mapping.raw_to_wave5[key]


def classify_metric_interval(
    metric_id: str,
    value: float,
    taxonomy: EvaluationTaxonomyConfig | None = None,
) -> NumericGradeBand:
    """Classify a single finite numeric value via continuous half-open intervals (zero dead zones)."""
    cfg = taxonomy if taxonomy is not None else load_evaluation_taxonomy()[0]
    if metric_id not in cfg.metric_intervals:
        raise ValueError(f"UNKNOWN_METRIC_ID: {metric_id!r}")
    return cfg.metric_intervals[metric_id].classify(value)


# ---------------------------------------------------------------------------
# Evaluation Input & Canonical Scorecard Contract (UI + Backend Shared SSOT)
# ---------------------------------------------------------------------------


class HorizonPartitionPct(StrictCatalogModel):
    """Exact 100%-sum Pass / Fail / Pending partition for one evaluation horizon."""

    pass_pct: PctFloat
    fail_pct: PctFloat
    pending_pct: PctFloat

    @model_validator(mode="after")
    def _validate_exact_100_sum(self) -> HorizonPartitionPct:
        total = self.pass_pct + self.fail_pct + self.pending_pct
        if abs(total - 100.0) > 1e-4:
            raise ValueError(
                f"INVALID_PARTITION_SUM: pass_pct({self.pass_pct}) + fail_pct({self.fail_pct}) + "
                f"pending_pct({self.pending_pct}) = {total:.6f} != 100.0"
            )
        return self


class BottleneckItem(StrictCatalogModel):
    """Exact machine-readable & plain-Vietnamese bottleneck entry."""

    code: NonEmptyText
    metric_id: NonEmptyText
    phase: EvalPhase
    current_value: FiniteFloat | None = None
    target_threshold: FiniteFloat | None = None
    target_grade: GradeBand
    severity_rank: StrictPosInt
    label_vi: NonEmptyText


class PhaseGradeDetail(StrictCatalogModel):
    """Per-phase grade with explicit `presentation-state@1.0.0` metadata."""

    phase: EvalPhase
    grade: GradeBand
    grade_vi: NonEmptyText
    presentation_state: PresentationState
    metric_grades: dict[str, GradeBand] = Field(default_factory=dict)
    pass_rate_pct: PctFloat | None = None
    fail_rate_pct: PctFloat | None = None
    pending_rate_pct: PctFloat | None = None
    bottlenecks: tuple[BottleneckItem, ...] = ()

    @model_validator(mode="after")
    def _validate_phase_consistency(self) -> PhaseGradeDetail:
        if self.grade == "UNKNOWN_LEGACY_UNINSTRUMENTED":
            if self.presentation_state.certainty != "unknown" or not self.presentation_state.label:
                raise ValueError(
                    "UNKNOWN_LEGACY_UNINSTRUMENTED phase requires certainty='unknown' and non-empty label"
                )
        if (
            self.pass_rate_pct is not None
            and self.fail_rate_pct is not None
            and self.pending_rate_pct is not None
        ):
            total = self.pass_rate_pct + self.fail_rate_pct + self.pending_rate_pct
            if abs(total - 100.0) > 1e-4:
                raise ValueError(f"phase {self.phase} partition sum {total:.6f} != 100.0")
        return self


class EvaluationInputRecord(StrictCatalogModel):
    """Validated input record for canonical `grade_evaluation_record(...)`."""

    record_id: NonEmptyText
    domain_tier: DomainTier = "T1_CFD_PROP"
    eval_scope: EvalScope = "MULTI_ACCOUNT_FLEET"
    pricing_regime: PricingRegime = "ALL_REGULAR_SSOT"
    evidence_stage: EvidenceStage = "DEV_CONSUMED_OOS"
    data_resolution: DataResolution = "APPROX_DAILY"
    execution_status: NonEmptyText = "MEASURED_DEMO_EXECUTION"
    risk_spectrum_tier: RiskSpectrumTier | None = None
    legacy_grade_code: NonEmptyText | None = None

    # Core continuous-interval metrics
    profit_factor: FiniteFloat | None = None
    calmar: FiniteFloat | None = None
    sharpe: FiniteFloat | None = None
    ev_per_fee: FiniteFloat | None = None
    funded_12m_blowup_pct: PctFloat | None = None
    ruin_36m_pct: PctFloat | None = None
    p_le_zero_24m_pct: PctFloat | None = None
    payout_1_cal_days: FiniteFloat | None = None
    slippage_breakeven_mult: FiniteFloat | None = None

    # Optional phase-level & balanced reporting metrics
    p1_pass_rate_pct: PctFloat | None = None
    p1_fail_rate_pct: PctFloat | None = None
    p1_pending_rate_pct: PctFloat | None = None
    p2_pass_rate_pct: PctFloat | None = None
    p2_fail_rate_pct: PctFloat | None = None
    p2_pending_rate_pct: PctFloat | None = None
    pass_eval_12m_pct: PctFloat | None = None
    pass_eval_36m_pct: PctFloat | None = None
    monthly_pass_fail_pending: dict[str, HorizonPartitionPct] | None = None
    first_ticket_pass_fail_pending: dict[str, HorizonPartitionPct] | None = None
    funded_12m_wilson_95_ub_pct: PctFloat | None = None
    ev_per_trade_r: FiniteFloat | None = None
    winrate_pct: PctFloat | None = None
    avg_rr: FiniteFloat | None = None
    max_dd_pct: PctFloat | None = None
    median_24m_net_vnd: FiniteFloat | None = None
    median_36m_net_vnd: FiniteFloat | None = None
    median_36m_net_usd: FiniteFloat | None = None

    holdout_rows_analysed: Literal[0] = 0
    order_send_count: Literal[0] = 0

    @model_validator(mode="after")
    def _validate_phase_partitions(self) -> EvaluationInputRecord:
        if self.payout_1_cal_days is not None and self.payout_1_cal_days < 0.0:
            raise ValueError(f"payout_1_cal_days must be >= 0, got {self.payout_1_cal_days!r}")
        if self.slippage_breakeven_mult is not None and self.slippage_breakeven_mult < 0.0:
            raise ValueError(f"slippage_breakeven_mult must be >= 0, got {self.slippage_breakeven_mult!r}")
        for prefix in ("p1", "p2"):
            p = getattr(self, f"{prefix}_pass_rate_pct")
            f = getattr(self, f"{prefix}_fail_rate_pct")
            w = getattr(self, f"{prefix}_pending_rate_pct")
            if p is not None and f is not None and w is not None:
                if abs((p + f + w) - 100.0) > 1e-4:
                    raise ValueError(f"{prefix} partition must sum to 100.0, got {p + f + w:.6f}")
        return self


class EvaluationScorecard(StrictCatalogModel):
    """Canonical Evaluation Scorecard contract (matches `UI/contracts/evaluation-scorecard/1.0.0/schema.json`)."""

    schema_version: Literal["naqex-evaluation-scorecard-v1"] = "naqex-evaluation-scorecard-v1"
    contract_version: Literal["1.0.0"] = "1.0.0"
    taxonomy_version: NonEmptyText
    taxonomy_sha256: Sha256Hex
    record_id: NonEmptyText
    domain_tier: DomainTier
    eval_scope: EvalScope
    pricing_regime: PricingRegime
    evidence_stage: EvidenceStage
    data_resolution: DataResolution
    resolution_label_vi: NonEmptyText
    execution_status: NonEmptyText
    risk_spectrum_tier: RiskSpectrumTier | None = None
    legacy_grade_code: NonEmptyText | None = None
    unified_grade_code: GradeBand
    overall_grade: GradeBand
    overall_grade_vi: NonEmptyText
    presentation_state: PresentationState
    phase_grades: dict[ScorecardPhaseKey, PhaseGradeDetail]
    metric_grades: dict[str, GradeBand]
    metric_pass_map: dict[str, bool]
    exact_bottlenecks: tuple[BottleneckItem, ...]
    monthly_pass_fail_pending: dict[str, HorizonPartitionPct] | None = None
    gap_to_top_1_pct_vi: NonEmptyText
    holdout_rows_analysed: Literal[0] = 0
    order_send_count: Literal[0] = 0
    execution_capability: Literal[False] = False

    @model_validator(mode="after")
    def _validate_scorecard_invariants(self) -> EvaluationScorecard:
        if self.unified_grade_code != self.overall_grade:
            raise ValueError("unified_grade_code must equal overall_grade")
        required_phases: set[ScorecardPhaseKey] = {"p1", "p2", "pass_eval", "funded_12m"}
        if set(self.phase_grades.keys()) != required_phases:
            raise ValueError(f"phase_grades must contain exact keys {sorted(required_phases)}")
        for ph_key, detail in self.phase_grades.items():
            if detail.phase != ph_key:
                raise ValueError(f"phase_grades[{ph_key!r}].phase={detail.phase!r} mismatch")
        if self.overall_grade == "UNKNOWN_LEGACY_UNINSTRUMENTED":
            if self.presentation_state.certainty != "unknown" or not self.presentation_state.label:
                raise ValueError("overall_grade UNKNOWN requires certainty='unknown' and label")
        return self


def export_scorecard_json_schema() -> dict[str, Any]:
    """Export canonical JSON Schema Draft 2020-12 directly from Pydantic v2 `EvaluationScorecard`."""
    schema = EvaluationScorecard.model_json_schema(mode="validation")
    ordered: dict[str, Any] = {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        "$id": SCORECARD_SCHEMA_ID,
        "title": "Naqex Evaluation Scorecard Contract 1.0.0",
        "description": (
            "Candidate trading-domain UI & backend scorecard contract binding SSOT evaluation taxonomy, "
            "per-phase grades (p1, p2, pass_eval, funded_12m), presentation-state@1.0.0 semantics, "
            "and ordered plain-Vietnamese bottlenecks."
        ),
    }
    for k, v in schema.items():
        if k not in ("title", "description"):
            ordered[k] = v
    return ordered


# ---------------------------------------------------------------------------
# Single Canonical Grader: `grade_evaluation_record(...)`
# ---------------------------------------------------------------------------


def _format_num_vi(value: float | None, unit: str) -> str:
    if value is None:
        return "chưa có"
    if unit == "percent":
        return f"{value:.2f}%"
    if unit == "multiple":
        return f"{value:.2f}x"
    if unit == "cal_days":
        return f"{value:.1f} ngày"
    return f"{value:.2f}"


def _build_bottleneck_label(
    base_label_vi: str,
    *,
    current_value: float | None,
    target_threshold: float | None,
    unit: str,
    direction: MetricDirection,
    target_grade_vi: str,
) -> str:
    if current_value is None or target_threshold is None:
        return base_label_vi
    cmp_sym = ">=" if direction == "higher_is_better" else "<"
    return (
        f"{base_label_vi}: hiện tại {_format_num_vi(current_value, unit)}, "
        f"cần {cmp_sym} {_format_num_vi(target_threshold, unit)} để đạt {target_grade_vi}."
    )


def _resolve_pass_eval_metric(rec: EvaluationInputRecord) -> tuple[float | None, float | None, float | None]:
    if rec.pass_eval_12m_pct is not None:
        return rec.pass_eval_12m_pct, None, None
    hmap = (
        rec.first_ticket_pass_fail_pending
        if rec.eval_scope == "SINGLE_TICKET" and rec.first_ticket_pass_fail_pending
        else rec.monthly_pass_fail_pending
    )
    if hmap and "12m" in hmap:
        p12 = hmap["12m"]
        return p12.pass_pct, p12.fail_pct, p12.pending_pct
    if rec.pass_eval_36m_pct is not None:
        return rec.pass_eval_36m_pct, None, None
    return None, None, None


def grade_evaluation_record(
    record: EvaluationInputRecord | Mapping[str, Any],
    *,
    taxonomy: EvaluationTaxonomyConfig | None = None,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
) -> EvaluationScorecard:
    """Single canonical grader emitting overall_grade, phase_grades, metric_pass_map, and exact_bottlenecks[]."""
    if taxonomy is None:
        cfg, tax_sha = load_evaluation_taxonomy(taxonomy_path)
    else:
        cfg = taxonomy
        tax_sha = taxonomy.fingerprint()

    rec = record if isinstance(record, EvaluationInputRecord) else EvaluationInputRecord.model_validate(record)
    tier_spec = cfg.domain_tier_thresholds[rec.domain_tier]

    # 1. Classify every present metric using the continuous half-open intervals
    metric_grades: dict[str, GradeBand] = {}
    metric_pass_map: dict[str, bool] = {}
    for mid, mspec in cfg.metric_intervals.items():
        val = getattr(rec, mspec.record_field, None)
        if val is None:
            continue
        band = mspec.classify(val)
        metric_grades[mid] = band
        metric_pass_map[mid] = GRADE_RANK[band] >= GRADE_RANK["GOOD"]

    # 2. Evaluate all 4 scorecard phases (`p1`, `p2`, `pass_eval`, `funded_12m`)
    phase_grades: dict[ScorecardPhaseKey, PhaseGradeDetail] = {}
    collected_bottlenecks: list[tuple[int, float, BottleneckItem]] = []

    def _next_target_for_threshold(
        thr: PhaseMetricThreshold,
        cur_grade: NumericGradeBand,
    ) -> tuple[NumericGradeBand, float]:
        if cur_grade == "BAD":
            return "GOOD", thr.good
        if cur_grade == "ADEQUATE":
            return "GOOD", thr.good
        return "TOP_1_PCT", thr.top_1

    def _deficit_ratio(thr: PhaseMetricThreshold, cur_val: float, target_val: float) -> float:
        denom = max(abs(target_val), 1.0)
        if thr.direction == "higher_is_better":
            return max(0.0, (target_val - cur_val) / denom)
        return max(0.0, (cur_val - target_val) / denom)

    def _grade_phase(phase_key: ScorecardPhaseKey) -> PhaseGradeDetail:
        pspec = tier_spec.phases[phase_key]
        if not pspec.applicable:
            na_label = f"Không áp dụng pha {phase_key} cho tầng {tier_spec.label_vi}"
            return PhaseGradeDetail(
                phase=phase_key,
                grade="UNKNOWN_LEGACY_UNINSTRUMENTED",
                grade_vi=GRADE_LABEL_VI["UNKNOWN_LEGACY_UNINSTRUMENTED"],
                presentation_state=PresentationState(
                    availability="ready",
                    freshness="partial",
                    certainty="unknown",
                    label=na_label,
                    ariaLabel=na_label,
                ),
            )

        p_rate: float | None = None
        f_rate: float | None = None
        w_rate: float | None = None
        if phase_key == "p1":
            p_rate, f_rate, w_rate = rec.p1_pass_rate_pct, rec.p1_fail_rate_pct, rec.p1_pending_rate_pct
        elif phase_key == "p2":
            p_rate, f_rate, w_rate = rec.p2_pass_rate_pct, rec.p2_fail_rate_pct, rec.p2_pending_rate_pct
        elif phase_key == "pass_eval":
            p_rate, f_rate, w_rate = _resolve_pass_eval_metric(rec)

        ph_metric_grades: dict[str, GradeBand] = {}
        ph_bns: list[BottleneckItem] = []
        ranks: list[int] = []

        for mkey, mthr in pspec.metrics.items():
            if phase_key == "pass_eval" and mkey == "pass_eval_rate":
                mval = p_rate
            else:
                mval = getattr(rec, mthr.record_field, None)
            if mval is None:
                continue
            g = mthr.classify(mval)
            ph_metric_grades[mkey] = g
            metric_pass_map[f"{phase_key}.{mkey}"] = GRADE_RANK[g] >= GRADE_RANK["GOOD"]
            ranks.append(GRADE_RANK[g])
            if g != "TOP_1_PCT":
                tgt_grade, tgt_val = _next_target_for_threshold(mthr, g)
                base_vi = str(cfg.bottleneck_catalog[mthr.bottleneck_code]["label_vi"])
                bn = BottleneckItem(
                    code=mthr.bottleneck_code,
                    metric_id=mkey,
                    phase=phase_key,
                    current_value=round(float(mval), 6),
                    target_threshold=round(float(tgt_val), 6),
                    target_grade=tgt_grade,
                    severity_rank=1,
                    label_vi=_build_bottleneck_label(
                        base_vi,
                        current_value=float(mval),
                        target_threshold=float(tgt_val),
                        unit=mthr.unit,
                        direction=mthr.direction,
                        target_grade_vi=GRADE_LABEL_VI[tgt_grade],
                    ),
                )
                ph_bns.append(bn)
                collected_bottlenecks.append((GRADE_RANK[g], -_deficit_ratio(mthr, float(mval), float(tgt_val)), bn))

        if not ranks:
            # Missing phase instrumentation -> explicit presentation-state@1.0.0 UNKNOWN (never numeric 0!)
            if phase_key in ("p1", "p2"):
                pstate = cfg.legacy_uninstrumented_presentation_state
            else:
                lbl = f"Thiếu dữ liệu đo pha {phase_key}"
                pstate = PresentationState(
                    availability="ready",
                    freshness="partial",
                    certainty="unknown",
                    label=lbl,
                    ariaLabel=lbl,
                )
            return PhaseGradeDetail(
                phase=phase_key,
                grade="UNKNOWN_LEGACY_UNINSTRUMENTED",
                grade_vi=GRADE_LABEL_VI["UNKNOWN_LEGACY_UNINSTRUMENTED"],
                presentation_state=pstate,
                metric_grades={},
                pass_rate_pct=p_rate,
                fail_rate_pct=f_rate,
                pending_rate_pct=w_rate,
                bottlenecks=(),
            )

        worst_rank = min(ranks)
        ph_grade: NumericGradeBand = RANK_TO_GRADE[worst_rank]
        ph_freshness: Literal["current", "partial"] = "partial" if rec.data_resolution == "APPROX_DAILY" else "current"
        ph_certainty: Literal["known", "uncertain"] = (
            "uncertain"
            if rec.evidence_stage in ("DEV_IS", "DEV_CONSUMED_OOS")
            or rec.execution_status == "TERMS_VERIFIED_EXECUTION_UNMEASURED"
            else "known"
        )
        ph_label = f"{phase_key.upper()}: {GRADE_LABEL_VI[ph_grade]}"
        if ph_freshness == "partial":
            ph_label = f"{ph_label} ({cfg.data_resolution_specs[rec.data_resolution]['label_vi']})"
        return PhaseGradeDetail(
            phase=phase_key,
            grade=ph_grade,
            grade_vi=GRADE_LABEL_VI[ph_grade],
            presentation_state=PresentationState(
                availability="ready",
                freshness=ph_freshness,
                certainty=ph_certainty,
                label=ph_label,
                ariaLabel=ph_label,
            ),
            metric_grades=ph_metric_grades,
            pass_rate_pct=p_rate,
            fail_rate_pct=f_rate,
            pending_rate_pct=w_rate,
            bottlenecks=tuple(ph_bns),
        )

    for pk in ("p1", "p2", "pass_eval", "funded_12m"):
        phase_grades[pk] = _grade_phase(pk)

    # 3. Grade `overall_36m` (drives `overall_grade` / `unified_grade_code`)
    overall_spec = tier_spec.phases["overall_36m"]
    overall_ranks: list[int] = []
    seen_overall_keys: set[tuple[str, str]] = set()
    for mkey, mthr in overall_spec.metrics.items():
        # In SINGLE_TICKET scope, fleet bankroll ruin_36m is optional if omitted
        mval = getattr(rec, mthr.record_field, None)
        if mval is None:
            continue
        g = mthr.classify(mval)
        metric_pass_map[mkey] = GRADE_RANK[g] >= GRADE_RANK["GOOD"]
        metric_pass_map[f"overall_36m.{mkey}"] = GRADE_RANK[g] >= GRADE_RANK["GOOD"]
        overall_ranks.append(GRADE_RANK[g])
        if g != "TOP_1_PCT":
            tgt_grade, tgt_val = _next_target_for_threshold(mthr, g)
            base_vi = str(cfg.bottleneck_catalog[mthr.bottleneck_code]["label_vi"])
            bn = BottleneckItem(
                code=mthr.bottleneck_code,
                metric_id=mkey,
                phase="overall_36m",
                current_value=round(float(mval), 6),
                target_threshold=round(float(tgt_val), 6),
                target_grade=tgt_grade,
                severity_rank=1,
                label_vi=_build_bottleneck_label(
                    base_vi,
                    current_value=float(mval),
                    target_threshold=float(tgt_val),
                    unit=mthr.unit,
                    direction=mthr.direction,
                    target_grade_vi=GRADE_LABEL_VI[tgt_grade],
                ),
            )
            key_sig = (bn.code, bn.metric_id)
            if key_sig not in seen_overall_keys:
                seen_overall_keys.add(key_sig)
                collected_bottlenecks.append((GRADE_RANK[g], -_deficit_ratio(mthr, float(mval), float(tgt_val)), bn))

    # Fallback if overall_36m metrics were not supplied (e.g. pure strategy quality record)
    if not overall_ranks and metric_grades:
        for mid, g in metric_grades.items():
            if g == "UNKNOWN_LEGACY_UNINSTRUMENTED":
                continue
            overall_ranks.append(GRADE_RANK[g])
            if g != "TOP_1_PCT":
                mspec = cfg.metric_intervals[mid]
                tgt_grade: NumericGradeBand = "GOOD" if GRADE_RANK[g] < GRADE_RANK["GOOD"] else "TOP_1_PCT"
                tgt_val = mspec.target_for_grade(tgt_grade)
                cur_val = getattr(rec, mspec.record_field, None)
                base_vi = str(cfg.bottleneck_catalog[mspec.bottleneck_code]["label_vi"])
                bn = BottleneckItem(
                    code=mspec.bottleneck_code,
                    metric_id=mid,
                    phase="overall_36m",
                    current_value=round(float(cur_val), 6) if cur_val is not None else None,
                    target_threshold=round(float(tgt_val), 6) if tgt_val is not None else None,
                    target_grade=tgt_grade,
                    severity_rank=1,
                    label_vi=_build_bottleneck_label(
                        base_vi,
                        current_value=float(cur_val) if cur_val is not None else None,
                        target_threshold=float(tgt_val) if tgt_val is not None else None,
                        unit=mspec.unit,
                        direction=mspec.direction,
                        target_grade_vi=GRADE_LABEL_VI[tgt_grade],
                    ),
                )
                collected_bottlenecks.append((GRADE_RANK[g], 0.0, bn))

    # Also collect non-blocking caveats (Dev-only, Unmeasured Demo, Promo assumption, Approx Daily) at tail
    caveat_items: list[BottleneckItem] = []
    if rec.execution_status == "TERMS_VERIFIED_EXECUTION_UNMEASURED":
        caveat_items.append(
            BottleneckItem(
                code="EXECUTION_UNMEASURED_DEMO",
                metric_id="execution_status",
                phase="overall_36m",
                current_value=None,
                target_threshold=None,
                target_grade="TOP_1_PCT",
                severity_rank=1,
                label_vi=str(cfg.bottleneck_catalog["EXECUTION_UNMEASURED_DEMO"]["label_vi"]),
            )
        )
    if rec.pricing_regime == "BLACK_FRIDAY_PROMO":
        caveat_items.append(
            BottleneckItem(
                code="PRICING_PROMO_ASSUMPTION",
                metric_id="pricing_regime",
                phase="overall_36m",
                current_value=None,
                target_threshold=None,
                target_grade="TOP_1_PCT",
                severity_rank=1,
                label_vi=str(cfg.bottleneck_catalog["PRICING_PROMO_ASSUMPTION"]["label_vi"]),
            )
        )
    if rec.evidence_stage != "LIVE_REAL":
        caveat_items.append(
            BottleneckItem(
                code="EVIDENCE_STAGE_DEV_ONLY",
                metric_id="evidence_stage",
                phase="overall_36m",
                current_value=None,
                target_threshold=None,
                target_grade="TOP_1_PCT",
                severity_rank=1,
                label_vi=str(cfg.bottleneck_catalog["EVIDENCE_STAGE_DEV_ONLY"]["label_vi"]),
            )
        )

    # Deduplicate numeric bottlenecks by (code, metric_id) keeping worst severity, then sort deterministically
    best_by_key: dict[tuple[str, str], tuple[int, float, BottleneckItem]] = {}
    for item in collected_bottlenecks:
        k = (item[2].code, item[2].metric_id)
        prev = best_by_key.get(k)
        if prev is None or (item[0], item[1]) < (prev[0], prev[1]):
            best_by_key[k] = item

    sorted_numeric = sorted(
        best_by_key.values(),
        key=lambda t: (t[0], t[1], t[2].code, t[2].phase, t[2].metric_id),
    )
    ordered_bottlenecks: list[BottleneckItem] = []
    for idx, (_rk, _def, bn) in enumerate(sorted_numeric, start=1):
        ordered_bottlenecks.append(bn.model_copy(update={"severity_rank": idx}))
    for cav in caveat_items:
        ordered_bottlenecks.append(cav.model_copy(update={"severity_rank": len(ordered_bottlenecks) + 1}))

    if overall_ranks:
        overall_grade: GradeBand = RANK_TO_GRADE[min(overall_ranks)]
    else:
        overall_grade = "UNKNOWN_LEGACY_UNINSTRUMENTED"

    res_label_vi = str(cfg.data_resolution_specs[rec.data_resolution]["label_vi"])
    overall_grade_vi = GRADE_LABEL_VI[overall_grade]

    if overall_grade == "UNKNOWN_LEGACY_UNINSTRUMENTED":
        ov_state = PresentationState(
            availability="ready",
            freshness="partial",
            certainty="unknown",
            label="Chưa đủ chỉ số để chấm điểm tổng thể",
            ariaLabel="Chưa đủ chỉ số để chấm điểm tổng thể",
        )
    else:
        ov_freshness: Literal["current", "partial"] = "partial" if rec.data_resolution == "APPROX_DAILY" else "current"
        ov_certainty: Literal["known", "uncertain"] = (
            "uncertain"
            if rec.evidence_stage != "LIVE_REAL" or rec.execution_status == "TERMS_VERIFIED_EXECUTION_UNMEASURED"
            else "known"
        )
        ov_label = f"{overall_grade_vi} · {res_label_vi} · {cfg.evidence_stage_specs[rec.evidence_stage]['label_vi']}"
        ov_state = PresentationState(
            availability="ready",
            freshness=ov_freshness,
            certainty=ov_certainty,
            label=ov_label,
            ariaLabel=ov_label,
        )

    if overall_grade == "TOP_1_PCT" and rec.evidence_stage == "LIVE_REAL":
        gap_vi = "Đã đạt chuẩn Top 1% thực tế trên dữ liệu tiền thật."
    elif ordered_bottlenecks:
        top_gaps = "; ".join(bn.label_vi for bn in ordered_bottlenecks[:3])
        gap_vi = f"Nút thắt chính tới Top 1%: {top_gaps}"
    else:
        gap_vi = "Đạt chuẩn Top 1% trên mô phỏng Dev; cần xác minh thêm bằng Holdout mù và Demo/Live."

    return EvaluationScorecard(
        taxonomy_version=cfg.schema_version,
        taxonomy_sha256=tax_sha,
        record_id=rec.record_id,
        domain_tier=rec.domain_tier,
        eval_scope=rec.eval_scope,
        pricing_regime=rec.pricing_regime,
        evidence_stage=rec.evidence_stage,
        data_resolution=rec.data_resolution,
        resolution_label_vi=res_label_vi,
        execution_status=rec.execution_status,
        risk_spectrum_tier=rec.risk_spectrum_tier,
        legacy_grade_code=rec.legacy_grade_code,
        unified_grade_code=overall_grade,
        overall_grade=overall_grade,
        overall_grade_vi=overall_grade_vi,
        presentation_state=ov_state,
        phase_grades=phase_grades,
        metric_grades=metric_grades,
        metric_pass_map=metric_pass_map,
        exact_bottlenecks=tuple(ordered_bottlenecks),
        monthly_pass_fail_pending=rec.monthly_pass_fail_pending,
        gap_to_top_1_pct_vi=gap_vi,
        holdout_rows_analysed=0,
        order_send_count=0,
        execution_capability=False,
    )


# ---------------------------------------------------------------------------
# Federated Unified DuckDB Catalog + SQLiteRunRegistry Hash Chain
# ---------------------------------------------------------------------------


def _import_duckdb() -> Any:
    import duckdb  # lazy import so Pydantic models & grader work even without duckdb

    return duckdb


def _close_con_box(box: list[Any]) -> None:
    con = box[0]
    box[0] = None
    if con is not None:
        try:
            con.close()
        except Exception:
            pass


_CATALOG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs_catalog (
    run_id VARCHAR PRIMARY KEY,
    strategy_id VARCHAR NOT NULL,
    wave_tag VARCHAR NOT NULL,
    domain_tier VARCHAR NOT NULL,
    eval_scope VARCHAR NOT NULL,
    pricing_regime VARCHAR NOT NULL,
    evidence_stage VARCHAR NOT NULL,
    data_resolution VARCHAR NOT NULL,
    execution_status VARCHAR NOT NULL,
    risk_spectrum_tier VARCHAR,
    profile_id VARCHAR,
    funded_mult DOUBLE,
    friction_mult DOUBLE,
    legacy_grade_code VARCHAR,
    unified_grade_code VARCHAR NOT NULL,
    p1_grade VARCHAR NOT NULL,
    p2_grade VARCHAR NOT NULL,
    pass_eval_grade VARCHAR NOT NULL,
    funded_12m_grade VARCHAR NOT NULL,
    profit_factor DOUBLE,
    calmar DOUBLE,
    sharpe DOUBLE,
    ev_per_fee DOUBLE,
    funded_12m_blowup_pct DOUBLE,
    ruin_36m_pct DOUBLE,
    p_le_zero_24m_pct DOUBLE,
    payout_1_cal_days DOUBLE,
    slippage_breakeven_mult DOUBLE,
    metric_pass_map_json VARCHAR NOT NULL,
    exact_bottlenecks_json VARCHAR NOT NULL,
    scorecard_json VARCHAR NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    order_send_count INTEGER NOT NULL,
    created_utc VARCHAR NOT NULL,
    record_sha256 VARCHAR NOT NULL,
    registry_event_hash VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS mc_cases_catalog (
    case_key VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    campaign_id VARCHAR NOT NULL DEFAULT 'offensive4',
    source_cohort VARCHAR NOT NULL,
    case_id VARCHAR NOT NULL,
    firm_group VARCHAR NOT NULL,
    contract_id VARCHAR,
    profile_id VARCHAR NOT NULL,
    funded_mult DOUBLE NOT NULL,
    friction_mult DOUBLE NOT NULL,
    bankroll_m_vnd INTEGER NOT NULL,
    bankroll_usd DOUBLE NOT NULL,
    concurrency_mode VARCHAR NOT NULL,
    allocation_policy VARCHAR NOT NULL,
    domain_tier VARCHAR NOT NULL,
    eval_scope VARCHAR NOT NULL,
    pricing_regime VARCHAR NOT NULL,
    evidence_stage VARCHAR NOT NULL,
    data_resolution VARCHAR NOT NULL,
    resolution_label_vi VARCHAR NOT NULL,
    execution_status VARCHAR NOT NULL,
    n_paths INTEGER NOT NULL,
    horizon_days INTEGER NOT NULL,
    is_pareto_in_tier BOOLEAN NOT NULL,
    is_pareto_overall BOOLEAN NOT NULL,
    median_24m_net_vnd DOUBLE NOT NULL,
    median_36m_net_vnd DOUBLE NOT NULL,
    median_36m_net_usd DOUBLE NOT NULL,
    mean_36m_net_vnd DOUBLE NOT NULL,
    ev_per_1_vnd_fee_24m DOUBLE NOT NULL,
    ev_per_1_vnd_fee_36m DOUBLE NOT NULL,
    p_net_le_0_24m_pct DOUBLE NOT NULL,
    p_net_le_0_36m_pct DOUBLE NOT NULL,
    p_bankroll_ruin_24m_pct DOUBLE NOT NULL,
    p_bankroll_ruin_pct DOUBLE NOT NULL,
    funded_12m_blowup_pct DOUBLE NOT NULL,
    funded_12m_wilson_95_ub_pct DOUBLE NOT NULL,
    uncond_med_pay1_cal_days_cap365 DOUBLE NOT NULL,
    uncond_med_pay1_cal_days_cap730 DOUBLE NOT NULL,
    pass_12m_pct DOUBLE NOT NULL,
    fail_12m_pct DOUBLE NOT NULL,
    pending_12m_pct DOUBLE NOT NULL,
    pass_36m_pct DOUBLE NOT NULL,
    fail_36m_pct DOUBLE NOT NULL,
    pending_36m_pct DOUBLE NOT NULL,
    strategy_pf DOUBLE,
    strategy_calmar DOUBLE,
    strategy_sharpe DOUBLE,
    strategy_winrate_pct DOUBLE,
    strategy_avg_rr DOUBLE,
    strategy_ev_r DOUBLE,
    legacy_grade_code VARCHAR NOT NULL,
    unified_grade_code VARCHAR NOT NULL,
    p1_grade VARCHAR NOT NULL,
    p2_grade VARCHAR NOT NULL,
    pass_eval_grade VARCHAR NOT NULL,
    funded_12m_grade VARCHAR NOT NULL,
    p1_presentation_state_json VARCHAR NOT NULL,
    p2_presentation_state_json VARCHAR NOT NULL,
    metric_pass_map_json VARCHAR NOT NULL,
    exact_bottlenecks_json VARCHAR NOT NULL,
    scorecard_json VARCHAR NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    order_send_count INTEGER NOT NULL,
    source_artifact_sha256 VARCHAR NOT NULL,
    created_utc VARCHAR NOT NULL,
    record_sha256 VARCHAR NOT NULL,
    registry_event_hash VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS alpha_registry_catalog (
    alpha_id VARCHAR PRIMARY KEY,
    family_id VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    leader_symbol VARCHAR,
    lifecycle_state VARCHAR NOT NULL,
    blindness_tier VARCHAR NOT NULL,
    mt5_hcc_ready BOOLEAN NOT NULL,
    evidence_stage VARCHAR NOT NULL,
    data_resolution VARCHAR NOT NULL,
    cluster_a_sharpe DOUBLE,
    cluster_b_sharpe DOUBLE,
    profit_factor DOUBLE,
    calmar DOUBLE,
    slippage_breakeven_mult DOUBLE,
    corr_vs_7e DOUBLE,
    tail_corr_vs_7e DOUBLE,
    unified_grade_code VARCHAR NOT NULL,
    scorecard_json VARCHAR NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    order_send_count INTEGER NOT NULL,
    updated_utc VARCHAR NOT NULL,
    record_sha256 VARCHAR NOT NULL,
    registry_event_hash VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS _legacy_trials_ingested (
    trial_uid VARCHAR PRIMARY KEY,
    source_key VARCHAR NOT NULL,
    source_db VARCHAR NOT NULL,
    source_table VARCHAR NOT NULL,
    legacy_id VARCHAR NOT NULL,
    family_id VARCHAR NOT NULL,
    strategy_id VARCHAR NOT NULL,
    sharpe DOUBLE,
    profit_factor DOUBLE,
    max_dd_pct DOUBLE,
    p_value DOUBLE,
    verdict VARCHAR,
    evidence_stage VARCHAR NOT NULL,
    holdout_rows_analysed INTEGER NOT NULL,
    created_utc VARCHAR NOT NULL,
    source_db_sha256 VARCHAR NOT NULL
);

CREATE OR REPLACE VIEW legacy_trials_federated_view AS
SELECT
    trial_uid,
    source_key,
    source_db,
    source_table,
    legacy_id,
    family_id,
    strategy_id,
    sharpe,
    profit_factor,
    max_dd_pct,
    p_value,
    verdict,
    evidence_stage,
    holdout_rows_analysed,
    created_utc,
    source_db_sha256
FROM _legacy_trials_ingested;
"""


class AlphaRegistryEntry(StrictCatalogModel):
    """Validated record for `alpha_registry_catalog`."""

    alpha_id: NonEmptyText
    family_id: NonEmptyText
    symbol: NonEmptyText
    leader_symbol: NonEmptyText | None = None
    lifecycle_state: AlphaLifecycleState
    raw_blindness_tier: NonEmptyText
    mt5_hcc_ready: bool
    evidence_stage: EvidenceStage = "DEV_BLIND_OOS"
    data_resolution: DataResolution = "M1_BID_SPREAD"
    cluster_a_sharpe: FiniteFloat | None = None
    cluster_b_sharpe: FiniteFloat | None = None
    profit_factor: FiniteFloat | None = None
    calmar: FiniteFloat | None = None
    slippage_breakeven_mult: FiniteFloat | None = None
    corr_vs_7e: FiniteFloat | None = None
    tail_corr_vs_7e: FiniteFloat | None = None
    holdout_rows_analysed: Literal[0] = 0
    order_send_count: Literal[0] = 0


def _extract_wave4_ssot_context(payload: Mapping[str, Any]) -> tuple[str, float, dict[str, Any]]:
    """Extract `profile_id` and `funded_mult` strictly from `ssot_provenance` / `sku_funded_diagnostics_1_0x`."""
    prov = payload.get("ssot_provenance")
    if not isinstance(prov, Mapping):
        raise ValueError("Wave 4 Pareto artifact missing ssot_provenance")
    profile_id = _validate_non_empty_text(prov.get("profile_id"))
    raw_fm = prov.get("funded_mult")
    sku_diags = payload.get("sku_funded_diagnostics_1_0x")
    if raw_fm is None and isinstance(sku_diags, Mapping) and sku_diags:
        first_diag = next(iter(sku_diags.values()))
        if isinstance(first_diag, Mapping):
            raw_fm = first_diag.get("funded_mult")
    funded_mult = _reject_bool_and_coerce_finite_float(raw_fm)
    if funded_mult <= 0.0:
        raise ValueError(f"funded_mult must be > 0, got {funded_mult!r}")
    if isinstance(sku_diags, Mapping):
        for sku_id, diag in sku_diags.items():
            if isinstance(diag, Mapping) and "funded_mult" in diag:
                d_fm = _reject_bool_and_coerce_finite_float(diag["funded_mult"])
                if not math.isclose(d_fm, funded_mult, rel_tol=1e-9, abs_tol=1e-9):
                    raise ValueError(
                        f"funded_mult mismatch between ssot_provenance ({funded_mult}) and {sku_id} ({d_fm})"
                    )
    ref_sku_diag: dict[str, Any] = {}
    if isinstance(sku_diags, Mapping):
        cand = sku_diags.get("ftmo_standard_100k") or (next(iter(sku_diags.values())) if sku_diags else {})
        if isinstance(cand, Mapping):
            ref_sku_diag = dict(cand)
    return profile_id, funded_mult, ref_sku_diag


def _parse_horizon_map(raw_map: Any) -> dict[str, HorizonPartitionPct]:
    if not isinstance(raw_map, Mapping):
        raise ValueError("monthly_pass_fail_pending must be a mapping")
    out: dict[str, HorizonPartitionPct] = {}
    for hkey, part in raw_map.items():
        if not isinstance(part, Mapping):
            raise ValueError(f"horizon {hkey!r} must be a mapping")
        out[str(hkey)] = HorizonPartitionPct(
            pass_pct=part["pass_pct"],
            fail_pct=part["fail_pct"],
            pending_pct=part["pending_pct"],
        )
    return out


def _case_to_mc_row(
    case: Mapping[str, Any],
    *,
    source_cohort: str,
    firm_group: str,
    profile_id: str,
    funded_mult: float,
    default_friction_mult: float,
    ref_sku_diag: Mapping[str, Any],
    taxonomy: EvaluationTaxonomyConfig,
    source_artifact_sha256: str,
    run_id: str,
    created_utc: str,
) -> dict[str, Any]:
    if case.get("holdout_rows_analysed") != 0 or isinstance(case.get("holdout_rows_analysed"), bool):
        raise ValueError(f"HOLDOUT_VIOLATION in case {case.get('case_id')!r}")
    if case.get("order_send_count") != 0 or isinstance(case.get("order_send_count"), bool):
        raise ValueError(f"ORDER_SEND_VIOLATION in case {case.get('case_id')!r}")

    case_id = _validate_non_empty_text(case.get("case_id"))
    case_key = f"{source_cohort.lower()}::{case_id}"
    friction_mult = _reject_bool_and_coerce_finite_float(case.get("friction_mult", default_friction_mult))

    raw_stage = str(case.get("evidence_stage") or "BACKTEST_DEV_SEALED_LE_2024")
    evidence_stage = taxonomy.legacy_evidence_stage_mapping.get(raw_stage)
    if evidence_stage is None:
        raise ValueError(f"UNKNOWN_LEGACY_EVIDENCE_STAGE: {raw_stage!r}")

    raw_res = str(case.get("resolution_tag") or "APPROX_DAILY_RESOLUTION")
    data_resolution = taxonomy.legacy_resolution_mapping.get(raw_res)
    if data_resolution is None:
        raise ValueError(f"UNKNOWN_LEGACY_RESOLUTION: {raw_res!r}")

    raw_pricing = str(case.get("pricing_regime") or "ALL_REGULAR_SSOT")
    pricing_regime = taxonomy.legacy_pricing_regime_mapping.get(raw_pricing)
    if pricing_regime is None:
        raise ValueError(f"UNKNOWN_LEGACY_PRICING_REGIME: {raw_pricing!r}")

    monthly_map = _parse_horizon_map(case.get("monthly_pass_fail_pending"))
    first_ticket_map = (
        _parse_horizon_map(case.get("first_ticket_pass_fail_pending"))
        if isinstance(case.get("first_ticket_pass_fail_pending"), Mapping)
        else None
    )
    if "12m" not in monthly_map or "36m" not in monthly_map:
        raise ValueError(f"case {case_id} missing 12m/36m horizon partitions")

    fn12 = case.get("funded_12m_blowup")
    if not isinstance(fn12, Mapping):
        raise ValueError(f"case {case_id} missing funded_12m_blowup")
    blowup_12m = _reject_bool_and_coerce_finite_float(fn12.get("blowup_12m_pct"))
    wilson_ub = _reject_bool_and_coerce_finite_float(fn12.get("wilson_95_ub_pct"))

    sq = case.get("strategy_quality") if isinstance(case.get("strategy_quality"), Mapping) else {}
    if not sq and ref_sku_diag:
        sq = ref_sku_diag

    raw_legacy_grade = str((case.get("law15_position") or {}).get("grade_code") or "UNKNOWN")
    if raw_legacy_grade not in taxonomy.legacy_grade_mapping:
        raise ValueError(f"UNKNOWN_LEGACY_GRADE_CODE: {raw_legacy_grade!r} in case {case_id!r}")

    pf_val = _reject_bool_and_coerce_finite_float(sq["profit_factor"]) if sq.get("profit_factor") is not None else None
    calmar_val = _reject_bool_and_coerce_finite_float(sq["calmar"]) if sq.get("calmar") is not None else None
    sharpe_val = _reject_bool_and_coerce_finite_float(sq["sharpe"]) if sq.get("sharpe") is not None else None
    wr_val = _reject_bool_and_coerce_finite_float(sq["winrate_pct"]) if sq.get("winrate_pct") is not None else None
    rr_val = _reject_bool_and_coerce_finite_float(sq["avg_rr"]) if sq.get("avg_rr") is not None else None
    ev_r_val = (
        _reject_bool_and_coerce_finite_float(sq["ev_per_trade_r"]) if sq.get("ev_per_trade_r") is not None else None
    )

    ev_fee_36m = _reject_bool_and_coerce_finite_float(case.get("ev_per_1_vnd_fee_36m"))
    ev_fee_24m = _reject_bool_and_coerce_finite_float(case.get("ev_per_1_vnd_fee_24m"))
    ruin_36m = _reject_bool_and_coerce_finite_float(case.get("p_bankroll_ruin_pct"))
    ruin_24m = _reject_bool_and_coerce_finite_float(case.get("p_bankroll_ruin_24m_pct"))
    p_le_0_24m = _reject_bool_and_coerce_finite_float(case.get("p_net_le_0_24m_pct"))
    p_le_0_36m = _reject_bool_and_coerce_finite_float(case.get("p_net_le_0_36m_pct"))
    pay1_365 = _reject_bool_and_coerce_finite_float(case.get("uncond_med_pay1_cal_days_cap365"))
    pay1_730 = _reject_bool_and_coerce_finite_float(case.get("uncond_med_pay1_cal_days_cap730"))

    eval_input = EvaluationInputRecord(
        record_id=case_key,
        domain_tier="T1_CFD_PROP",
        eval_scope="MULTI_ACCOUNT_FLEET",
        pricing_regime=pricing_regime,
        evidence_stage=evidence_stage,
        data_resolution=data_resolution,
        execution_status=str(case.get("execution_status") or "MEASURED_DEMO_EXECUTION"),
        legacy_grade_code=raw_legacy_grade,
        profit_factor=pf_val,
        calmar=calmar_val,
        sharpe=sharpe_val,
        ev_per_fee=ev_fee_36m,
        funded_12m_blowup_pct=blowup_12m,
        ruin_36m_pct=ruin_36m,
        p_le_zero_24m_pct=p_le_0_24m,
        payout_1_cal_days=pay1_730,
        # Wave 4 legacy cases lack separate P1/P2 instrumentation -> strictly None -> UNKNOWN_LEGACY_UNINSTRUMENTED
        p1_pass_rate_pct=None,
        p2_pass_rate_pct=None,
        pass_eval_12m_pct=monthly_map["12m"].pass_pct,
        pass_eval_36m_pct=monthly_map["36m"].pass_pct,
        monthly_pass_fail_pending=monthly_map,
        first_ticket_pass_fail_pending=first_ticket_map,
        funded_12m_wilson_95_ub_pct=wilson_ub,
        ev_per_trade_r=ev_r_val,
        winrate_pct=wr_val,
        avg_rr=rr_val,
        median_24m_net_vnd=_reject_bool_and_coerce_finite_float(case.get("median_24m_net_vnd")),
        median_36m_net_vnd=_reject_bool_and_coerce_finite_float(case.get("median_36m_net_vnd")),
        median_36m_net_usd=_reject_bool_and_coerce_finite_float(case.get("median_36m_net_usd")),
        holdout_rows_analysed=0,
        order_send_count=0,
    )
    scorecard = grade_evaluation_record(eval_input, taxonomy=taxonomy)

    p1_detail = scorecard.phase_grades["p1"]
    p2_detail = scorecard.phase_grades["p2"]
    pass_detail = scorecard.phase_grades["pass_eval"]
    fn_detail = scorecard.phase_grades["funded_12m"]

    row_payload: dict[str, Any] = {
        "case_key": case_key,
        "run_id": run_id,
        "source_cohort": source_cohort,
        "case_id": case_id,
        "firm_group": firm_group,
        "contract_id": str(case["contract_id"]) if case.get("contract_id") is not None else None,
        "profile_id": profile_id,
        "funded_mult": funded_mult,
        "friction_mult": friction_mult,
        "bankroll_m_vnd": _validate_strict_int(case.get("bankroll_m_vnd")),
        "bankroll_usd": _reject_bool_and_coerce_finite_float(case.get("bankroll_usd")),
        "concurrency_mode": _validate_non_empty_text(case.get("concurrency_mode")),
        "allocation_policy": _validate_non_empty_text(case.get("allocation_policy")),
        "domain_tier": scorecard.domain_tier,
        "eval_scope": scorecard.eval_scope,
        "pricing_regime": scorecard.pricing_regime,
        "evidence_stage": scorecard.evidence_stage,
        "data_resolution": scorecard.data_resolution,
        "resolution_label_vi": scorecard.resolution_label_vi,
        "execution_status": scorecard.execution_status,
        "n_paths": _validate_strict_int(case.get("n_paths")),
        "horizon_days": _validate_strict_int(case.get("horizon_days")),
        "is_pareto_in_tier": bool(case.get("is_pareto_in_tier", False)),
        "is_pareto_overall": bool(case.get("is_pareto_overall", False)),
        "median_24m_net_vnd": _reject_bool_and_coerce_finite_float(case.get("median_24m_net_vnd")),
        "median_36m_net_vnd": _reject_bool_and_coerce_finite_float(case.get("median_36m_net_vnd")),
        "median_36m_net_usd": _reject_bool_and_coerce_finite_float(case.get("median_36m_net_usd")),
        "mean_36m_net_vnd": _reject_bool_and_coerce_finite_float(case.get("mean_36m_net_vnd")),
        "ev_per_1_vnd_fee_24m": ev_fee_24m,
        "ev_per_1_vnd_fee_36m": ev_fee_36m,
        "p_net_le_0_24m_pct": p_le_0_24m,
        "p_net_le_0_36m_pct": p_le_0_36m,
        "p_bankroll_ruin_24m_pct": ruin_24m,
        "p_bankroll_ruin_pct": ruin_36m,
        "funded_12m_blowup_pct": blowup_12m,
        "funded_12m_wilson_95_ub_pct": wilson_ub,
        "uncond_med_pay1_cal_days_cap365": pay1_365,
        "uncond_med_pay1_cal_days_cap730": pay1_730,
        "pass_12m_pct": monthly_map["12m"].pass_pct,
        "fail_12m_pct": monthly_map["12m"].fail_pct,
        "pending_12m_pct": monthly_map["12m"].pending_pct,
        "pass_36m_pct": monthly_map["36m"].pass_pct,
        "fail_36m_pct": monthly_map["36m"].fail_pct,
        "pending_36m_pct": monthly_map["36m"].pending_pct,
        "strategy_pf": pf_val,
        "strategy_calmar": calmar_val,
        "strategy_sharpe": sharpe_val,
        "strategy_winrate_pct": wr_val,
        "strategy_avg_rr": rr_val,
        "strategy_ev_r": ev_r_val,
        "legacy_grade_code": raw_legacy_grade,
        "unified_grade_code": scorecard.unified_grade_code,
        "p1_grade": p1_detail.grade,
        "p2_grade": p2_detail.grade,
        "pass_eval_grade": pass_detail.grade,
        "funded_12m_grade": fn_detail.grade,
        "p1_presentation_state_json": _canonical_json(p1_detail.presentation_state.model_dump(mode="json")),
        "p2_presentation_state_json": _canonical_json(p2_detail.presentation_state.model_dump(mode="json")),
        "metric_pass_map_json": _canonical_json(scorecard.metric_pass_map),
        "exact_bottlenecks_json": _canonical_json([b.model_dump(mode="json") for b in scorecard.exact_bottlenecks]),
        "scorecard_json": _canonical_json(scorecard.model_dump(mode="json")),
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "source_artifact_sha256": source_artifact_sha256,
        "created_utc": created_utc,
    }
    row_payload["record_sha256"] = _sha256_text(_canonical_json(row_payload))
    row_payload["campaign_id"] = "offensive4"
    return row_payload


def _wave5_case_to_mc_row(
    case: Mapping[str, Any],
    *,
    campaign_id: str,
    run_id: str,
    source_artifact_sha256: str,
    taxonomy: EvaluationTaxonomyConfig,
    created_utc: str,
) -> dict[str, Any]:
    """Validate, grade, and hash a Wave 5 instrumented MC case for `mc_cases_catalog`."""
    if case.get("holdout_rows_analysed", 0) != 0 or isinstance(case.get("holdout_rows_analysed", 0), bool):
        raise ValueError(f"HOLDOUT_VIOLATION in case {case.get('case_id')!r}")
    if case.get("order_send_count", 0) != 0 or isinstance(case.get("order_send_count", 0), bool):
        raise ValueError(f"ORDER_SEND_VIOLATION in case {case.get('case_id')!r}")

    case_id = _validate_non_empty_text(case.get("case_id"))
    source_cohort = _validate_non_empty_text(case.get("source_cohort"))
    case_key = str(case.get("case_key") or f"{campaign_id}::{source_cohort.lower()}::{case_id}")
    firm_group = _validate_non_empty_text(case.get("firm_group") or "FTMO")
    profile_id = _validate_non_empty_text(case.get("profile_id"))
    funded_mult = _reject_bool_and_coerce_finite_float(case.get("funded_mult"))
    friction_mult = _reject_bool_and_coerce_finite_float(case.get("friction_mult", 1.0))
    if funded_mult <= 0.0 or friction_mult <= 0.0:
        raise ValueError(f"funded_mult ({funded_mult}) and friction_mult ({friction_mult}) must be > 0")

    monthly_map = _parse_horizon_map(case.get("monthly_pass_fail_pending"))
    if "12m" not in monthly_map or "36m" not in monthly_map:
        raise ValueError(f"case {case_id} missing 12m/36m horizon partitions")
    first_ticket_map = (
        _parse_horizon_map(case.get("first_ticket_pass_fail_pending"))
        if isinstance(case.get("first_ticket_pass_fail_pending"), Mapping)
        else None
    )

    def _opt_float(key: str, src: Mapping[str, Any] = case) -> float | None:
        v = src.get(key)
        return _reject_bool_and_coerce_finite_float(v) if v is not None else None

    sq = case.get("strategy_quality") if isinstance(case.get("strategy_quality"), Mapping) else {}
    pf_val = _opt_float("profit_factor", sq) if "profit_factor" in sq else _opt_float("profit_factor")
    calmar_val = _opt_float("calmar", sq) if "calmar" in sq else _opt_float("calmar")
    sharpe_val = _opt_float("sharpe", sq) if "sharpe" in sq else _opt_float("sharpe")
    wr_val = _opt_float("winrate_pct", sq) if "winrate_pct" in sq else _opt_float("winrate_pct")
    rr_val = _opt_float("avg_rr", sq) if "avg_rr" in sq else _opt_float("avg_rr")
    ev_r_val = _opt_float("ev_per_trade_r", sq) if "ev_per_trade_r" in sq else _opt_float("ev_per_trade_r")
    max_dd_val = _opt_float("max_dd_pct", sq) if "max_dd_pct" in sq else _opt_float("max_dd_pct")
    slip_be_val = _opt_float("slippage_breakeven_mult")

    fn12 = case.get("funded_12m_blowup") if isinstance(case.get("funded_12m_blowup"), Mapping) else {}
    blowup_12m = _reject_bool_and_coerce_finite_float(
        fn12["blowup_12m_pct"] if "blowup_12m_pct" in fn12 else case.get("funded_12m_blowup_pct")
    )
    wilson_ub = _reject_bool_and_coerce_finite_float(
        fn12["wilson_95_ub_pct"] if "wilson_95_ub_pct" in fn12 else case.get("funded_12m_wilson_95_ub_pct")
    )

    ev_fee_24m = _reject_bool_and_coerce_finite_float(case.get("ev_per_1_vnd_fee_24m"))
    ev_fee_36m = _reject_bool_and_coerce_finite_float(case.get("ev_per_1_vnd_fee_36m", ev_fee_24m))
    ev_fee_grade = _reject_bool_and_coerce_finite_float(case.get("ev_per_fee", ev_fee_36m))
    ruin_24m = _reject_bool_and_coerce_finite_float(case.get("p_bankroll_ruin_24m_pct", 0.0))
    ruin_36m_col = _reject_bool_and_coerce_finite_float(case.get("p_bankroll_ruin_pct", ruin_24m))
    eval_scope_str = str(case.get("eval_scope") or "SINGLE_TICKET")
    ruin_36m_grade = (
        _opt_float("ruin_36m_pct")
        if "ruin_36m_pct" in case
        else (None if eval_scope_str == "SINGLE_TICKET" else ruin_36m_col)
    )
    p_le_0_24m = _reject_bool_and_coerce_finite_float(case.get("p_net_le_0_24m_pct"))
    p_le_0_36m = _reject_bool_and_coerce_finite_float(case.get("p_net_le_0_36m_pct", p_le_0_24m))
    pay1_730 = _reject_bool_and_coerce_finite_float(case.get("uncond_med_pay1_cal_days_cap730"))
    pay1_365 = _reject_bool_and_coerce_finite_float(
        case.get("uncond_med_pay1_cal_days_cap365", min(pay1_730, 365.0))
    )

    eval_input = EvaluationInputRecord(
        record_id=case_key,
        domain_tier=case.get("domain_tier", "T1_CFD_PROP"),
        eval_scope=eval_scope_str,  # type: ignore[arg-type]
        pricing_regime=case.get("pricing_regime", "ALL_REGULAR_SSOT"),
        evidence_stage=case.get("evidence_stage", "DEV_CONSUMED_OOS"),
        data_resolution=case.get("data_resolution", "APPROX_DAILY"),
        execution_status=str(case.get("execution_status") or "MEASURED_DEMO_EXECUTION"),
        risk_spectrum_tier=case.get("risk_spectrum_tier"),
        legacy_grade_code=case.get("legacy_grade_code"),
        profit_factor=pf_val,
        calmar=calmar_val,
        sharpe=sharpe_val,
        ev_per_fee=ev_fee_grade,
        funded_12m_blowup_pct=blowup_12m,
        ruin_36m_pct=ruin_36m_grade,
        p_le_zero_24m_pct=p_le_0_24m,
        payout_1_cal_days=pay1_730,
        slippage_breakeven_mult=slip_be_val,
        p1_pass_rate_pct=_opt_float("p1_pass_rate_pct"),
        p1_fail_rate_pct=_opt_float("p1_fail_rate_pct"),
        p1_pending_rate_pct=_opt_float("p1_pending_rate_pct"),
        p2_pass_rate_pct=_opt_float("p2_pass_rate_pct"),
        p2_fail_rate_pct=_opt_float("p2_fail_rate_pct"),
        p2_pending_rate_pct=_opt_float("p2_pending_rate_pct"),
        pass_eval_12m_pct=_opt_float("pass_eval_12m_pct")
        if case.get("pass_eval_12m_pct") is not None
        else monthly_map["12m"].pass_pct,
        pass_eval_36m_pct=_opt_float("pass_eval_36m_pct")
        if case.get("pass_eval_36m_pct") is not None
        else monthly_map["36m"].pass_pct,
        monthly_pass_fail_pending=monthly_map,
        first_ticket_pass_fail_pending=first_ticket_map,
        funded_12m_wilson_95_ub_pct=wilson_ub,
        ev_per_trade_r=ev_r_val,
        winrate_pct=wr_val,
        avg_rr=rr_val,
        max_dd_pct=max_dd_val,
        median_24m_net_vnd=_reject_bool_and_coerce_finite_float(case.get("median_24m_net_vnd")),
        median_36m_net_vnd=_reject_bool_and_coerce_finite_float(
            case.get("median_36m_net_vnd", case.get("median_24m_net_vnd"))
        ),
        median_36m_net_usd=_reject_bool_and_coerce_finite_float(case.get("median_36m_net_usd")),
        holdout_rows_analysed=0,
        order_send_count=0,
    )
    scorecard = grade_evaluation_record(eval_input, taxonomy=taxonomy)

    p1_detail = scorecard.phase_grades["p1"]
    p2_detail = scorecard.phase_grades["p2"]
    pass_detail = scorecard.phase_grades["pass_eval"]
    fn_detail = scorecard.phase_grades["funded_12m"]
    legacy_grade_col = str(case.get("legacy_grade_code") or scorecard.unified_grade_code)

    row_payload: dict[str, Any] = {
        "case_key": case_key,
        "run_id": run_id,
        "campaign_id": campaign_id,
        "source_cohort": source_cohort,
        "case_id": case_id,
        "firm_group": firm_group,
        "contract_id": str(case["contract_id"]) if case.get("contract_id") is not None else None,
        "profile_id": profile_id,
        "funded_mult": funded_mult,
        "friction_mult": friction_mult,
        "bankroll_m_vnd": _validate_strict_int(case.get("bankroll_m_vnd")),
        "bankroll_usd": _reject_bool_and_coerce_finite_float(case.get("bankroll_usd")),
        "concurrency_mode": _validate_non_empty_text(case.get("concurrency_mode") or "SINGLE_TICKET_ZERO_RETRY"),
        "allocation_policy": _validate_non_empty_text(case.get("allocation_policy") or "SINGLE_TICKET_BASELINE"),
        "domain_tier": scorecard.domain_tier,
        "eval_scope": scorecard.eval_scope,
        "pricing_regime": scorecard.pricing_regime,
        "evidence_stage": scorecard.evidence_stage,
        "data_resolution": scorecard.data_resolution,
        "resolution_label_vi": scorecard.resolution_label_vi,
        "execution_status": scorecard.execution_status,
        "n_paths": _validate_strict_int(case.get("n_paths")),
        "horizon_days": _validate_strict_int(case.get("horizon_days")),
        "is_pareto_in_tier": bool(case.get("is_pareto_in_tier", False)),
        "is_pareto_overall": bool(case.get("is_pareto_overall", False)),
        "median_24m_net_vnd": _reject_bool_and_coerce_finite_float(case.get("median_24m_net_vnd")),
        "median_36m_net_vnd": _reject_bool_and_coerce_finite_float(
            case.get("median_36m_net_vnd", case.get("median_24m_net_vnd"))
        ),
        "median_36m_net_usd": _reject_bool_and_coerce_finite_float(case.get("median_36m_net_usd")),
        "mean_36m_net_vnd": _reject_bool_and_coerce_finite_float(
            case.get("mean_36m_net_vnd", case.get("median_24m_net_vnd"))
        ),
        "ev_per_1_vnd_fee_24m": ev_fee_24m,
        "ev_per_1_vnd_fee_36m": ev_fee_36m,
        "p_net_le_0_24m_pct": p_le_0_24m,
        "p_net_le_0_36m_pct": p_le_0_36m,
        "p_bankroll_ruin_24m_pct": ruin_24m,
        "p_bankroll_ruin_pct": ruin_36m_col,
        "funded_12m_blowup_pct": blowup_12m,
        "funded_12m_wilson_95_ub_pct": wilson_ub,
        "uncond_med_pay1_cal_days_cap365": pay1_365,
        "uncond_med_pay1_cal_days_cap730": pay1_730,
        "pass_12m_pct": monthly_map["12m"].pass_pct,
        "fail_12m_pct": monthly_map["12m"].fail_pct,
        "pending_12m_pct": monthly_map["12m"].pending_pct,
        "pass_36m_pct": monthly_map["36m"].pass_pct,
        "fail_36m_pct": monthly_map["36m"].fail_pct,
        "pending_36m_pct": monthly_map["36m"].pending_pct,
        "strategy_pf": pf_val,
        "strategy_calmar": calmar_val,
        "strategy_sharpe": sharpe_val,
        "strategy_winrate_pct": wr_val,
        "strategy_avg_rr": rr_val,
        "strategy_ev_r": ev_r_val,
        "legacy_grade_code": legacy_grade_col,
        "unified_grade_code": scorecard.unified_grade_code,
        "p1_grade": p1_detail.grade,
        "p2_grade": p2_detail.grade,
        "pass_eval_grade": pass_detail.grade,
        "funded_12m_grade": fn_detail.grade,
        "p1_presentation_state_json": _canonical_json(p1_detail.presentation_state.model_dump(mode="json")),
        "p2_presentation_state_json": _canonical_json(p2_detail.presentation_state.model_dump(mode="json")),
        "metric_pass_map_json": _canonical_json(scorecard.metric_pass_map),
        "exact_bottlenecks_json": _canonical_json([b.model_dump(mode="json") for b in scorecard.exact_bottlenecks]),
        "scorecard_json": _canonical_json(scorecard.model_dump(mode="json")),
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "source_artifact_sha256": source_artifact_sha256,
        "created_utc": created_utc,
    }
    row_payload["record_sha256"] = _sha256_text(_canonical_json(row_payload))
    return row_payload


def _read_legacy_source_rows(
    source_key: str,
    db_path: Path,
    table_name: str,
) -> tuple[list[dict[str, Any]], str]:
    """Read ONE distinct legacy table in read-only mode (ZERO mutation to legacy DBs, ZERO double counting)."""
    duckdb = _import_duckdb()
    if not db_path.is_file():
        raise FileNotFoundError(f"LEGACY_DB_NOT_FOUND: {db_path}")
    db_sha = _sha256_file(db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        if table_name not in tables:
            raise ValueError(f"LEGACY_TABLE_MISSING: {db_path}::{table_name} (found {sorted(tables)})")

        rows_out: list[dict[str, Any]] = []
        if source_key == "experiments_core" or table_name == "experiments":
            raw_rows = con.execute(
                """
                SELECT run_id, family_id, strategy_id, sharpe, p_value, created_utc
                FROM experiments
                ORDER BY run_id ASC
                """
            ).fetchall()
            for run_id, family_id, strategy_id, sharpe, p_value, created_utc in raw_rows:
                lid = str(run_id)
                rows_out.append(
                    {
                        "trial_uid": f"{source_key}::{table_name}::{lid}",
                        "source_key": source_key,
                        "source_db": db_path.name,
                        "source_table": table_name,
                        "legacy_id": lid,
                        "family_id": str(family_id),
                        "strategy_id": str(strategy_id),
                        "sharpe": float(sharpe) if sharpe is not None and math.isfinite(float(sharpe)) else None,
                        "profit_factor": None,
                        "max_dd_pct": None,
                        "p_value": float(p_value) if p_value is not None and math.isfinite(float(p_value)) else None,
                        "verdict": None,
                        "evidence_stage": "DEV_CONSUMED_OOS",
                        "holdout_rows_analysed": 0,
                        "created_utc": str(created_utc),
                        "source_db_sha256": db_sha,
                    }
                )
        elif source_key == "wave4_ml_m48" or table_name == "wave4_ml_m48":
            raw_rows = con.execute(
                """
                SELECT trial_id, family_name, pf_1x, max_dd_pct_1x, verdict, oos_label,
                       holdout_rows_analysed, created_utc
                FROM wave4_ml_m48
                ORDER BY trial_seq ASC, trial_id ASC
                """
            ).fetchall()
            for trial_id, family_name, pf_1x, max_dd_pct_1x, verdict, oos_label, ho, created_utc in raw_rows:
                if int(ho or 0) != 0:
                    raise ValueError(f"HOLDOUT_VIOLATION in wave4_ml_m48::{trial_id}: holdout_rows={ho}")
                lid = str(trial_id)
                stage = "DEV_CONSUMED_OOS" if "CONSUMED" in str(oos_label or "").upper() else "DEV_IS"
                rows_out.append(
                    {
                        "trial_uid": f"{source_key}::{table_name}::{lid}",
                        "source_key": source_key,
                        "source_db": db_path.name,
                        "source_table": table_name,
                        "legacy_id": lid,
                        "family_id": str(family_name),
                        "strategy_id": f"v104_ml::{lid}",
                        "sharpe": None,
                        "profit_factor": float(pf_1x) if pf_1x is not None and math.isfinite(float(pf_1x)) else None,
                        "max_dd_pct": (
                            float(max_dd_pct_1x)
                            if max_dd_pct_1x is not None and math.isfinite(float(max_dd_pct_1x))
                            else None
                        ),
                        "p_value": None,
                        "verdict": str(verdict) if verdict is not None else None,
                        "evidence_stage": stage,
                        "holdout_rows_analysed": 0,
                        "created_utc": str(created_utc),
                        "source_db_sha256": db_sha,
                    }
                )
        elif source_key == "wave4_frontier_m36" or table_name == "wave4_frontier_trials":
            # Explicitly query ONLY `wave4_frontier_trials`, skipping duplicate `experiments` table!
            raw_rows = con.execute(
                """
                SELECT trial_id, family_budget_id, sleeve_id, split, cluster_a_sharpe, cluster_a_dd,
                       p_value, holdout_rows_analysed, created_utc
                FROM wave4_frontier_trials
                ORDER BY trial_id ASC
                """
            ).fetchall()
            for trial_id, fam_id, sleeve_id, split, sh, dd, pval, ho, created_utc in raw_rows:
                if int(ho or 0) != 0:
                    raise ValueError(f"HOLDOUT_VIOLATION in wave4_frontier_trials::{trial_id}: holdout_rows={ho}")
                lid = str(trial_id)
                stage = "DEV_BLIND_OOS" if "blind" in str(split or "").lower() else "DEV_IS"
                rows_out.append(
                    {
                        "trial_uid": f"{source_key}::{table_name}::{lid}",
                        "source_key": source_key,
                        "source_db": db_path.name,
                        "source_table": table_name,
                        "legacy_id": lid,
                        "family_id": str(fam_id),
                        "strategy_id": f"{sleeve_id}::{lid}",
                        "sharpe": float(sh) if sh is not None and math.isfinite(float(sh)) else None,
                        "profit_factor": None,
                        "max_dd_pct": float(dd) if dd is not None and math.isfinite(float(dd)) else None,
                        "p_value": float(pval) if pval is not None and math.isfinite(float(pval)) else None,
                        "verdict": str(split) if split is not None else None,
                        "evidence_stage": stage,
                        "holdout_rows_analysed": 0,
                        "created_utc": str(created_utc),
                        "source_db_sha256": db_sha,
                    }
                )
        else:
            raise ValueError(f"UNSUPPORTED_LEGACY_SOURCE: {source_key!r} / {table_name!r}")
    finally:
        con.close()
    return rows_out, db_sha


class UnifiedEvaluationCatalog:
    """Federated DuckDB catalog backed by `SQLiteRunRegistry` tamper-evident SHA-256 hash chain."""

    def __init__(
        self,
        duckdb_path: str | Path = DEFAULT_CATALOG_DUCKDB_PATH,
        registry_path: str | Path | None = None,
        taxonomy_path: str | Path = DEFAULT_TAXONOMY_PATH,
        *,
        read_only: bool = False,
    ) -> None:
        self.duckdb_path = Path(duckdb_path)
        self.read_only = bool(read_only)
        self.registry_path = (
            Path(registry_path)
            if registry_path is not None
            else self.duckdb_path.with_name("unified_eval_registry.sqlite3")
        )
        self.taxonomy_path = Path(taxonomy_path)
        self.taxonomy, self.taxonomy_sha256 = load_evaluation_taxonomy(self.taxonomy_path)
        self._lock = threading.RLock()
        self._con_box: list[Any] = [None]
        self._finalizer = weakref.finalize(self, _close_con_box, self._con_box)

        if not self.read_only:
            self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
            self.registry = SQLiteRunRegistry(self.registry_path)
            with self._connect() as con:
                con.execute(_CATALOG_SCHEMA_SQL)
                self._ensure_mc_campaign_id_column(con)
        else:
            self.registry = SQLiteRunRegistry(self.registry_path) if self.registry_path.is_file() else None

    @staticmethod
    def _ensure_mc_campaign_id_column(con: Any) -> None:
        """Idempotently migrate pre-campaign `mc_cases_catalog` tables without mutating Wave 4 row hashes."""
        cols = {str(r[1]) for r in con.execute("PRAGMA table_info('mc_cases_catalog')").fetchall()}
        if "campaign_id" not in cols:
            con.execute("ALTER TABLE mc_cases_catalog ADD COLUMN campaign_id VARCHAR DEFAULT 'offensive4'")
        con.execute("UPDATE mc_cases_catalog SET campaign_id = 'offensive4' WHERE campaign_id IS NULL")

    def close(self) -> None:
        with self._lock:
            _close_con_box(self._con_box)

    def __enter__(self) -> UnifiedEvaluationCatalog:
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()

    @contextmanager
    def _connect(self) -> Generator[Any, None, None]:
        duckdb = _import_duckdb()
        with self._lock:
            con = self._con_box[0]
            if con is None:
                con = duckdb.connect(str(self.duckdb_path), read_only=self.read_only)
                self._con_box[0] = con
            yield con

    def _require_writable(self) -> SQLiteRunRegistry:
        if self.read_only or self.registry is None:
            raise RuntimeError("CATALOG_READ_ONLY: write operation rejected on read-only catalog")
        return self.registry

    def _append_registry_event(
        self,
        *,
        run_id: str,
        run_kind: str,
        correlation_id: str,
        event_type: str,
        idempotency_key: str,
        payload: Mapping[str, Any],
        input_sha256: str,
        source_refs: tuple[str, ...],
        occurred_at_utc: str | None = None,
    ) -> RunEvent:
        registry = self._require_writable()
        ts = occurred_at_utc or utc_now()
        cfg_sha = _sha256_text(_canonical_json(payload))
        prov = Provenance(
            code_revision="wave5-evaluation-catalog-v1",
            config_sha256=cfg_sha,
            input_sha256=input_sha256 if _SHA256_RE.fullmatch(input_sha256) else _sha256_text(input_sha256),
            source_refs=source_refs,
        )
        safe_rid = _safe_reg_id(run_id, prefix="w5")
        safe_corr = _safe_reg_id(correlation_id, prefix="corr")
        safe_idem = _safe_reg_id(idempotency_key, prefix="idem")
        run_rec = RunRecord(
            run_id=safe_rid,
            attempt_no=1,
            fence_token=f"w5cat-{safe_rid}",
            project_id="quant_factory_wave5",
            run_kind=run_kind,
            mode="research",
            correlation_id=safe_corr,
            provenance=prov,
            created_at_utc=ts,
        )
        registered = registry.register_run(run_rec)
        return registry.append(
            RunEvent.create(
                event_type=event_type,
                run=registered,
                idempotency_key=safe_idem,
                event_id=_safe_reg_id(f"evt-{safe_idem}", prefix="evt"),
                occurred_at_utc=registered.created_at_utc,
                payload=dict(payload),
            )
        )

    def record_run(
        self,
        eval_input: EvaluationInputRecord | Mapping[str, Any],
        *,
        strategy_id: str,
        wave_tag: str = "wave5",
        profile_id: str | None = None,
        funded_mult: float | None = None,
        friction_mult: float | None = None,
        created_utc: str | None = None,
    ) -> dict[str, Any]:
        """Validate, grade, hash-chain in SQLiteRunRegistry, and insert into `runs_catalog`."""
        self._require_writable()
        rec = (
            eval_input
            if isinstance(eval_input, EvaluationInputRecord)
            else EvaluationInputRecord.model_validate(eval_input)
        )
        sid = _validate_non_empty_text(strategy_id)
        wtag = _validate_non_empty_text(wave_tag)
        fm = _reject_bool_and_coerce_finite_float(funded_mult) if funded_mult is not None else None
        fric = _reject_bool_and_coerce_finite_float(friction_mult) if friction_mult is not None else None
        scorecard = grade_evaluation_record(rec, taxonomy=self.taxonomy)
        ts = created_utc or utc_now()

        row_dict: dict[str, Any] = {
            "run_id": rec.record_id,
            "strategy_id": sid,
            "wave_tag": wtag,
            "domain_tier": scorecard.domain_tier,
            "eval_scope": scorecard.eval_scope,
            "pricing_regime": scorecard.pricing_regime,
            "evidence_stage": scorecard.evidence_stage,
            "data_resolution": scorecard.data_resolution,
            "execution_status": scorecard.execution_status,
            "risk_spectrum_tier": scorecard.risk_spectrum_tier,
            "profile_id": profile_id,
            "funded_mult": fm,
            "friction_mult": fric,
            "legacy_grade_code": scorecard.legacy_grade_code,
            "unified_grade_code": scorecard.unified_grade_code,
            "p1_grade": scorecard.phase_grades["p1"].grade,
            "p2_grade": scorecard.phase_grades["p2"].grade,
            "pass_eval_grade": scorecard.phase_grades["pass_eval"].grade,
            "funded_12m_grade": scorecard.phase_grades["funded_12m"].grade,
            "profit_factor": rec.profit_factor,
            "calmar": rec.calmar,
            "sharpe": rec.sharpe,
            "ev_per_fee": rec.ev_per_fee,
            "funded_12m_blowup_pct": rec.funded_12m_blowup_pct,
            "ruin_36m_pct": rec.ruin_36m_pct,
            "p_le_zero_24m_pct": rec.p_le_zero_24m_pct,
            "payout_1_cal_days": rec.payout_1_cal_days,
            "slippage_breakeven_mult": rec.slippage_breakeven_mult,
            "metric_pass_map_json": _canonical_json(scorecard.metric_pass_map),
            "exact_bottlenecks_json": _canonical_json([b.model_dump(mode="json") for b in scorecard.exact_bottlenecks]),
            "scorecard_json": _canonical_json(scorecard.model_dump(mode="json")),
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "created_utc": ts,
        }
        rec_sha = _sha256_text(_canonical_json(row_dict))
        row_dict["record_sha256"] = rec_sha

        event = self._append_registry_event(
            run_id=rec.record_id,
            run_kind="evaluation_run",
            correlation_id=f"wave-{wtag}",
            event_type="catalog.run_recorded",
            idempotency_key=f"run-{rec.record_id}-{rec_sha[:16]}",
            payload={
                "table": "runs_catalog",
                "run_id": rec.record_id,
                "strategy_id": sid,
                "unified_grade_code": scorecard.unified_grade_code,
                "record_sha256": rec_sha,
                "holdout_rows_analysed": 0,
                "order_send_count": 0,
            },
            input_sha256=self.taxonomy_sha256,
            source_refs=(f"strategy:{sid}", f"wave:{wtag}"),
            occurred_at_utc=ts,
        )
        row_dict["registry_event_hash"] = str(event.event_hash)

        cols = list(row_dict.keys())
        placeholders = ", ".join("?" for _ in cols)
        with self._connect() as con:
            con.execute(
                f"INSERT OR REPLACE INTO runs_catalog ({', '.join(cols)}) VALUES ({placeholders})",
                [row_dict[c] for c in cols],
            )
        return {**row_dict, "scorecard": scorecard.model_dump(mode="json")}

    def record_alpha(
        self,
        entry: AlphaRegistryEntry | Mapping[str, Any],
        *,
        updated_utc: str | None = None,
    ) -> dict[str, Any]:
        """Validate, map Wave 5 blindness tier, grade, hash-chain, and upsert into `alpha_registry_catalog`."""
        self._require_writable()
        item = entry if isinstance(entry, AlphaRegistryEntry) else AlphaRegistryEntry.model_validate(entry)
        mapped_tier = map_blindness_tier(item.raw_blindness_tier, self.taxonomy)
        ts = updated_utc or utc_now()

        eval_input = EvaluationInputRecord(
            record_id=item.alpha_id,
            domain_tier="T3_MULTI_ASSET_OWNBOOK",
            eval_scope="SINGLE_TICKET",
            pricing_regime="ALL_REGULAR_SSOT",
            evidence_stage=item.evidence_stage,
            data_resolution=item.data_resolution,
            execution_status="MEASURED_DEMO_EXECUTION" if item.mt5_hcc_ready else "TERMS_VERIFIED_EXECUTION_UNMEASURED",
            profit_factor=item.profit_factor,
            calmar=item.calmar,
            sharpe=item.cluster_b_sharpe if item.cluster_b_sharpe is not None else item.cluster_a_sharpe,
            slippage_breakeven_mult=item.slippage_breakeven_mult,
            holdout_rows_analysed=0,
            order_send_count=0,
        )
        scorecard = grade_evaluation_record(eval_input, taxonomy=self.taxonomy)

        row_dict: dict[str, Any] = {
            "alpha_id": item.alpha_id,
            "family_id": item.family_id,
            "symbol": item.symbol,
            "leader_symbol": item.leader_symbol,
            "lifecycle_state": item.lifecycle_state,
            "blindness_tier": mapped_tier,
            "mt5_hcc_ready": bool(item.mt5_hcc_ready),
            "evidence_stage": item.evidence_stage,
            "data_resolution": item.data_resolution,
            "cluster_a_sharpe": item.cluster_a_sharpe,
            "cluster_b_sharpe": item.cluster_b_sharpe,
            "profit_factor": item.profit_factor,
            "calmar": item.calmar,
            "slippage_breakeven_mult": item.slippage_breakeven_mult,
            "corr_vs_7e": item.corr_vs_7e,
            "tail_corr_vs_7e": item.tail_corr_vs_7e,
            "unified_grade_code": scorecard.unified_grade_code,
            "scorecard_json": _canonical_json(scorecard.model_dump(mode="json")),
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "updated_utc": ts,
        }
        rec_sha = _sha256_text(_canonical_json(row_dict))
        row_dict["record_sha256"] = rec_sha

        event = self._append_registry_event(
            run_id=f"alpha-{item.alpha_id}",
            run_kind="alpha_registry",
            correlation_id=f"fam-{item.family_id}",
            event_type="catalog.alpha_upserted",
            idempotency_key=f"alpha-{item.alpha_id}-{rec_sha[:16]}",
            payload={
                "table": "alpha_registry_catalog",
                "alpha_id": item.alpha_id,
                "lifecycle_state": item.lifecycle_state,
                "blindness_tier": mapped_tier,
                "record_sha256": rec_sha,
                "holdout_rows_analysed": 0,
                "order_send_count": 0,
            },
            input_sha256=self.taxonomy_sha256,
            source_refs=(f"family:{item.family_id}", f"symbol:{item.symbol}"),
            occurred_at_utc=ts,
        )
        row_dict["registry_event_hash"] = str(event.event_hash)

        cols = list(row_dict.keys())
        placeholders = ", ".join("?" for _ in cols)
        with self._connect() as con:
            con.execute(
                f"INSERT OR REPLACE INTO alpha_registry_catalog ({', '.join(cols)}) VALUES ({placeholders})",
                [row_dict[c] for c in cols],
            )
        return row_dict

    def ingest_legacy_trials(
        self,
        *,
        sources: Sequence[Mapping[str, Any]] | None = None,
        repo_root: Path = REPO_ROOT,
        ingested_utc: str | None = None,
    ) -> dict[str, Any]:
        """Ingest exact 3 distinct legacy DuckDB tables into `legacy_trials_federated_view` (ZERO double counting)."""
        self._require_writable()
        src_list = list(sources) if sources is not None else list(DEFAULT_LEGACY_SOURCES)
        if not src_list:
            raise ValueError("sources must not be empty")

        all_rows: list[dict[str, Any]] = []
        per_source_counts: dict[str, int] = {}
        per_source_sha: dict[str, str] = {}
        seen_uids: set[str] = set()

        for src in src_list:
            skey = _validate_non_empty_text(src["source_key"])
            tname = _validate_non_empty_text(src["table_name"])
            if "db_path" in src and src["db_path"] is not None:
                db_path = Path(src["db_path"])
            else:
                db_path = Path(repo_root) / str(src["db_rel_path"])
            # Hard anti-double-counting guard: NEVER ingest `experiments` from wave4_frontier_m36.duckdb!
            if "frontier" in db_path.name.lower() and tname == "experiments":
                raise ValueError(
                    "DOUBLE_COUNT_GUARD: wave4_frontier_m36.duckdb::experiments is a duplicate of "
                    "wave4_frontier_trials and MUST be skipped"
                )
            rows, db_sha = _read_legacy_source_rows(skey, db_path, tname)
            for row in rows:
                uid = row["trial_uid"]
                if uid in seen_uids:
                    raise ValueError(f"DUPLICATE_TRIAL_UID: {uid!r}")
                seen_uids.add(uid)
            all_rows.extend(rows)
            per_source_counts[f"{skey}::{tname}"] = len(rows)
            per_source_sha[f"{skey}::{tname}"] = db_sha

        ts = ingested_utc or utc_now()
        manifest_sha = _sha256_text(
            _canonical_json(
                {
                    "per_source_counts": per_source_counts,
                    "per_source_sha": per_source_sha,
                    "total_rows": len(all_rows),
                }
            )
        )
        event = self._append_registry_event(
            run_id=f"legacy-federated-{manifest_sha[:16]}",
            run_kind="legacy_federation",
            correlation_id="wave5-legacy-federation",
            event_type="catalog.legacy_trials_ingested",
            idempotency_key=f"legacy-fed-{manifest_sha[:32]}",
            payload={
                "table": "legacy_trials_federated_view",
                "total_distinct_trials": len(all_rows),
                "per_source_counts": per_source_counts,
                "per_source_sha": per_source_sha,
                "manifest_sha256": manifest_sha,
                "holdout_rows_analysed": 0,
                "order_send_count": 0,
            },
            input_sha256=manifest_sha,
            source_refs=tuple(sorted(per_source_counts.keys())),
            occurred_at_utc=ts,
        )

        cols = (
            "trial_uid",
            "source_key",
            "source_db",
            "source_table",
            "legacy_id",
            "family_id",
            "strategy_id",
            "sharpe",
            "profit_factor",
            "max_dd_pct",
            "p_value",
            "verdict",
            "evidence_stage",
            "holdout_rows_analysed",
            "created_utc",
            "source_db_sha256",
        )
        placeholders = ", ".join("?" for _ in cols)
        with self._connect() as con:
            con.execute("BEGIN TRANSACTION")
            try:
                con.execute("DELETE FROM _legacy_trials_ingested")
                con.executemany(
                    f"INSERT INTO _legacy_trials_ingested ({', '.join(cols)}) VALUES ({placeholders})",
                    [[r[c] for c in cols] for r in all_rows],
                )
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

        return {
            "total_distinct_trials": len(all_rows),
            "per_source_counts": per_source_counts,
            "per_source_sha": per_source_sha,
            "manifest_sha256": manifest_sha,
            "registry_event_hash": str(event.event_hash),
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }

    def backfill_wave4_pareto(
        self,
        pareto_json_path: Path = DEFAULT_WAVE4_PARETO_PATH,
        *,
        backfilled_utc: str | None = None,
    ) -> dict[str, Any]:
        """Backfill all 168 Wave 4 MC rows (81 FTMO 1.0x + 81 FTMO 1.5x + 6 The5ers) into `mc_cases_catalog`."""
        self._require_writable()
        p = Path(pareto_json_path)
        if not p.is_file():
            raise FileNotFoundError(f"WAVE4_PARETO_JSON_NOT_FOUND: {p}")
        art_sha = _sha256_file(p)
        payload = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Wave 4 Pareto JSON root must be an object")

        profile_id, funded_mult, ref_sku_diag = _extract_wave4_ssot_context(payload)
        ts = backfilled_utc or str(payload.get("generated_utc") or utc_now())
        if not ts.endswith("Z"):
            ts = utc_now()
        run_id = f"wave4-pareto-backfill-{art_sha[:12]}"

        cohorts: tuple[tuple[str, str, str, float], ...] = (
            ("cases", "FTMO_BASELINE_1_0X", "FTMO", 1.0),
            ("cases_stress_1_5x", "FTMO_STRESS_1_5X", "FTMO", 1.5),
            ("the5ers_reference_rows", "THE5ERS_REF_1_0X", "THE5ERS", 1.0),
        )
        rows_to_insert: list[dict[str, Any]] = []
        cohort_counts: dict[str, int] = {}
        legacy_grade_counts: dict[str, int] = {}
        unified_grade_counts: dict[str, int] = {}

        for list_key, cohort_name, firm_group, default_fric in cohorts:
            raw_cases = payload.get(list_key)
            if not isinstance(raw_cases, list):
                raise ValueError(f"Wave 4 Pareto JSON missing list {list_key!r}")
            cohort_counts[cohort_name] = len(raw_cases)
            for case in raw_cases:
                row = _case_to_mc_row(
                    case,
                    source_cohort=cohort_name,
                    firm_group=firm_group,
                    profile_id=profile_id,
                    funded_mult=funded_mult,
                    default_friction_mult=default_fric,
                    ref_sku_diag=ref_sku_diag,
                    taxonomy=self.taxonomy,
                    source_artifact_sha256=art_sha,
                    run_id=run_id,
                    created_utc=ts,
                )
                rows_to_insert.append(row)
                lg = row["legacy_grade_code"]
                ug = row["unified_grade_code"]
                legacy_grade_counts[lg] = legacy_grade_counts.get(lg, 0) + 1
                unified_grade_counts[ug] = unified_grade_counts.get(ug, 0) + 1

        batch_sha = _sha256_text(
            _canonical_json(
                {
                    "source_artifact_sha256": art_sha,
                    "profile_id": profile_id,
                    "funded_mult": funded_mult,
                    "row_hashes": {r["case_key"]: r["record_sha256"] for r in rows_to_insert},
                }
            )
        )
        event = self._append_registry_event(
            run_id=run_id,
            run_kind="wave4_mc_backfill",
            correlation_id="wave5-wave4-backfill",
            event_type="catalog.mc_cases_backfilled",
            idempotency_key=f"mc-backfill-{batch_sha[:32]}",
            payload={
                "table": "mc_cases_catalog",
                "total_mc_cases": len(rows_to_insert),
                "cohort_counts": cohort_counts,
                "profile_id": profile_id,
                "funded_mult": funded_mult,
                "source_artifact_sha256": art_sha,
                "batch_sha256": batch_sha,
                "legacy_grade_counts": legacy_grade_counts,
                "unified_grade_counts": unified_grade_counts,
                "holdout_rows_analysed": 0,
                "order_send_count": 0,
            },
            input_sha256=art_sha,
            source_refs=("wave4:pareto_81cases_10k", f"profile:{profile_id}"),
            occurred_at_utc=ts,
        )
        ev_hash = str(event.event_hash)
        for r in rows_to_insert:
            r["registry_event_hash"] = ev_hash

        cols = list(rows_to_insert[0].keys())
        placeholders = ", ".join("?" for _ in cols)
        with self._connect() as con:
            con.execute("BEGIN TRANSACTION")
            try:
                con.executemany(
                    f"INSERT OR REPLACE INTO mc_cases_catalog ({', '.join(cols)}) VALUES ({placeholders})",
                    [[r[c] for c in cols] for r in rows_to_insert],
                )
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

        return {
            "total_mc_cases": len(rows_to_insert),
            "cohort_counts": cohort_counts,
            "profile_id": profile_id,
            "funded_mult": funded_mult,
            "legacy_grade_counts": legacy_grade_counts,
            "unified_grade_counts": unified_grade_counts,
            "source_artifact_sha256": art_sha,
            "batch_sha256": batch_sha,
            "registry_event_hash": ev_hash,
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }

    def record_mc_cases(
        self,
        cases: Sequence[Mapping[str, Any]],
        *,
        campaign_id: str,
        run_id: str,
        source_artifact_sha256: str,
        created_utc: str | None = None,
        replace_campaign: bool = True,
    ) -> dict[str, Any]:
        """Grade, hash-chain in SQLiteRunRegistry, and upsert Wave 5 MC cases into `mc_cases_catalog`."""
        self._require_writable()
        cid = _validate_non_empty_text(campaign_id)
        if cid == "offensive4":
            raise ValueError("CAMPAIGN_PROTECTED: use backfill_wave4_pareto() for campaign_id='offensive4'")
        rid = _validate_non_empty_text(run_id)
        art_sha = _validate_sha256_hex(source_artifact_sha256)
        case_list = list(cases)
        if not case_list:
            raise ValueError("EMPTY_MC_CASES: record_mc_cases requires at least 1 case")

        ts = created_utc or utc_now()
        rows_to_insert: list[dict[str, Any]] = []
        cohort_counts: dict[str, int] = {}
        unified_grade_counts: dict[str, int] = {}
        phase_grade_summary: dict[str, dict[str, str]] = {}

        for case in case_list:
            row = _wave5_case_to_mc_row(
                case,
                campaign_id=cid,
                run_id=rid,
                source_artifact_sha256=art_sha,
                taxonomy=self.taxonomy,
                created_utc=ts,
            )
            rows_to_insert.append(row)
            coh = row["source_cohort"]
            cohort_counts[coh] = cohort_counts.get(coh, 0) + 1
            ug = row["unified_grade_code"]
            unified_grade_counts[ug] = unified_grade_counts.get(ug, 0) + 1
            phase_grade_summary[row["case_key"]] = {
                "overall": ug,
                "p1": row["p1_grade"],
                "p2": row["p2_grade"],
                "pass_eval": row["pass_eval_grade"],
                "funded_12m": row["funded_12m_grade"],
            }

        batch_sha = _sha256_text(
            _canonical_json(
                {
                    "campaign_id": cid,
                    "source_artifact_sha256": art_sha,
                    "row_hashes": {r["case_key"]: r["record_sha256"] for r in rows_to_insert},
                }
            )
        )
        event = self._append_registry_event(
            run_id=f"mc-{cid}-{batch_sha[:12]}",
            run_kind="wave5_mc_cases",
            correlation_id=f"campaign-{cid}",
            event_type="catalog.mc_cases_recorded",
            idempotency_key=f"mc-rec-{cid}-{batch_sha[:24]}",
            payload={
                "table": "mc_cases_catalog",
                "campaign_id": cid,
                "run_id": rid,
                "total_mc_cases": len(rows_to_insert),
                "cohort_counts": cohort_counts,
                "unified_grade_counts": unified_grade_counts,
                "source_artifact_sha256": art_sha,
                "batch_sha256": batch_sha,
                "holdout_rows_analysed": 0,
                "order_send_count": 0,
            },
            input_sha256=art_sha,
            source_refs=(f"campaign:{cid}", f"run:{rid}"),
            occurred_at_utc=ts,
        )
        ev_hash = str(event.event_hash)
        for r in rows_to_insert:
            r["registry_event_hash"] = ev_hash

        cols = list(rows_to_insert[0].keys())
        placeholders = ", ".join("?" for _ in cols)
        with self._connect() as con:
            con.execute("BEGIN TRANSACTION")
            try:
                if replace_campaign:
                    con.execute("DELETE FROM mc_cases_catalog WHERE campaign_id = ?", [cid])
                con.executemany(
                    f"INSERT OR REPLACE INTO mc_cases_catalog ({', '.join(cols)}) VALUES ({placeholders})",
                    [[r[c] for c in cols] for r in rows_to_insert],
                )
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise

        return {
            "campaign_id": cid,
            "run_id": rid,
            "total_mc_cases": len(rows_to_insert),
            "cohort_counts": cohort_counts,
            "unified_grade_counts": unified_grade_counts,
            "phase_grade_summary": phase_grade_summary,
            "source_artifact_sha256": art_sha,
            "batch_sha256": batch_sha,
            "registry_event_hash": ev_hash,
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }

    def query_sql(self, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        """Execute a single read-only parameterized SELECT/WITH query against DuckDB."""
        stmt = _validate_non_empty_text(sql)
        stripped = stmt.rstrip().rstrip(";").strip()
        if ";" in stripped or not _READONLY_SQL_START_RE.match(stripped) or _FORBIDDEN_SQL_WRITE_RE.search(stripped):
            raise ValueError("query_sql only permits single read-only SELECT/WITH queries")
        with self._connect() as con:
            return list(con.execute(stripped, list(params)).fetchall())

    def get_catalog_summary(self) -> dict[str, Any]:
        """Return compact counts and health summary across all 4 federated tables/views."""
        with self._connect() as con:
            runs_cnt = int(con.execute("SELECT COUNT(*) FROM runs_catalog").fetchone()[0])
            mc_cnt = int(con.execute("SELECT COUNT(*) FROM mc_cases_catalog").fetchone()[0])
            alpha_cnt = int(con.execute("SELECT COUNT(*) FROM alpha_registry_catalog").fetchone()[0])
            legacy_cnt = int(con.execute("SELECT COUNT(*) FROM legacy_trials_federated_view").fetchone()[0])
            legacy_distinct = int(
                con.execute("SELECT COUNT(DISTINCT trial_uid) FROM legacy_trials_federated_view").fetchone()[0]
            )
            legacy_by_src = {
                f"{r[0]}::{r[1]}": int(r[2])
                for r in con.execute(
                    "SELECT source_key, source_table, COUNT(*) "
                    "FROM legacy_trials_federated_view GROUP BY 1,2 ORDER BY 1,2"
                ).fetchall()
            }
            mc_by_cohort = {
                str(r[0]): int(r[1])
                for r in con.execute(
                    "SELECT source_cohort, COUNT(*) FROM mc_cases_catalog GROUP BY 1 ORDER BY 1"
                ).fetchall()
            }
            mc_cols = {str(r[1]) for r in con.execute("PRAGMA table_info('mc_cases_catalog')").fetchall()}
            if "campaign_id" in mc_cols:
                mc_by_campaign = {
                    str(r[0]): int(r[1])
                    for r in con.execute(
                        "SELECT campaign_id, COUNT(*) FROM mc_cases_catalog GROUP BY 1 ORDER BY 1"
                    ).fetchall()
                }
            else:
                mc_by_campaign = {"offensive4": mc_cnt} if mc_cnt > 0 else {}
        return {
            "duckdb_path": str(self.duckdb_path),
            "registry_path": str(self.registry_path),
            "runs_catalog_count": runs_cnt,
            "mc_cases_catalog_count": mc_cnt,
            "mc_by_cohort": mc_by_cohort,
            "mc_by_campaign": mc_by_campaign,
            "alpha_registry_catalog_count": alpha_cnt,
            "legacy_trials_federated_count": legacy_cnt,
            "legacy_trials_distinct_count": legacy_distinct,
            "legacy_by_source": legacy_by_src,
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }

    def verify_integrity(self) -> dict[str, Any]:
        """Verify BOTH SQLiteRunRegistry hash-chain AND DuckDB row/hash parity fail-closed."""
        if self.registry is None:
            raise JournalCorruptionError(f"REGISTRY_MISSING: {self.registry_path}")
        events = self.registry.replay()

        expected_runs: dict[str, str] = {}
        expected_alphas: dict[str, str] = {}
        latest_legacy_event: RunEvent | None = None
        latest_mc_event: RunEvent | None = None
        latest_mc_campaigns: dict[str, RunEvent] = {}

        for ev in events:
            et = ev.event_type
            p = ev.payload
            if et == "catalog.run_recorded":
                expected_runs[str(p["run_id"])] = str(p["record_sha256"])
            elif et == "catalog.alpha_upserted":
                expected_alphas[str(p["alpha_id"])] = str(p["record_sha256"])
            elif et == "catalog.legacy_trials_ingested":
                latest_legacy_event = ev
            elif et == "catalog.mc_cases_backfilled":
                latest_mc_event = ev
            elif et == "catalog.mc_cases_recorded":
                latest_mc_campaigns[str(p["campaign_id"])] = ev

        with self._connect() as con:
            # 1. Verify runs_catalog parity
            duck_runs = {
                str(r[0]): str(r[1]) for r in con.execute("SELECT run_id, record_sha256 FROM runs_catalog").fetchall()
            }
            if duck_runs != expected_runs:
                raise JournalCorruptionError(
                    f"RUNS_CATALOG_PARITY_MISMATCH: duckdb={len(duck_runs)} vs registry={len(expected_runs)}"
                )

            # 2. Verify alpha_registry_catalog parity
            duck_alphas = {
                str(r[0]): str(r[1])
                for r in con.execute("SELECT alpha_id, record_sha256 FROM alpha_registry_catalog").fetchall()
            }
            if duck_alphas != expected_alphas:
                raise JournalCorruptionError(
                    f"ALPHA_CATALOG_PARITY_MISMATCH: duckdb={len(duck_alphas)} vs registry={len(expected_alphas)}"
                )

            # 3. Verify legacy_trials_federated_view count & per-source manifest parity
            if latest_legacy_event is not None:
                exp_total = int(latest_legacy_event.payload["total_distinct_trials"])
                exp_by_src = dict(latest_legacy_event.payload["per_source_counts"])
                actual_total = int(con.execute("SELECT COUNT(*) FROM legacy_trials_federated_view").fetchone()[0])
                actual_distinct = int(
                    con.execute("SELECT COUNT(DISTINCT trial_uid) FROM legacy_trials_federated_view").fetchone()[0]
                )
                actual_by_src = {
                    f"{r[0]}::{r[1]}": int(r[2])
                    for r in con.execute(
                        "SELECT source_key, source_table, COUNT(*) FROM legacy_trials_federated_view GROUP BY 1,2"
                    ).fetchall()
                }
                if actual_total != exp_total or actual_distinct != exp_total or actual_by_src != exp_by_src:
                    raise JournalCorruptionError(
                        f"LEGACY_FEDERATION_TAMPERED: expected={exp_total}/{exp_by_src}, "
                        f"actual={actual_total}(distinct={actual_distinct})/{actual_by_src}"
                    )

            # 4. Verify mc_cases_catalog count & batch hash parity
            if latest_mc_event is not None:
                exp_mc_total = int(latest_mc_event.payload["total_mc_cases"])
                exp_batch_sha = str(latest_mc_event.payload["batch_sha256"])
                exp_art_sha = str(latest_mc_event.payload["source_artifact_sha256"])
                exp_profile = str(latest_mc_event.payload["profile_id"])
                exp_fm = float(latest_mc_event.payload["funded_mult"])
                mc_rows = con.execute(
                    """
                    SELECT case_key, record_sha256, source_artifact_sha256, profile_id, funded_mult,
                           holdout_rows_analysed, order_send_count
                    FROM mc_cases_catalog
                    WHERE source_artifact_sha256 = ?
                    ORDER BY case_key ASC
                    """,
                    [exp_art_sha],
                ).fetchall()
                if len(mc_rows) != exp_mc_total:
                    raise JournalCorruptionError(
                        f"MC_CATALOG_COUNT_TAMPERED: expected={exp_mc_total}, actual={len(mc_rows)}"
                    )
                for row in mc_rows:
                    if int(row[5]) != 0 or int(row[6]) != 0:
                        raise JournalCorruptionError(f"MC_SAFETY_INVARIANT_TAMPERED: case_key={row[0]!r}")
                recomputed_batch_sha = _sha256_text(
                    _canonical_json(
                        {
                            "source_artifact_sha256": exp_art_sha,
                            "profile_id": exp_profile,
                            "funded_mult": exp_fm,
                            "row_hashes": {str(r[0]): str(r[1]) for r in mc_rows},
                        }
                    )
                )
                if recomputed_batch_sha != exp_batch_sha:
                    raise JournalCorruptionError(
                        f"MC_CATALOG_BATCH_SHA_TAMPERED: expected={exp_batch_sha}, actual={recomputed_batch_sha}"
                    )

            # 5. Verify every Wave 5+ recorded MC campaign batch hash & safety invariants
            for cid, camp_ev in sorted(latest_mc_campaigns.items()):
                exp_cnt = int(camp_ev.payload["total_mc_cases"])
                exp_bsha = str(camp_ev.payload["batch_sha256"])
                exp_asha = str(camp_ev.payload["source_artifact_sha256"])
                camp_rows = con.execute(
                    """
                    SELECT case_key, record_sha256, holdout_rows_analysed, order_send_count
                    FROM mc_cases_catalog
                    WHERE campaign_id = ?
                    ORDER BY case_key ASC
                    """,
                    [cid],
                ).fetchall()
                if len(camp_rows) != exp_cnt:
                    raise JournalCorruptionError(
                        f"MC_CAMPAIGN_COUNT_TAMPERED [{cid}]: expected={exp_cnt}, actual={len(camp_rows)}"
                    )
                for crow in camp_rows:
                    if int(crow[2]) != 0 or int(crow[3]) != 0:
                        raise JournalCorruptionError(
                            f"MC_CAMPAIGN_SAFETY_TAMPERED [{cid}]: case_key={crow[0]!r}"
                        )
                recomputed_csha = _sha256_text(
                    _canonical_json(
                        {
                            "campaign_id": cid,
                            "source_artifact_sha256": exp_asha,
                            "row_hashes": {str(r[0]): str(r[1]) for r in camp_rows},
                        }
                    )
                )
                if recomputed_csha != exp_bsha:
                    raise JournalCorruptionError(
                        f"MC_CAMPAIGN_BATCH_SHA_TAMPERED [{cid}]: expected={exp_bsha}, actual={recomputed_csha}"
                    )

        summary = self.get_catalog_summary()
        return {
            "verified": True,
            "registry_events": len(events),
            **summary,
        }


# ---------------------------------------------------------------------------
# High-Level Build/Backfill Orchestrator (Supports `write_output_path=None`)
# ---------------------------------------------------------------------------


def build_and_backfill_unified_catalog(
    *,
    duckdb_path: Path = DEFAULT_CATALOG_DUCKDB_PATH,
    registry_path: Path | None = None,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
    pareto_json_path: Path = DEFAULT_WAVE4_PARETO_PATH,
    legacy_sources: Sequence[Mapping[str, Any]] | None = None,
    write_output_path: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Build federated catalog, ingest 3 legacy DBs (1,342 trials), backfill 168 Wave 4 MC rows & verify."""
    with UnifiedEvaluationCatalog(
        duckdb_path=duckdb_path,
        registry_path=registry_path,
        taxonomy_path=taxonomy_path,
    ) as catalog:
        legacy_res = catalog.ingest_legacy_trials(sources=legacy_sources, repo_root=repo_root)
        backfill_res = catalog.backfill_wave4_pareto(pareto_json_path=pareto_json_path)
        integrity_res = catalog.verify_integrity()

    report: dict[str, Any] = {
        "schema_version": "naqex-wave5-unified-catalog-build-v1",
        "built_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": 0,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "duckdb_path": str(duckdb_path),
        "registry_path": str(registry_path or Path(duckdb_path).with_name("unified_eval_registry.sqlite3")),
        "duckdb_sha256": _sha256_file(Path(duckdb_path)),
        "legacy_federation": legacy_res,
        "wave4_backfill": backfill_res,
        "integrity": integrity_res,
    }
    if write_output_path is not None:
        out_p = Path(write_output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 5 Unified Evaluation Taxonomy & Federated DuckDB Catalog CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_bf = sub.add_parser("backfill", help="Ingest 3 legacy DuckDB tables & backfill 168 Wave 4 MC rows")
    p_bf.add_argument("--duckdb-path", type=Path, default=DEFAULT_CATALOG_DUCKDB_PATH)
    p_bf.add_argument("--registry-path", type=Path, default=DEFAULT_CATALOG_REGISTRY_PATH)
    p_bf.add_argument("--pareto-json", type=Path, default=DEFAULT_WAVE4_PARETO_PATH)
    p_bf.add_argument("--write-summary", type=Path, default=None)

    p_ver = sub.add_parser("verify", help="Verify read-only catalog integrity against SQLiteRunRegistry")
    p_ver.add_argument("--duckdb-path", type=Path, default=DEFAULT_CATALOG_DUCKDB_PATH)
    p_ver.add_argument("--registry-path", type=Path, default=DEFAULT_CATALOG_REGISTRY_PATH)

    p_sch = sub.add_parser("export-schema", help="Export Pydantic v2 JSON Schema for evaluation-scorecard@1.0.0")
    p_sch.add_argument("--output", type=Path, default=None)

    args = ap.parse_args(argv)
    if args.cmd == "backfill":
        res = build_and_backfill_unified_catalog(
            duckdb_path=args.duckdb_path,
            registry_path=args.registry_path,
            pareto_json_path=args.pareto_json,
            write_output_path=args.write_summary,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.cmd == "verify":
        with UnifiedEvaluationCatalog(
            duckdb_path=args.duckdb_path,
            registry_path=args.registry_path,
            read_only=True,
        ) as cat:
            res = cat.verify_integrity()
        print(json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.cmd == "export-schema":
        schema = export_scorecard_json_schema()
        text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8", newline="\n")
        else:
            print(text)
        return 0

    return 2


__all__ = [
    "AlphaLifecycleState",
    "AlphaRegistryEntry",
    "BottleneckItem",
    "CanonicalBlindnessTier",
    "DEFAULT_CATALOG_DUCKDB_PATH",
    "DEFAULT_CATALOG_REGISTRY_PATH",
    "DEFAULT_LEGACY_SOURCES",
    "DEFAULT_SCORECARD_SCHEMA_PATH",
    "DEFAULT_TAXONOMY_PATH",
    "DEFAULT_WAVE4_PARETO_PATH",
    "DataResolution",
    "DomainTier",
    "DomainTierThresholds",
    "EvalPhase",
    "EvalScope",
    "EvaluationInputRecord",
    "EvaluationScorecard",
    "EvaluationTaxonomyConfig",
    "EvidenceStage",
    "GRADE_LABEL_VI",
    "GRADE_RANK",
    "GradeBand",
    "HOLDOUT_CUTOFF_DATE",
    "HorizonPartitionPct",
    "LEGACY_UNINSTRUMENTED_LABEL_VI",
    "MetricIntervalBand",
    "MetricIntervalSpec",
    "NumericGradeBand",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PhaseGradeDetail",
    "PhaseMetricThreshold",
    "PhaseThresholdSpec",
    "PresentationState",
    "PricingRegime",
    "RiskSpectrumTier",
    "SCORECARD_CONTRACT_VERSION",
    "SCORECARD_SCHEMA_ID",
    "UnifiedEvaluationCatalog",
    "build_and_backfill_unified_catalog",
    "classify_metric_interval",
    "export_scorecard_json_schema",
    "grade_evaluation_record",
    "load_evaluation_taxonomy",
    "map_blindness_tier",
]


if __name__ == "__main__":
    raise SystemExit(main())
