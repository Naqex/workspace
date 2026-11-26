"""Pydantic v2 Single-Source-of-Truth (SSOT) schemas for Naqex quant configs and receipts.

All models are immutable (`frozen=True`), reject unknown keys (`extra="forbid"`),
reject `NaN`/`Inf` (`allow_inf_nan=False`), reject `bool` disguised as numbers,
validate IANA timezones via `zoneinfo.ZoneInfo`, reject future timestamps
(`> now_utc + 300s`), and strictly enforce unit suffixes:
  - `_frac` in `[0.0, 1.0]`
  - `_pct` in `[0.0, 100.0]`
  - `_usd` finite non-negative USD
  - `_cal_days`, `_trading_days` strict non-negative integer
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

MAX_FUTURE_TIMESTAMP_SKEW_SEC = 300
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

SkillStage = Literal[
    "research-and-memory-ops",
    "strategy-research",
    "whitebox-prop-discovery",
    "quant-factory-ops",
    "strategy-qualification",
    "adversarial-self-audit",
    "naqex-node-ops",
    "evidence-continuity",
    "engineering-retrospective",
]

ExecutionStatus = Literal[
    "MEASURED_DEMO_EXECUTION",
    "TERMS_VERIFIED_EXECUTION_UNMEASURED",
    "LIVE_EXECUTION_VERIFIED",
]

DDAnchorTag = Literal[
    "DD_ANCHOR_BALANCE_VERIFIED",
    "DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET",
]

DailyDDAnchorMode = Literal[
    "MIDNIGHT_BALANCE_OVER_INITIAL",
    "MAX_BALANCE_EQUITY_OVER_ANCHOR",
    "PREV_DAY_BALANCE_IF_FLAT",
]

PhaseKey = Literal["p1", "p2", "funded"]


def _reject_bool_and_coerce_finite_float(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected finite int/float (not bool), got {type(value).__name__}")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("value must be finite (NaN/Inf forbidden)")
    return out


def _validate_strict_int(value: Any) -> int:
    if type(value) is not int:
        raise ValueError(f"expected strict int (not bool/float/str), got {type(value).__name__}")
    return value


def _validate_iana_timezone(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("reset_tz must be a non-empty IANA timezone string")
    tz = value.strip()
    if tz != value:
        raise ValueError("reset_tz must not have leading or trailing whitespace")
    if tz.upper().startswith(("UTC+", "UTC-", "GMT+", "GMT-")):
        raise ValueError(f"reset_tz must be a canonical IANA timezone, not fixed offset: {tz!r}")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
        raise ValueError(f"invalid IANA timezone: {tz!r}") from exc
    return tz


def _validate_verified_utc_input(value: Any) -> str | datetime:
    if not isinstance(value, (str, datetime)):
        raise ValueError(
            f"verified_utc must be an ISO-8601 string or timezone-aware datetime, not {type(value).__name__}"
        )
    if isinstance(value, str) and not value.strip():
        raise ValueError("verified_utc string must not be empty")
    return value


def _validate_verified_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware UTC")
    as_utc = value.astimezone(UTC)
    max_allowed = datetime.now(UTC) + timedelta(seconds=MAX_FUTURE_TIMESTAMP_SKEW_SEC)
    if as_utc > max_allowed:
        raise ValueError(
            f"verified_utc {as_utc.isoformat()} exceeds allowed future skew (+{MAX_FUTURE_TIMESTAMP_SKEW_SEC}s)"
        )
    return as_utc


def _validate_sha256_hex(value: Any) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError("expected lowercase 64-character hex SHA-256")
    return value


FiniteFloat = Annotated[float, BeforeValidator(_reject_bool_and_coerce_finite_float)]
FracFloat = Annotated[float, BeforeValidator(_reject_bool_and_coerce_finite_float), Field(ge=0.0, le=1.0)]
PctFloat = Annotated[float, BeforeValidator(_reject_bool_and_coerce_finite_float), Field(ge=0.0, le=100.0)]
NonNegUsdFloat = Annotated[float, BeforeValidator(_reject_bool_and_coerce_finite_float), Field(ge=0.0)]
PosUsdFloat = Annotated[float, BeforeValidator(_reject_bool_and_coerce_finite_float), Field(gt=0.0)]
PosMultFloat = Annotated[float, BeforeValidator(_reject_bool_and_coerce_finite_float), Field(gt=0.0)]
StrictNonNegInt = Annotated[int, BeforeValidator(_validate_strict_int), Field(ge=0)]
StrictPosInt = Annotated[int, BeforeValidator(_validate_strict_int), Field(ge=1)]
IanaTimezone = Annotated[str, BeforeValidator(_validate_iana_timezone)]
VerifiedUtcDatetime = Annotated[
    datetime,
    BeforeValidator(_validate_verified_utc_input),
    AfterValidator(_validate_verified_utc),
]
Sha256Hex = Annotated[str, BeforeValidator(_validate_sha256_hex)]


class SSOTBaseModel(BaseModel):
    """Frozen, strict, NaN/Inf-forbidding base model with unit-suffix enforcement."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def _enforce_unit_suffix_invariants(self) -> SSOTBaseModel:
        for field_name in type(self).model_fields:
            val = getattr(self, field_name)
            if val is None:
                continue
            if field_name.endswith("_frac"):
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not (0.0 <= float(val) <= 1.0):
                    raise ValueError(f"{field_name} must be a fraction in [0.0, 1.0], got {val!r}")
            elif field_name.endswith("_pct"):
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not (0.0 <= float(val) <= 100.0):
                    raise ValueError(f"{field_name} must be a percentage in [0.0, 100.0], got {val!r}")
            elif field_name.endswith("_usd"):
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(float(val)):
                    raise ValueError(f"{field_name} must be a finite USD amount, got {val!r}")
            elif field_name.endswith(("_cal_days", "_trading_days")):
                if type(val) is not int or val < 0:
                    raise ValueError(f"{field_name} must be a non-negative integer, got {val!r}")
        return self

    def fingerprint(self) -> str:
        """Canonical SHA-256 hash of this frozen model's JSON serialization."""
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class FxRatesConfig(SSOTBaseModel):
    """Single canonical FX conversion rate source (USD/VND, EUR/USD, EUR/VND)."""

    schema_version: Literal["naqex-ssot-fx-rates-v1"] = "naqex-ssot-fx-rates-v1"
    usd_vnd: PosUsdFloat
    eur_usd: PosUsdFloat
    eur_vnd: PosUsdFloat
    usd_eur: PosUsdFloat | None = None
    verified_utc: VerifiedUtcDatetime
    provider_timestamp_utc: VerifiedUtcDatetime | None = None
    source: str = Field(min_length=1, max_length=256)
    source_url: str | None = Field(default=None, min_length=1, max_length=512)
    rate_status: Literal["LIVE_PUBLIC_API", "OFFICIAL_CHECKOUT", "MANUAL_VERIFIED"] = "LIVE_PUBLIC_API"

    @model_validator(mode="after")
    def _validate_cross_rate_consistency(self) -> FxRatesConfig:
        implied_eur_vnd = self.eur_usd * self.usd_vnd
        rel_err = abs(self.eur_vnd - implied_eur_vnd) / self.eur_vnd
        if rel_err > 0.015:
            raise ValueError(f"eur_vnd ({self.eur_vnd}) inconsistent with eur_usd*usd_vnd ({implied_eur_vnd:.2f})")
        if self.usd_eur is not None:
            inv_err = abs(self.usd_eur * self.eur_usd - 1.0)
            if inv_err > 0.01:
                raise ValueError(f"usd_eur ({self.usd_eur}) inconsistent with 1/eur_usd ({1.0 / self.eur_usd:.6f})")
        return self


class FirmTierContract(SSOTBaseModel):
    """Single prop firm program tier contract with strict unit suffixes and VN availability."""

    contract_id: str = Field(min_length=1, max_length=128)
    firm_id: str = Field(min_length=1, max_length=64)
    program_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    account_type: Literal[
        "Standard",
        "Swing",
        "HighStakesClassic",
        "HighStakesNew",
        "TwoStepPro",
        "OneStep",
        "Instant",
    ]
    steps: StrictNonNegInt = Field(le=2)
    capital_usd: PosUsdFloat
    available_vn: bool
    unavailable_reason_vn: str | None = Field(default=None, max_length=256)
    fee_orig_usd: NonNegUsdFloat | None = None
    fee_promo_usd: NonNegUsdFloat | None = None
    promo_discount_frac: FracFloat = 0.0
    promo_label: str = Field(default="NONE", min_length=1, max_length=128)
    p1_target_frac: FracFloat | None = None
    p2_target_frac: FracFloat | None = None
    daily_loss_limit_frac: FracFloat
    static_loss_limit_frac: FracFloat
    dd_type: Literal["static", "eod_trailing", "intraday_trailing"] = "static"
    daily_pause_only: bool = False
    dd_anchor_tag: DDAnchorTag
    daily_dd_anchor_mode: DailyDDAnchorMode
    reset_tz: IanaTimezone
    min_trading_days: StrictNonNegInt
    min_profitable_days: StrictNonNegInt = 0
    profitable_day_threshold_frac: FracFloat = 0.0
    payout_split_frac: FracFloat
    payout_split_max_frac: FracFloat | None = None
    payout_cycle_cal_days: StrictPosInt
    payout_settlement_lag_cal_days: StrictNonNegInt = 3
    min_payout_usd: NonNegUsdFloat
    fee_refund_external_cash_frac: FracFloat
    fee_refund_hub_credit_frac: FracFloat = 0.0
    fee_refund_milestone: Literal[
        "FIRST_PAYOUT",
        "THIRD_PAYOUT",
        "NON_REFUNDABLE",
        "SPLIT_HUB_AND_FIRST_PAYOUT",
    ]
    card_fx_fee_frac: FracFloat = 0.025
    withdrawal_fee_frac: FracFloat = 0.015
    leverage_fx: StrictPosInt
    leverage_indices: StrictPosInt
    news_restricted_eval: bool
    news_restricted_funded: bool
    news_window_sec: StrictNonNegInt = 0
    overnight_weekend_allowed: bool
    requires_ea_written_clearance: bool = False
    execution_status: ExecutionStatus
    verified_utc: VerifiedUtcDatetime
    source_urls: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_contract_semantics(self) -> FirmTierContract:
        if self.daily_loss_limit_frac <= 0.0:
            raise ValueError("daily_loss_limit_frac must be > 0")
        if self.static_loss_limit_frac <= 0.0:
            raise ValueError("static_loss_limit_frac must be > 0")
        if self.daily_loss_limit_frac > self.static_loss_limit_frac:
            raise ValueError("daily_loss_limit_frac cannot exceed static_loss_limit_frac")
        if self.available_vn:
            if self.fee_orig_usd is None or self.fee_orig_usd <= 0.0:
                raise ValueError(f"{self.contract_id}: available_vn=True requires fee_orig_usd > 0")
        if self.fee_promo_usd is not None and self.fee_orig_usd is not None:
            if self.fee_promo_usd > self.fee_orig_usd + 1e-9:
                raise ValueError(f"{self.contract_id}: fee_promo_usd cannot exceed fee_orig_usd")
        if self.steps >= 1 and (self.p1_target_frac is None or self.p1_target_frac <= 0.0):
            raise ValueError(f"{self.contract_id}: steps >= 1 requires p1_target_frac > 0")
        if self.steps >= 2 and (self.p2_target_frac is None or self.p2_target_frac <= 0.0):
            raise ValueError(f"{self.contract_id}: steps == 2 requires p2_target_frac > 0")
        if self.fee_refund_external_cash_frac + self.fee_refund_hub_credit_frac > 1.0 + 1e-9:
            raise ValueError(f"{self.contract_id}: total refund fractions exceed 1.0")
        if self.payout_split_max_frac is not None and self.payout_split_max_frac < self.payout_split_frac:
            raise ValueError(f"{self.contract_id}: payout_split_max_frac cannot be below payout_split_frac")
        return self


class SSOTFirmsCatalog(SSOTBaseModel):
    """Canonical reconciled prop-firm catalog validated fail-closed."""

    schema_version: Literal["naqex-ssot-firms-catalog-v1"] = "naqex-ssot-firms-catalog-v1"
    updated_utc: VerifiedUtcDatetime
    staleness_max_cal_days: StrictPosInt = 7
    vn_card_fx_fee_frac: FracFloat = 0.025
    vn_withdrawal_fee_frac: FracFloat = 0.015
    vn_fx_conversion_spread_frac: FracFloat = 0.005
    contracts: dict[str, FirmTierContract]
    order_send_count: Literal[0] = 0
    holdout_rows_analysed: Literal[0] = 0

    @model_validator(mode="after")
    def _validate_contracts_map(self) -> SSOTFirmsCatalog:
        if not self.contracts:
            raise ValueError("contracts must not be empty")
        for key, contract in self.contracts.items():
            if key != contract.contract_id:
                raise ValueError(f"contracts key {key!r} must match contract_id {contract.contract_id!r}")
        return self


class EngineBaseRiskSpec(SSOTBaseModel):
    """Canonical base risk specification for one core strategy engine."""

    engine_id: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=32)
    magic: StrictPosInt
    base_risk_pct: PctFloat
    base_risk_frac: FracFloat
    signals_array_index: StrictNonNegInt

    @model_validator(mode="after")
    def _validate_pct_frac_parity(self) -> EngineBaseRiskSpec:
        if abs(self.base_risk_pct / 100.0 - self.base_risk_frac) > 1e-9:
            raise ValueError(
                f"{self.engine_id}: base_risk_pct ({self.base_risk_pct}) != "
                f"base_risk_frac*100 ({self.base_risk_frac * 100})"
            )
        return self


class FactorClusterCaps(SSOTBaseModel):
    """Directional factor and account concurrent open SL risk caps (fractions of equity)."""

    per_symbol_frac: FracFloat
    usd_directional_frac: FracFloat
    jpy_directional_frac: FracFloat
    us100_index_frac: FracFloat
    total_open_account_frac: FracFloat

    @model_validator(mode="after")
    def _validate_cap_ordering(self) -> FactorClusterCaps:
        for name, val in (
            ("per_symbol_frac", self.per_symbol_frac),
            ("usd_directional_frac", self.usd_directional_frac),
            ("jpy_directional_frac", self.jpy_directional_frac),
            ("us100_index_frac", self.us100_index_frac),
        ):
            if val <= 0.0:
                raise ValueError(f"{name} must be > 0")
            if val > self.total_open_account_frac + 1e-12:
                raise ValueError(
                    f"{name} ({val}) cannot exceed total_open_account_frac ({self.total_open_account_frac})"
                )
        return self


class PhaseRiskProfile(SSOTBaseModel):
    """Per-phase sizing, ProfitLock, kill-switch, cluster caps, and news guard contract."""

    base_phase_mult: PosMultFloat
    profit_lock_trigger_of_target_frac: FracFloat
    profit_lock_pct: PctFloat
    profit_lock_mult: PosMultFloat
    kill_daily_dd_frac: FracFloat
    kill_static_dd_frac: FracFloat
    symcap_frac: FracFloat
    factor_caps: FactorClusterCaps
    enable_red_news_guard: bool

    @model_validator(mode="after")
    def _validate_phase_limits(self) -> PhaseRiskProfile:
        if self.kill_daily_dd_frac <= 0.0 or self.kill_static_dd_frac <= 0.0:
            raise ValueError("kill_daily_dd_frac and kill_static_dd_frac must be > 0")
        if self.kill_daily_dd_frac > self.kill_static_dd_frac:
            raise ValueError("kill_daily_dd_frac cannot exceed kill_static_dd_frac")
        if abs(self.symcap_frac - self.factor_caps.per_symbol_frac) > 1e-12:
            raise ValueError("symcap_frac must match factor_caps.per_symbol_frac")
        if self.profit_lock_pct > 0.0 and self.profit_lock_mult > self.base_phase_mult + 1e-12:
            raise ValueError("profit_lock_mult cannot exceed base_phase_mult when ProfitLock is enabled")
        return self


class RiskBrakeProfile(SSOTBaseModel):
    """Canonical portfolio risk-brake profile (relative AMBER/RED, ProfitLock, SYMCAP, dailyHeadroom)."""

    profile_id: str = Field(min_length=1, max_length=64)
    portfolio_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=256)
    brake_mode: Literal["RELATIVE_TO_PHASE_MULT"] = "RELATIVE_TO_PHASE_MULT"
    amber_dd_frac: FracFloat
    amber_mult: PosMultFloat
    red_dd_frac: FracFloat
    red_mult: PosMultFloat
    daily_headroom_taper_threshold_frac: FracFloat = 0.02
    daily_headroom_taper_floor_mult: PosMultFloat = 0.25
    red_news_pad_sec: StrictNonNegInt = 300
    red_news_hard_ban_sec: StrictNonNegInt = 135
    engines: tuple[EngineBaseRiskSpec, ...]
    phases: dict[PhaseKey, PhaseRiskProfile]

    @model_validator(mode="after")
    def _validate_risk_profile(self) -> RiskBrakeProfile:
        if self.amber_dd_frac <= 0.0 or self.red_dd_frac <= self.amber_dd_frac:
            raise ValueError("must satisfy 0 < amber_dd_frac < red_dd_frac")
        if not (0.0 < self.red_mult < self.amber_mult < 1.0):
            raise ValueError("must satisfy 0 < red_mult < amber_mult < 1.0 for relative AMBER/RED brakes")
        if not (0.0 < self.daily_headroom_taper_floor_mult <= 1.0):
            raise ValueError("daily_headroom_taper_floor_mult must be in (0.0, 1.0]")
        if self.red_news_hard_ban_sec > self.red_news_pad_sec:
            raise ValueError("red_news_hard_ban_sec cannot exceed red_news_pad_sec")
        if not self.engines:
            raise ValueError("engines must not be empty")
        if len({e.engine_id for e in self.engines}) != len(self.engines):
            raise ValueError("engine_id entries must be unique")
        if len({e.magic for e in self.engines}) != len(self.engines):
            raise ValueError("engine magic entries must be unique")
        required_phases: set[PhaseKey] = {"p1", "p2", "funded"}
        if set(self.phases.keys()) != required_phases:
            raise ValueError("phases must contain exact keys: p1, p2, funded")
        return self


class SSOTRiskProfiles(SSOTBaseModel):
    """Root container for canonical risk-brake profiles."""

    schema_version: Literal["naqex-ssot-risk-profiles-v1"] = "naqex-ssot-risk-profiles-v1"
    updated_utc: VerifiedUtcDatetime
    primary_profile_id: str = Field(min_length=1, max_length=64)
    profiles: dict[str, RiskBrakeProfile]
    order_send_count: Literal[0] = 0
    holdout_rows_analysed: Literal[0] = 0

    @model_validator(mode="after")
    def _validate_profiles_map(self) -> SSOTRiskProfiles:
        if self.primary_profile_id not in self.profiles:
            raise ValueError(f"primary_profile_id {self.primary_profile_id!r} not found in profiles")
        for key, profile in self.profiles.items():
            if key != profile.profile_id:
                raise ValueError(f"profiles key {key!r} must match profile_id {profile.profile_id!r}")
        return self


class NegativeMutationRecord(SSOTBaseModel):
    """Proof that a deliberate realistic defect flips an audited gate to FAIL."""

    mutation_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)
    expected_outcome: Literal["FAIL_CLOSED"] = "FAIL_CLOSED"
    observed_failed: bool
    evidence_ref: str = Field(min_length=1, max_length=256)


class AdversarialAuditReceipt(SSOTBaseModel):
    """Machine-readable JSON receipt for `adversarial-self-audit`."""

    schema_version: Literal["naqex-adversarial-audit-receipt-v1"] = "naqex-adversarial-audit-receipt-v1"
    audit_id: str = Field(min_length=1, max_length=128)
    target_path: str = Field(min_length=1, max_length=512)
    target_sha256: Sha256Hex
    audited_utc: VerifiedUtcDatetime
    auditor_role: str = Field(default="independent-verifier", min_length=1, max_length=128)
    vectors_checked: tuple[str, ...] = Field(min_length=1)
    negative_mutations: tuple[NegativeMutationRecord, ...]
    caveats: tuple[str, ...] = ()
    passed: bool
    holdout_rows_analysed: Literal[0] = 0
    order_send_count: Literal[0] = 0

    @model_validator(mode="after")
    def _validate_audit_verdict(self) -> AdversarialAuditReceipt:
        if len(set(self.vectors_checked)) != len(self.vectors_checked):
            raise ValueError("vectors_checked must not contain duplicates")
        if self.passed:
            if not self.negative_mutations:
                raise ValueError("passed audit receipt requires at least 1 negative_mutation proof")
            if not all(m.observed_failed for m in self.negative_mutations):
                raise ValueError("passed audit receipt requires every negative_mutation to have observed_failed=True")
        return self


class HandoffEnvelope(SSOTBaseModel):
    """Typed JSON handoff contract linking the 9 Naqex skill stages."""

    schema_version: Literal["naqex-skill-handoff-v1"] = "naqex-skill-handoff-v1"
    handoff_id: str = Field(min_length=1, max_length=128)
    from_stage: SkillStage
    to_stage: SkillStage
    created_utc: VerifiedUtcDatetime
    artifact_paths: tuple[str, ...] = Field(min_length=1)
    artifact_sha256: dict[str, Sha256Hex]
    summary: str = Field(min_length=1, max_length=2048)
    status: Literal["READY", "BLOCKED", "VERIFIED", "REJECTED"]
    audit_receipt_sha256: Sha256Hex | None = None
    caveats: tuple[str, ...] = ()
    holdout_rows_analysed: Literal[0] = 0
    order_send_count: Literal[0] = 0
    execution_capability: Literal[False] = False

    @model_validator(mode="after")
    def _validate_handoff(self) -> HandoffEnvelope:
        if self.from_stage == self.to_stage:
            raise ValueError(f"from_stage and to_stage must differ (both {self.from_stage!r})")
        if len(set(self.artifact_paths)) != len(self.artifact_paths):
            raise ValueError("artifact_paths must be unique")
        if not self.artifact_sha256:
            raise ValueError("artifact_sha256 must hash at least one artifact")
        unknown_keys = set(self.artifact_sha256) - set(self.artifact_paths)
        if unknown_keys:
            raise ValueError(f"artifact_sha256 keys not listed in artifact_paths: {sorted(unknown_keys)}")
        if self.status == "VERIFIED" and self.audit_receipt_sha256 is None:
            raise ValueError("status='VERIFIED' requires audit_receipt_sha256")
        return self


__all__ = [
    "AdversarialAuditReceipt",
    "DDAnchorTag",
    "DailyDDAnchorMode",
    "EngineBaseRiskSpec",
    "ExecutionStatus",
    "FactorClusterCaps",
    "FirmTierContract",
    "FxRatesConfig",
    "HandoffEnvelope",
    "MAX_FUTURE_TIMESTAMP_SKEW_SEC",
    "NegativeMutationRecord",
    "PhaseKey",
    "PhaseRiskProfile",
    "RiskBrakeProfile",
    "SSOTBaseModel",
    "SSOTFirmsCatalog",
    "SSOTRiskProfiles",
    "SkillStage",
]
