"""Fleet Admission & Edge-Case Guards (E1..E6), OPS-2 Composition & FTMO Scaling Tracker.

Total Offensive #4 Wave 1B (`W4-G10`): strictly deterministic, fail-closed offline guard engine
protecting multi-account prop fleet admission and runtime operation across all 6 canonical guards:
  - `E1_EVAL_FAIL_COOLDOWN`: trailing 30-day eval failures (`>= 2` -> block new ticket admission
    until a verified signed `OPS-6` forensic review receipt is supplied).
  - `E2_FUNDED_DD_FREEZE`: if ANY active Funded account (`S5`/`S6`/`E2`) reaches Amber (`DD >= 3.5%`)
    or Red (`DD >= 6.0%`) or `OPS-4` Amber/Red, immediately freeze opening ANY new Challenge across
    the entire fleet and emit the objective scale factor (`0.5x` Amber / `0.0x` Red).
  - `E3_FUNDED_BREACH_POSTMORTEM`: if ANY Funded breach exists without a signed `OPS-6` postmortem
    classifying `BOT_BUG | SLIPPAGE | VARIANCE`, lock entire fleet admission.
  - `E4_CAP_OR_VPS_OVERFLOW`: enforce FTMO `400,000 USD` total active Funded cap (`200,000 USD` max
    single Challenge), firm contract availability & slot limits from `firms_catalog.json` +
    `fleet_policy`, AND `naqex-node1` VPS capacity budget (CPU / RAM / max concurrent MT5 terminals).
  - `E5_CROSS_ACCOUNT_OPPOSITE_HEDGE`: detect & reject same-firm opposite directional exposure
    (canonical symbol root parity), duplicate/overlapping `MagicNumber` ranges across accounts,
    and duplicate (or forbidden `E:` drive) MT5 Portable directory paths.
  - `E6_INACTIVITY_OR_FEED_STALE_LOCK`: track trading inactivity (`21d` warning / `27d` urgent /
    `30d` fail-closed lock), stale heartbeat (`heartbeat.utc_ts < flag_write_utc_ts` or age > limit,
    `None` heartbeat/open_positions fail-closed), NTP offset `>= 1000 ms`, and `PRESET_SHA256_DRIFT`.

Also provides the **FTMO Scaling Plan Tracker** (`+25%` of original base allocation every `4` months
when `>= +10%` net profit and `>= 2` processed payouts, scaling up to `2,000,000 USD` & `90%` split).

HARD SAFETY & IMMUTABILITY INVARIANTS (`[ARCH-02]`, `G02`, `G11`, `G16`):
  - Strictly offline & read-only on trading systems:
      `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`.
  - Holdout 2025+ strictly sealed:
      `HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `HOLDOUT_ROWS_ANALYSED = 0`.
  - ZERO `MetaTrader5` imports, ZERO SSH/network calls, ZERO bare `assert` statements.
  - Composes `prop_lifecycle_orchestrator.py`, `account_phase_preflight.py`, `firms_catalog.json`,
    and `quant_core.tca` cleanly without modifying any upstream or immutable files.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

QUANT_FACTORY_DIR: Final[Path] = Path(__file__).resolve().parents[1]
AI_ENGINES_DIR: Final[Path] = QUANT_FACTORY_DIR.parent
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.tca import canonical_payload_sha256  # noqa: E402

from quant_factory.live_ops.account_phase_preflight import (  # noqa: E402
    INACTIVITY_AMBER_DAYS,
    INACTIVITY_HARD_LIMIT_DAYS,
    INACTIVITY_RED_DAYS,
    PreflightReport,
    canonical_symbol_root,
    check_eval_vs_funded_lock,
    check_multi_account_compliance,
)
from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE  # noqa: E402
from quant_factory.wave4 import ORDER_SEND_CAPABLE as _WAVE4_ORDER_SEND_CAPABLE  # noqa: E402
from quant_factory.wave4.prop_lifecycle_orchestrator import (  # noqa: E402
    DEFAULT_FIRMS_CATALOG_PATH,
    DEFAULT_SAMPLE_FIXTURE_PATH,
    FleetAccount,
    FleetPolicy,
    FleetState,
    PropFleetOrchestrator,
    TransitionEvent,
    load_firms_catalog,
)

# ---------------------------------------------------------------------------
# Hard Safety, Guard & Scaling Constants
# ---------------------------------------------------------------------------
ORDER_SEND_CAPABLE: bool = _WAVE4_ORDER_SEND_CAPABLE
ORDER_SEND_COUNT: int = 0
HOLDOUT_ROWS_ANALYSED: Final[int] = 0

FLEET_GUARDS_SCHEMA_VERSION: Final[str] = "naqex-prop-fleet-guards-v1"

GUARD_E1: Final[str] = "E1_EVAL_FAIL_COOLDOWN"
GUARD_E2: Final[str] = "E2_FUNDED_DD_FREEZE"
GUARD_E3: Final[str] = "E3_FUNDED_BREACH_POSTMORTEM"
GUARD_E4: Final[str] = "E4_CAP_OR_VPS_OVERFLOW"
GUARD_E5: Final[str] = "E5_CROSS_ACCOUNT_OPPOSITE_HEDGE"
GUARD_E6: Final[str] = "E6_INACTIVITY_OR_FEED_STALE_LOCK"

ALL_GUARD_IDS: Final[tuple[str, ...]] = (
    GUARD_E1,
    GUARD_E2,
    GUARD_E3,
    GUARD_E4,
    GUARD_E5,
    GUARD_E6,
)

# E1 thresholds
E1_TRAILING_WINDOW_DAYS: Final[int] = 30
E1_MAX_FAILED_EVALS_BEFORE_BLOCK: Final[int] = 2

# E2 thresholds
E2_AMBER_DD_PCT: Final[float] = 3.5
E2_RED_DD_PCT: Final[float] = 6.0
E2_SCALE_GREEN: Final[float] = 1.0
E2_SCALE_AMBER: Final[float] = 0.5
E2_SCALE_RED: Final[float] = 0.0

# E3 postmortem classification contract
VALID_OPS6_BREACH_CLASSES: Final[frozenset[str]] = frozenset({"BOT_BUG", "SLIPPAGE", "VARIANCE"})

# E4 FTMO & firm cap constants + naqex-node1 VPS defaults
FTMO_MAX_ACTIVE_FUNDED_USD: Final[float] = 400_000.0
FTMO_MAX_SINGLE_CHALLENGE_USD: Final[float] = 200_000.0
DEFAULT_FIRM_CAP_LIMITS: Final[dict[str, dict[str, float]]] = {
    "ftmo": {
        "max_active_funded_usd": FTMO_MAX_ACTIVE_FUNDED_USD,
        "max_single_challenge_usd": FTMO_MAX_SINGLE_CHALLENGE_USD,
    },
    "the5ers": {
        "max_active_funded_usd": 400_000.0,
        "max_single_challenge_usd": 100_000.0,
    },
    "ic_funded": {
        "max_active_funded_usd": 200_000.0,
        "max_single_challenge_usd": 100_000.0,
    },
}

DEFAULT_VPS_NODE_NAME: Final[str] = "naqex-node1"
DEFAULT_VPS_MAX_CPU_PCT: Final[float] = 75.0
DEFAULT_VPS_MIN_FREE_RAM_GB: Final[float] = 2.0
DEFAULT_VPS_RAM_PER_TERMINAL_GB: Final[float] = 0.5
DEFAULT_VPS_MIN_POST_ADD_RAM_GB: Final[float] = 1.5
DEFAULT_VPS_MAX_RAM_UTIL_PCT: Final[float] = 85.0
DEFAULT_VPS_MAX_MT5_TERMINALS: Final[int] = 6
DEFAULT_VPS_MIN_DISK_C_FREE_GB: Final[float] = 20.0

# E6 heartbeat & NTP thresholds
DEFAULT_MAX_HEARTBEAT_AGE_SEC: Final[float] = 180.0
DEFAULT_MAX_FUTURE_HEARTBEAT_SKEW_SEC: Final[float] = 5.0
DEFAULT_NTP_MAX_OFFSET_MS: Final[float] = 1000.0

# FTMO Scaling Plan official contract (+25% every 4m if >= +10% net & >= 2 payouts, up to 2M USD)
FTMO_SCALING_STEP_FRAC: Final[float] = 0.25
FTMO_SCALING_INTERVAL_MONTHS: Final[int] = 4
FTMO_SCALING_INTERVAL_CAL_DAYS: Final[int] = 120
FTMO_SCALING_MIN_NET_PROFIT_FRAC: Final[float] = 0.10
FTMO_SCALING_MIN_PAYOUTS: Final[int] = 2
FTMO_SCALING_MAX_CAPITAL_USD: Final[float] = 2_000_000.0
FTMO_SCALING_UPGRADED_SPLIT_FRAC: Final[float] = 0.90

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_VALID_TRAFFIC_LIGHTS: Final[frozenset[str]] = frozenset({"GREEN", "AMBER", "RED"})

_ACTIVE_EVAL_STATES: Final[frozenset[str]] = frozenset(
    {
        FleetState.S1_CHALLENGE_P1.value,
        FleetState.S3_CHALLENGE_P2.value,
    }
)
_ALL_EVAL_PIPELINE_STATES: Final[frozenset[str]] = frozenset(
    {
        FleetState.S1_CHALLENGE_P1.value,
        FleetState.S2_PASS_P1_HANDOFF.value,
        FleetState.S3_CHALLENGE_P2.value,
    }
)
_ACTIVE_FUNDED_STATES: Final[frozenset[str]] = frozenset(
    {
        FleetState.S5_FUNDED_ACTIVE.value,
        FleetState.S6_PAYOUT_AUDIT_AND_HARVEST.value,
        FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value,
    }
)
_COMMITTED_FUNDED_CAP_STATES: Final[frozenset[str]] = frozenset(
    {
        FleetState.S4_PASS_P2_TO_FUNDED_LOCK.value,
        FleetState.S5_FUNDED_ACTIVE.value,
        FleetState.S6_PAYOUT_AUDIT_AND_HARVEST.value,
        FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value,
        FleetState.E2_FUNDED_DD_FREEZE.value,
    }
)
_LIVE_RUNNING_STATES: Final[frozenset[str]] = frozenset(
    {
        FleetState.S1_CHALLENGE_P1.value,
        FleetState.S3_CHALLENGE_P2.value,
        FleetState.S5_FUNDED_ACTIVE.value,
        FleetState.S6_PAYOUT_AUDIT_AND_HARVEST.value,
    }
)
_OCCUPYING_FIRM_SLOT_STATES: Final[frozenset[str]] = frozenset(
    {
        FleetState.S1_CHALLENGE_P1.value,
        FleetState.S2_PASS_P1_HANDOFF.value,
        FleetState.S3_CHALLENGE_P2.value,
        FleetState.S4_PASS_P2_TO_FUNDED_LOCK.value,
        FleetState.S5_FUNDED_ACTIVE.value,
        FleetState.S6_PAYOUT_AUDIT_AND_HARVEST.value,
        FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value,
        FleetState.E2_FUNDED_DD_FREEZE.value,
    }
)
_PASSED_P1_OR_BEYOND_STATES: Final[frozenset[str]] = frozenset(
    {
        FleetState.S2_PASS_P1_HANDOFF.value,
        FleetState.S3_CHALLENGE_P2.value,
        FleetState.S4_PASS_P2_TO_FUNDED_LOCK.value,
        FleetState.S5_FUNDED_ACTIVE.value,
        FleetState.S6_PAYOUT_AUDIT_AND_HARVEST.value,
        FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value,
    }
)


# ---------------------------------------------------------------------------
# Fail-Closed Exception & Strict Runtime Safety Guard
# ---------------------------------------------------------------------------
class FleetGuardError(ValueError):
    """Fail-closed exception raised on hard safety-invariant tamper (e.g. ORDER_SEND_CAPABLE)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"[{code}] {message}")


def _assert_runtime_safety_invariants() -> None:
    if ORDER_SEND_CAPABLE is not False:
        raise FleetGuardError(
            "ORDER_SEND_CAPABLE_TAMPER",
            f"ORDER_SEND_CAPABLE must be strictly False, observed {ORDER_SEND_CAPABLE!r}.",
        )
    if type(ORDER_SEND_COUNT) is not int or ORDER_SEND_COUNT != 0:
        raise FleetGuardError(
            "ORDER_SEND_COUNT_TAMPER",
            f"ORDER_SEND_COUNT must be strictly 0, observed {ORDER_SEND_COUNT!r}.",
        )
    if _WAVE4_ORDER_SEND_CAPABLE is not False:
        raise FleetGuardError(
            "ORDER_SEND_CAPABLE_TAMPER",
            f"quant_factory.wave4.ORDER_SEND_CAPABLE must be strictly False, observed {_WAVE4_ORDER_SEND_CAPABLE!r}.",
        )


# ---------------------------------------------------------------------------
# Strict Primitive Parsers (Zero NaN / Inf / bool-as-int / None-as-0 Fail-Open)
# ---------------------------------------------------------------------------
def _parse_finite_float(
    value: Any,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    strictly_positive: bool = False,
) -> float | None:
    """Return finite float within bounds, or None on bool/None/NaN/Inf/str/out-of-range."""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    if not math.isfinite(out):
        return None
    if strictly_positive and out <= 0.0:
        return None
    if min_value is not None and out < min_value:
        return None
    if max_value is not None and out > max_value:
        return None
    return out


def _parse_strict_int(
    value: Any,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    """Return native int (strictly rejecting bool, float, None, str), or None."""
    if type(value) is not int:
        return None
    if min_value is not None and value < min_value:
        return None
    if max_value is not None and value > max_value:
        return None
    return value


def _parse_strict_bool(value: Any) -> bool | None:
    """Return native bool (strictly rejecting str/int/None), or None."""
    if type(value) is not bool:
        return None
    return value


def _is_valid_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_HEX_RE.match(value))


def _parse_utc_datetime(value: Any) -> datetime | None:
    """Parse timezone-aware datetime, ISO-8601 UTC string, or finite epoch seconds/ms into UTC datetime."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(UTC)
    if isinstance(value, (int, float)):
        fv = float(value)
        if not math.isfinite(fv) or fv < 0.0:
            return None
        if fv >= 1.0e12:
            fv = fv / 1000.0
        try:
            return datetime.fromtimestamp(fv, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        parsed_raw = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
        try:
            dt = datetime.fromisoformat(parsed_raw)
        except ValueError:
            return None
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None
        return dt.astimezone(UTC)
    return None


def _format_utc_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_firm_key(firm: Any) -> str:
    raw = str(firm or "").strip().lower()
    if raw.startswith("ftmo"):
        return "ftmo"
    if "5ers" in raw or "the5ers" in raw:
        return "the5ers"
    if "ic_funded" in raw or "icfunded" in raw or "ic funded" in raw:
        return "ic_funded"
    return raw


def _normalize_direction(direction: Any) -> str | None:
    if direction is None or isinstance(direction, bool):
        return None
    if isinstance(direction, (int, float)):
        fv = float(direction)
        if not math.isfinite(fv) or fv == 0.0:
            return None
        return "BUY" if fv > 0.0 else "SELL"
    if isinstance(direction, str):
        up = direction.strip().upper()
        if up in ("BUY", "LONG", "+1", "1", "B"):
            return "BUY"
        if up in ("SELL", "SHORT", "-1", "S"):
            return "SELL"
    return None


def _normalize_portable_dir(path_raw: Any) -> str | None:
    """Normalize a Windows/POSIX MT5 Portable directory path deterministically for collision detection."""
    if not isinstance(path_raw, str):
        return None
    stripped = path_raw.strip()
    if not stripped:
        return None
    norm = stripped.replace("/", "\\")
    while "\\\\" in norm:
        norm = norm.replace("\\\\", "\\")
    # Preserve drive root like `c:\` while removing trailing slashes elsewhere
    if len(norm) > 3:
        norm = norm.rstrip("\\")
    return norm.lower()


def _dedupe_codes(codes: Sequence[str]) -> tuple[str, ...]:
    seen: list[str] = []
    for code in codes:
        c = str(code).strip()
        if c and c not in seen:
            seen.append(c)
    return tuple(seen)


# ---------------------------------------------------------------------------
# Typed Contracts & Result Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VpsCapacityBudget:
    """Hardware & terminal concurrency budget for `naqex-node1`."""

    node_name: str = DEFAULT_VPS_NODE_NAME
    max_cpu_util_pct: float = DEFAULT_VPS_MAX_CPU_PCT
    min_free_ram_gb: float = DEFAULT_VPS_MIN_FREE_RAM_GB
    ram_per_terminal_gb: float = DEFAULT_VPS_RAM_PER_TERMINAL_GB
    min_post_add_ram_gb: float = DEFAULT_VPS_MIN_POST_ADD_RAM_GB
    max_ram_util_pct: float = DEFAULT_VPS_MAX_RAM_UTIL_PCT
    max_mt5_terminals: int = DEFAULT_VPS_MAX_MT5_TERMINALS
    min_disk_c_free_gb: float = DEFAULT_VPS_MIN_DISK_C_FREE_GB

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_name": self.node_name,
            "max_cpu_util_pct": self.max_cpu_util_pct,
            "min_free_ram_gb": self.min_free_ram_gb,
            "ram_per_terminal_gb": self.ram_per_terminal_gb,
            "min_post_add_ram_gb": self.min_post_add_ram_gb,
            "max_ram_util_pct": self.max_ram_util_pct,
            "max_mt5_terminals": self.max_mt5_terminals,
            "min_disk_c_free_gb": self.min_disk_c_free_gb,
        }


@dataclass(frozen=True)
class GuardResult:
    """Deterministic verdict for a single Fleet Guard (`E1..E6`)."""

    guard_id: str
    passed: bool
    blocking: bool
    status: str  # PASS | WARNING | URGENT | BLOCK
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "guard_id": self.guard_id,
            "passed": self.passed,
            "blocking": self.blocking,
            "status": self.status,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "details": self.details,
        }


@dataclass(frozen=True)
class AccountScalingStatus:
    """FTMO Scaling Plan status for a single Funded account."""

    account_id: str
    firm_id: str
    state: str
    eligible: bool
    at_max_cap: bool
    initial_capital_usd: float
    current_capital_usd: float
    next_capital_usd: float
    increment_usd: float
    current_payout_split_frac: float
    next_payout_split_frac: float
    elapsed_days: float
    elapsed_months: float
    net_profit_frac: float
    payouts_in_window: int
    missing_requirements: tuple[str, ...] = ()
    status_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "firm_id": self.firm_id,
            "state": self.state,
            "eligible": self.eligible,
            "at_max_cap": self.at_max_cap,
            "initial_capital_usd": round(self.initial_capital_usd, 2),
            "current_capital_usd": round(self.current_capital_usd, 2),
            "next_capital_usd": round(self.next_capital_usd, 2),
            "increment_usd": round(self.increment_usd, 2),
            "current_payout_split_frac": round(self.current_payout_split_frac, 4),
            "next_payout_split_frac": round(self.next_payout_split_frac, 4),
            "elapsed_days": round(self.elapsed_days, 2),
            "elapsed_months": round(self.elapsed_months, 3),
            "net_profit_frac": round(self.net_profit_frac, 6),
            "payouts_in_window": self.payouts_in_window,
            "missing_requirements": list(self.missing_requirements),
            "status_reason": self.status_reason,
        }


@dataclass(frozen=True)
class ScalingTrackerSummary:
    """Fleet-wide FTMO Scaling Plan tracker (`+25%` every `4` months up to `2,000,000 USD`)."""

    step_frac: float = FTMO_SCALING_STEP_FRAC
    interval_months: int = FTMO_SCALING_INTERVAL_MONTHS
    min_net_profit_frac: float = FTMO_SCALING_MIN_NET_PROFIT_FRAC
    min_payouts: int = FTMO_SCALING_MIN_PAYOUTS
    max_capital_usd: float = FTMO_SCALING_MAX_CAPITAL_USD
    eligible_count: int = 0
    eligible_account_ids: tuple[str, ...] = ()
    accounts: tuple[AccountScalingStatus, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_frac": self.step_frac,
            "interval_months": self.interval_months,
            "min_net_profit_frac": self.min_net_profit_frac,
            "min_payouts": self.min_payouts,
            "max_capital_usd": self.max_capital_usd,
            "eligible_count": self.eligible_count,
            "eligible_account_ids": list(self.eligible_account_ids),
            "accounts": [a.to_dict() for a in self.accounts],
        }


@dataclass(frozen=True)
class AdmissionVerdict:
    """Structured fail-closed verdict emitted by `evaluate_fleet_admission`."""

    allowed: bool
    active_guards: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    scaling_eligibility: ScalingTrackerSummary
    order_send_capable: bool = False
    order_send_count: int = 0
    holdout_cutoff_date: str = HOLDOUT_CUTOFF_DATE
    holdout_rows_analysed: int = HOLDOUT_ROWS_ANALYSED
    evaluated_utc: str = ""
    fleet_scale_factor: float = 1.0
    warnings: tuple[str, ...] = ()
    guard_results: dict[str, GuardResult] = field(default_factory=dict)
    proposed_account_id: str = ""
    schema_version: str = FLEET_GUARDS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.order_send_capable is not False:
            raise FleetGuardError(
                "ORDER_SEND_CAPABLE_TAMPER",
                f"AdmissionVerdict.order_send_capable must be strictly False, got {self.order_send_capable!r}.",
            )
        if type(self.order_send_count) is not int or self.order_send_count != 0:
            raise FleetGuardError(
                "ORDER_SEND_COUNT_TAMPER",
                f"AdmissionVerdict.order_send_count must be strictly 0, got {self.order_send_count!r}.",
            )
        if type(self.holdout_rows_analysed) is not int or self.holdout_rows_analysed != 0:
            raise FleetGuardError(
                "HOLDOUT_SEAL_BREACH",
                f"AdmissionVerdict.holdout_rows_analysed must be strictly 0, got {self.holdout_rows_analysed!r}.",
            )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "allowed": self.allowed,
            "active_guards": list(self.active_guards),
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "fleet_scale_factor": round(self.fleet_scale_factor, 4),
            "proposed_account_id": self.proposed_account_id,
            "evaluated_utc": self.evaluated_utc,
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_cutoff_date": self.holdout_cutoff_date,
            "holdout_rows_analysed": 0,
            "guard_results": {k: v.to_dict() for k, v in self.guard_results.items()},
            "scaling_eligibility": self.scaling_eligibility.to_dict(),
        }
        payload["report_sha256"] = canonical_payload_sha256(payload)
        return payload


# ---------------------------------------------------------------------------
# Ledger & Account Normalization (Composes PropFleetOrchestrator + Raw Dict)
# ---------------------------------------------------------------------------
def _account_to_record(acct: FleetAccount | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(acct, FleetAccount):
        return acct.to_dict()
    if isinstance(acct, Mapping):
        rec = dict(acct)
        if isinstance(rec.get("state"), FleetState):
            rec["state"] = rec["state"].value
        return rec
    return {}


def _transition_to_record(ev: TransitionEvent | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(ev, TransitionEvent):
        return ev.to_dict()
    if isinstance(ev, Mapping):
        return dict(ev)
    return {}


def _extract_ledger_view(
    ledger: PropFleetOrchestrator | Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any], list[str]]:
    """Normalize a `PropFleetOrchestrator` or `fleet_ledger.json` dict fail-closed."""
    errors: list[str] = []
    if ledger is None:
        return [], [], {}, {}, ["LEDGER_MISSING_FAIL_CLOSED"]

    if isinstance(ledger, PropFleetOrchestrator):
        accounts = [ledger.accounts[k].to_dict() for k in sorted(ledger.accounts.keys())]
        transitions = [ev.to_dict() for ev in ledger.transitions]
        policy = ledger.fleet_policy.to_dict(usd_vnd_rate=ledger.usd_vnd_rate)
        meta: dict[str, Any] = {
            "ledger_id": ledger.ledger_id,
            "ops6_eval_receipt": getattr(ledger, "ops6_eval_receipt", None),
            "ops6_postmortems": getattr(ledger, "ops6_postmortems", None),
            "active_signals": getattr(ledger, "active_signals", None),
        }
        return accounts, transitions, policy, meta, errors

    if not isinstance(ledger, Mapping):
        return [], [], {}, {}, ["LEDGER_INVALID_TYPE"]

    if "order_send_capable" in ledger and ledger.get("order_send_capable") is not False:
        raise FleetGuardError(
            "ORDER_SEND_CAPABLE_TAMPER",
            f"Ledger payload order_send_capable must be strictly False, got {ledger.get('order_send_capable')!r}.",
        )
    if "order_send_count" in ledger:
        osc = ledger.get("order_send_count")
        if type(osc) is not int or osc != 0:
            raise FleetGuardError(
                "ORDER_SEND_COUNT_TAMPER",
                f"Ledger payload order_send_count must be strictly 0, got {osc!r}.",
            )
    if "holdout_rows_analysed" in ledger:
        hra = ledger.get("holdout_rows_analysed")
        if type(hra) is not int or hra != 0:
            raise FleetGuardError(
                "HOLDOUT_SEAL_BREACH",
                f"Ledger payload holdout_rows_analysed must be strictly 0, got {hra!r}.",
            )

    raw_accounts = ledger.get("accounts")
    if not isinstance(raw_accounts, Sequence) or isinstance(raw_accounts, (str, bytes)):
        errors.append("LEDGER_INVALID_ACCOUNTS_LIST")
        accounts = []
    else:
        accounts = []
        for idx, item in enumerate(raw_accounts):
            if isinstance(item, (FleetAccount, Mapping)):
                accounts.append(_account_to_record(item))
            else:
                errors.append(f"LEDGER_INVALID_ACCOUNT_ENTRY_{idx}")

    raw_transitions = ledger.get("transitions", [])
    if not isinstance(raw_transitions, Sequence) or isinstance(raw_transitions, (str, bytes)):
        errors.append("LEDGER_INVALID_TRANSITIONS_LIST")
        transitions = []
    else:
        transitions = []
        for idx, item in enumerate(raw_transitions):
            if isinstance(item, (TransitionEvent, Mapping)):
                transitions.append(_transition_to_record(item))
            else:
                errors.append(f"LEDGER_INVALID_TRANSITION_ENTRY_{idx}")

    raw_policy = ledger.get("fleet_policy")
    if isinstance(raw_policy, FleetPolicy):
        policy = raw_policy.to_dict(usd_vnd_rate=25_765.94)
    elif isinstance(raw_policy, Mapping):
        policy = dict(raw_policy)
    elif raw_policy is None:
        policy = {}
    else:
        errors.append("LEDGER_INVALID_FLEET_POLICY")
        policy = {}

    meta = {
        "ledger_id": str(ledger.get("ledger_id") or ""),
        "ops6_eval_receipt": ledger.get("ops6_eval_receipt") or ledger.get("ops6_forensic_review_receipt"),
        "ops6_postmortems": ledger.get("ops6_postmortems"),
        "active_signals": ledger.get("active_signals"),
    }
    return accounts, transitions, policy, meta, errors


# ---------------------------------------------------------------------------
# OPS-6 Receipt & Postmortem Validators (Used by E1 & E3)
# ---------------------------------------------------------------------------
def _validate_ops6_eval_receipt(
    receipt: Mapping[str, Any] | None,
    *,
    latest_fail_dt: datetime,
    now_dt: datetime,
) -> tuple[bool, list[str]]:
    if receipt is None:
        return False, ["E1_OPS6_FORENSIC_RECEIPT_REQUIRED"]
    if not isinstance(receipt, Mapping):
        return False, ["E1_OPS6_RECEIPT_MALFORMED"]

    issues: list[str] = []
    receipt_id = str(receipt.get("receipt_id") or "").strip()
    signed_by = str(receipt.get("signed_by") or "").strip()
    signed_dt = _parse_utc_datetime(receipt.get("signed_utc"))
    sha = receipt.get("report_sha256") or receipt.get("receipt_sha256")
    approved = _parse_strict_bool(receipt.get("approved_to_resume"))

    if not receipt_id:
        issues.append("E1_OPS6_RECEIPT_ID_MISSING")
    if not signed_by:
        issues.append("E1_OPS6_RECEIPT_UNSIGNED")
    if signed_dt is None:
        issues.append("E1_OPS6_RECEIPT_INVALID_TIMESTAMP")
    else:
        if signed_dt < latest_fail_dt:
            issues.append("E1_OPS6_RECEIPT_STALE_PRE_FAILURE")
        if signed_dt > now_dt:
            issues.append("E1_OPS6_RECEIPT_FUTURE_TIMESTAMP")
    if not _is_valid_sha256_hex(sha):
        issues.append("E1_OPS6_RECEIPT_SHA256_INVALID")
    if approved is not True:
        issues.append("E1_OPS6_RECEIPT_NOT_APPROVED")

    if "root_cause_class" in receipt and receipt.get("root_cause_class") is not None:
        rc = str(receipt.get("root_cause_class")).strip().upper()
        if rc not in VALID_OPS6_BREACH_CLASSES:
            issues.append("E1_OPS6_RECEIPT_INVALID_CLASSIFICATION")
        elif rc == "BOT_BUG":
            fix_ok = _parse_strict_bool(receipt.get("fix_verified"))
            if fix_ok is not True:
                issues.append("E1_OPS6_BOT_BUG_FIX_UNVERIFIED")

    return len(issues) == 0, issues


def _validate_ops6_breach_postmortem(
    pm: Mapping[str, Any] | None,
    *,
    account_id: str,
    breach_dt: datetime | None,
    now_dt: datetime,
) -> tuple[bool, list[str]]:
    if pm is None or not isinstance(pm, Mapping):
        return False, ["E3_OPS6_POSTMORTEM_MISSING"]

    issues: list[str] = []
    pm_acct = str(pm.get("account_id") or "").strip()
    if pm_acct != account_id:
        issues.append("E3_OPS6_POSTMORTEM_ACCOUNT_MISMATCH")

    raw_cls = pm.get("classification") if "classification" in pm else pm.get("root_cause_class")
    norm_cls = str(raw_cls or "").strip().upper() if isinstance(raw_cls, str) else ""
    if norm_cls not in VALID_OPS6_BREACH_CLASSES:
        issues.append("E3_OPS6_POSTMORTEM_INVALID_CLASSIFICATION")

    signed_by = str(pm.get("signed_by") or "").strip()
    if not signed_by:
        issues.append("E3_OPS6_POSTMORTEM_UNSIGNED")

    if "signed" in pm:
        s_flag = _parse_strict_bool(pm.get("signed"))
        if s_flag is not True:
            issues.append("E3_OPS6_POSTMORTEM_SIGNED_FLAG_NOT_TRUE")

    signed_dt = _parse_utc_datetime(pm.get("signed_utc"))
    if signed_dt is None:
        issues.append("E3_OPS6_POSTMORTEM_INVALID_TIMESTAMP")
    else:
        if breach_dt is not None and signed_dt < breach_dt:
            issues.append("E3_OPS6_POSTMORTEM_STALE_PRE_BREACH")
        if signed_dt > now_dt:
            issues.append("E3_OPS6_POSTMORTEM_FUTURE_TIMESTAMP")

    sha = pm.get("report_sha256") or pm.get("postmortem_sha256")
    if not _is_valid_sha256_hex(sha):
        issues.append("E3_OPS6_POSTMORTEM_SHA256_INVALID")

    if norm_cls == "BOT_BUG":
        fix_ok = _parse_strict_bool(pm.get("fix_verified"))
        if fix_ok is not True:
            issues.append("E3_OPS6_BOT_BUG_FIX_UNVERIFIED")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# E1: Eval Fail Cooldown (Trailing 30d >= 2 fails -> Block + OPS-6 Receipt)
# ---------------------------------------------------------------------------
def evaluate_e1_eval_fail_cooldown(
    accounts: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]],
    *,
    now_dt: datetime,
    ops6_eval_receipt: Mapping[str, Any] | None = None,
    window_days: int = E1_TRAILING_WINDOW_DAYS,
    fail_threshold: int = E1_MAX_FAILED_EVALS_BEFORE_BLOCK,
) -> GuardResult:
    """E1: Count failed evals in trailing 30 days (`>= 2` blocks admission unless cleared by OPS-6 receipt)."""
    win_d = _parse_strict_int(window_days, min_value=1)
    thr = _parse_strict_int(fail_threshold, min_value=1)
    if win_d is None or thr is None:
        return GuardResult(
            guard_id=GUARD_E1,
            passed=False,
            blocking=True,
            status="BLOCK",
            blocking_reasons=("E1_INVALID_CONFIG_THRESHOLDS",),
            details={"window_days": window_days, "fail_threshold": fail_threshold},
        )

    window_sec = float(win_d) * 86400.0
    blocking_reasons: list[str] = []
    warnings: list[str] = []
    seen_fail_keys: set[tuple[str, str]] = set()
    recent_fails: list[dict[str, Any]] = []
    latest_fail_dt: datetime | None = None

    for idx, ev in enumerate(transitions):
        if str(ev.get("to_state") or "") != FleetState.E1_EVAL_FAIL_COOLDOWN.value:
            continue
        acct_id = str(ev.get("account_id") or f"unknown_{idx}")
        ev_dt = _parse_utc_datetime(ev.get("utc_ts"))
        if ev_dt is None:
            blocking_reasons.append("E1_POISONED_FAIL_EVENT_TIMESTAMP")
            continue
        age_sec = (now_dt - ev_dt).total_seconds()
        if age_sec < -DEFAULT_MAX_FUTURE_HEARTBEAT_SKEW_SEC:
            blocking_reasons.append("E1_FUTURE_FAIL_EVENT_TIMESTAMP")
            continue
        if age_sec <= window_sec:
            ts_iso = _format_utc_iso(ev_dt)
            key = (acct_id, ts_iso)
            if key not in seen_fail_keys:
                seen_fail_keys.add(key)
                recent_fails.append(
                    {
                        "account_id": acct_id,
                        "utc_ts": ts_iso,
                        "age_days": round(max(0.0, age_sec) / 86400.0, 3),
                        "source": "transition",
                    }
                )
                if latest_fail_dt is None or ev_dt > latest_fail_dt:
                    latest_fail_dt = ev_dt

    # Also capture accounts currently sitting in E1 without an explicit transition log entry
    accounts_seen_in_transitions = {f["account_id"] for f in recent_fails}
    for acct in accounts:
        if str(acct.get("state") or "") != FleetState.E1_EVAL_FAIL_COOLDOWN.value:
            continue
        acct_id = str(acct.get("account_id") or "")
        if acct_id in accounts_seen_in_transitions:
            continue
        ev_dt = _parse_utc_datetime(acct.get("last_transition_utc"))
        if ev_dt is None:
            blocking_reasons.append("E1_POISONED_ACCOUNT_FAIL_TIMESTAMP")
            continue
        age_sec = (now_dt - ev_dt).total_seconds()
        if age_sec < -DEFAULT_MAX_FUTURE_HEARTBEAT_SKEW_SEC:
            blocking_reasons.append("E1_FUTURE_FAIL_EVENT_TIMESTAMP")
            continue
        if age_sec <= window_sec:
            ts_iso = _format_utc_iso(ev_dt)
            key = (acct_id, ts_iso)
            if key not in seen_fail_keys:
                seen_fail_keys.add(key)
                recent_fails.append(
                    {
                        "account_id": acct_id,
                        "utc_ts": ts_iso,
                        "age_days": round(max(0.0, age_sec) / 86400.0, 3),
                        "source": "account_state",
                    }
                )
                if latest_fail_dt is None or ev_dt > latest_fail_dt:
                    latest_fail_dt = ev_dt

    fail_count = len(recent_fails)
    cleared_by_receipt = False

    if fail_count >= thr:
        eff_latest = latest_fail_dt or now_dt
        receipt_ok, receipt_issues = _validate_ops6_eval_receipt(
            ops6_eval_receipt,
            latest_fail_dt=eff_latest,
            now_dt=now_dt,
        )
        if receipt_ok:
            cleared_by_receipt = True
            warnings.append("E1_COOLDOWN_CLEARED_BY_OPS6_RECEIPT")
        else:
            blocking_reasons.append("E1_EVAL_FAIL_COOLDOWN_BLOCKED")
            blocking_reasons.extend(receipt_issues)
    elif fail_count == 1:
        warnings.append("E1_SINGLE_EVAL_FAIL_IN_30D_WATCH")

    blocking = len(blocking_reasons) > 0
    status = "BLOCK" if blocking else ("WARNING" if warnings else "PASS")
    return GuardResult(
        guard_id=GUARD_E1,
        passed=not blocking,
        blocking=blocking,
        status=status,
        blocking_reasons=_dedupe_codes(blocking_reasons),
        warnings=_dedupe_codes(warnings),
        details={
            "window_days": win_d,
            "fail_threshold": thr,
            "failed_evals_in_window": fail_count,
            "cleared_by_ops6_receipt": cleared_by_receipt,
            "recent_failures": recent_fails,
        },
    )


# ---------------------------------------------------------------------------
# E2: Funded DD Freeze (Amber >= 3.5% -> 0.5x | Red >= 6.0% -> 0.0x)
# ---------------------------------------------------------------------------
def evaluate_e2_funded_dd_freeze(
    accounts: Sequence[Mapping[str, Any]],
    *,
    amber_dd_pct: float = E2_AMBER_DD_PCT,
    red_dd_pct: float = E2_RED_DD_PCT,
) -> GuardResult:
    """E2: Freeze opening ANY new Challenge if ANY active Funded account is Amber (`>=3.5%`) or Red (`>=6.0%`)."""
    amber_thr = _parse_finite_float(amber_dd_pct, strictly_positive=True, max_value=100.0)
    red_thr = _parse_finite_float(red_dd_pct, strictly_positive=True, max_value=100.0)
    if amber_thr is None or red_thr is None or red_thr <= amber_thr:
        return GuardResult(
            guard_id=GUARD_E2,
            passed=False,
            blocking=True,
            status="BLOCK",
            blocking_reasons=("E2_INVALID_DD_THRESHOLDS",),
            details={"scale_factor": E2_SCALE_RED, "dd_regime": "RED"},
        )

    blocking_reasons: list[str] = []
    affected_accounts: list[dict[str, Any]] = []
    max_observed_dd = 0.0
    scale_factor = E2_SCALE_GREEN
    regime = "GREEN"
    funded_checked = 0

    for acct in accounts:
        state = str(acct.get("state") or "")
        if state not in (
            FleetState.S5_FUNDED_ACTIVE.value,
            FleetState.S6_PAYOUT_AUDIT_AND_HARVEST.value,
            FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value,
            FleetState.E2_FUNDED_DD_FREEZE.value,
        ):
            continue
        funded_checked += 1
        acct_id = str(acct.get("account_id") or "UNKNOWN")

        if state == FleetState.E2_FUNDED_DD_FREEZE.value:
            scale_factor = min(scale_factor, E2_SCALE_RED)
            regime = "RED"
            blocking_reasons.append("E2_FUNDED_ACCOUNT_FROZEN_IN_E2")
            affected_accounts.append(
                {
                    "account_id": acct_id,
                    "state": state,
                    "regime": "RED",
                    "scale_factor": E2_SCALE_RED,
                    "reason": "STATE_E2_FUNDED_DD_FREEZE",
                }
            )

        static_dd = _parse_finite_float(acct.get("static_dd_pct"), min_value=0.0, max_value=100.0)
        daily_dd = _parse_finite_float(acct.get("daily_dd_pct"), min_value=0.0, max_value=100.0)
        traffic = acct.get("ops4_traffic_light", "GREEN")

        if static_dd is None or daily_dd is None:
            scale_factor = E2_SCALE_RED
            regime = "RED"
            blocking_reasons.append("E2_POISONED_FUNDED_DD_INPUT")
            affected_accounts.append(
                {
                    "account_id": acct_id,
                    "state": state,
                    "regime": "RED",
                    "scale_factor": E2_SCALE_RED,
                    "reason": "POISONED_DD_VALUE",
                }
            )
            continue

        if not isinstance(traffic, str) or traffic not in _VALID_TRAFFIC_LIGHTS:
            scale_factor = E2_SCALE_RED
            regime = "RED"
            blocking_reasons.append("E2_POISONED_OPS4_TRAFFIC_LIGHT")
            affected_accounts.append(
                {
                    "account_id": acct_id,
                    "state": state,
                    "regime": "RED",
                    "scale_factor": E2_SCALE_RED,
                    "reason": f"INVALID_TRAFFIC_LIGHT:{traffic!r}",
                }
            )
            continue

        eff_dd = max(static_dd, daily_dd)
        if eff_dd > max_observed_dd:
            max_observed_dd = eff_dd

        if eff_dd >= red_thr or traffic == "RED":
            scale_factor = min(scale_factor, E2_SCALE_RED)
            regime = "RED"
            blocking_reasons.append("E2_FUNDED_DD_RED_FREEZE")
            affected_accounts.append(
                {
                    "account_id": acct_id,
                    "state": state,
                    "static_dd_pct": round(static_dd, 4),
                    "daily_dd_pct": round(daily_dd, 4),
                    "effective_dd_pct": round(eff_dd, 4),
                    "ops4_traffic_light": traffic,
                    "regime": "RED",
                    "scale_factor": E2_SCALE_RED,
                }
            )
        elif eff_dd >= amber_thr or traffic == "AMBER":
            scale_factor = min(scale_factor, E2_SCALE_AMBER)
            if regime != "RED":
                regime = "AMBER"
            blocking_reasons.append("E2_FUNDED_DD_AMBER_FREEZE")
            affected_accounts.append(
                {
                    "account_id": acct_id,
                    "state": state,
                    "static_dd_pct": round(static_dd, 4),
                    "daily_dd_pct": round(daily_dd, 4),
                    "effective_dd_pct": round(eff_dd, 4),
                    "ops4_traffic_light": traffic,
                    "regime": "AMBER",
                    "scale_factor": E2_SCALE_AMBER,
                }
            )

    blocking = len(blocking_reasons) > 0
    return GuardResult(
        guard_id=GUARD_E2,
        passed=not blocking,
        blocking=blocking,
        status="BLOCK" if blocking else "PASS",
        blocking_reasons=_dedupe_codes(blocking_reasons),
        details={
            "funded_accounts_checked": funded_checked,
            "amber_dd_threshold_pct": amber_thr,
            "red_dd_threshold_pct": red_thr,
            "max_funded_dd_pct": round(max_observed_dd, 4),
            "dd_regime": regime,
            "scale_factor": scale_factor,
            "affected_accounts": affected_accounts,
        },
    )


# ---------------------------------------------------------------------------
# E3: Funded Breach Postmortem (OPS-6 Signed BOT_BUG | SLIPPAGE | VARIANCE)
# ---------------------------------------------------------------------------
def evaluate_e3_funded_breach_postmortem(
    accounts: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]],
    *,
    now_dt: datetime,
    ops6_postmortems: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
) -> GuardResult:
    """E3: Lock entire fleet admission if ANY Funded breach lacks a signed OPS-6 postmortem."""
    # Map latest breach timestamp per breached account from both transition history and current state
    breaches: dict[str, datetime | None] = {}
    blocking_reasons: list[str] = []

    for idx, ev in enumerate(transitions):
        if str(ev.get("to_state") or "") != FleetState.E3_FUNDED_BREACH_POSTMORTEM.value:
            continue
        acct_id = str(ev.get("account_id") or f"unknown_{idx}")
        ev_dt = _parse_utc_datetime(ev.get("utc_ts"))
        if ev_dt is None:
            blocking_reasons.append("E3_POISONED_BREACH_TIMESTAMP")
            breaches.setdefault(acct_id, None)
            continue
        prev_dt = breaches.get(acct_id)
        if prev_dt is None or ev_dt > prev_dt:
            breaches[acct_id] = ev_dt

    for acct in accounts:
        if str(acct.get("state") or "") != FleetState.E3_FUNDED_BREACH_POSTMORTEM.value:
            continue
        acct_id = str(acct.get("account_id") or "UNKNOWN")
        ev_dt = _parse_utc_datetime(acct.get("last_transition_utc"))
        if acct_id not in breaches:
            breaches[acct_id] = ev_dt
        elif ev_dt is not None and (breaches[acct_id] is None or ev_dt > breaches[acct_id]):
            breaches[acct_id] = ev_dt

    # Index supplied OPS-6 postmortems (plus any inline account-level `ops6_postmortem` field)
    pm_by_account: dict[str, list[Mapping[str, Any]]] = {}
    if isinstance(ops6_postmortems, Mapping):
        for k, v in ops6_postmortems.items():
            if isinstance(v, Mapping):
                rec = dict(v)
                rec.setdefault("account_id", str(k))
                pm_by_account.setdefault(str(rec["account_id"]), []).append(rec)
    elif isinstance(ops6_postmortems, Sequence) and not isinstance(ops6_postmortems, (str, bytes)):
        for item in ops6_postmortems:
            if isinstance(item, Mapping):
                aid = str(item.get("account_id") or "")
                pm_by_account.setdefault(aid, []).append(item)
    elif ops6_postmortems is not None:
        blocking_reasons.append("E3_INVALID_POSTMORTEMS_CONTAINER")

    for acct in accounts:
        inline_pm = acct.get("ops6_postmortem")
        if isinstance(inline_pm, Mapping):
            aid = str(acct.get("account_id") or "")
            rec = dict(inline_pm)
            rec.setdefault("account_id", aid)
            pm_by_account.setdefault(aid, []).append(rec)

    unresolved_breaches: list[dict[str, Any]] = []
    resolved_breaches: list[dict[str, Any]] = []

    for acct_id in sorted(breaches.keys()):
        breach_dt = breaches[acct_id]
        candidates = pm_by_account.get(acct_id, [])
        best_ok = False
        best_cls = ""
        last_issues: list[str] = ["E3_OPS6_POSTMORTEM_MISSING"]
        for cand in candidates:
            ok, issues = _validate_ops6_breach_postmortem(
                cand,
                account_id=acct_id,
                breach_dt=breach_dt,
                now_dt=now_dt,
            )
            if ok:
                best_ok = True
                raw_c = cand.get("classification") if "classification" in cand else cand.get("root_cause_class")
                best_cls = str(raw_c or "").strip().upper()
                break
            last_issues = issues

        if best_ok:
            resolved_breaches.append(
                {
                    "account_id": acct_id,
                    "breach_utc": _format_utc_iso(breach_dt) if breach_dt else None,
                    "classification": best_cls,
                    "status": "SIGNED_OPS6_VERIFIED",
                }
            )
        else:
            blocking_reasons.append("E3_FUNDED_BREACH_UNRESOLVED_POSTMORTEM")
            blocking_reasons.extend(last_issues)
            unresolved_breaches.append(
                {
                    "account_id": acct_id,
                    "breach_utc": _format_utc_iso(breach_dt) if breach_dt else None,
                    "issues": list(_dedupe_codes(last_issues)),
                }
            )

    blocking = len(blocking_reasons) > 0
    return GuardResult(
        guard_id=GUARD_E3,
        passed=not blocking,
        blocking=blocking,
        status="BLOCK" if blocking else "PASS",
        blocking_reasons=_dedupe_codes(blocking_reasons),
        details={
            "total_funded_breaches": len(breaches),
            "resolved_breaches": resolved_breaches,
            "unresolved_breaches": unresolved_breaches,
            "allowed_classifications": sorted(VALID_OPS6_BREACH_CLASSES),
        },
    )


# ---------------------------------------------------------------------------
# E4: Capital Cap (FTMO 400K / 200K), Firm Slots & naqex-node1 VPS Capacity
# ---------------------------------------------------------------------------
def evaluate_e4_cap_or_vps_overflow(
    accounts: Sequence[Mapping[str, Any]],
    proposed_account: Mapping[str, Any] | FleetAccount | None,
    vps_telemetry: Mapping[str, Any] | None,
    *,
    fleet_policy: Mapping[str, Any] | FleetPolicy | None = None,
    contracts: Mapping[str, Mapping[str, Any]] | None = None,
    catalog_path: Path | str | None = None,
    vps_budget: VpsCapacityBudget | None = None,
) -> GuardResult:
    """E4: Enforce FTMO 400K Funded / 200K Challenge cap, catalog/firm slots, and VPS CPU/RAM/MT5 limits."""
    blocking_reasons: list[str] = []
    warnings: list[str] = []
    budget = vps_budget or VpsCapacityBudget()

    try:
        catalog = contracts if contracts is not None else load_firms_catalog(catalog_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return GuardResult(
            guard_id=GUARD_E4,
            passed=False,
            blocking=True,
            status="BLOCK",
            blocking_reasons=("E4_FIRMS_CATALOG_UNAVAILABLE",),
        )

    if proposed_account is None:
        return GuardResult(
            guard_id=GUARD_E4,
            passed=False,
            blocking=True,
            status="BLOCK",
            blocking_reasons=("E4_PROPOSED_ACCOUNT_MISSING",),
        )

    prop = _account_to_record(proposed_account)
    if not prop:
        return GuardResult(
            guard_id=GUARD_E4,
            passed=False,
            blocking=True,
            status="BLOCK",
            blocking_reasons=("E4_PROPOSED_ACCOUNT_INVALID",),
        )

    prop_id = str(prop.get("account_id") or "").strip()
    contract_id = str(prop.get("contract_id") or "").strip()
    contract = catalog.get(contract_id) if contract_id else None

    if contract is None:
        blocking_reasons.append("E4_UNKNOWN_CATALOG_CONTRACT")
        firm_id = _normalize_firm_key(prop.get("firm_id") or prop.get("firm_profile"))
        contract_cap_usd = None
    else:
        firm_id = _normalize_firm_key(contract.get("firm_id") or prop.get("firm_id"))
        avail_vn = _parse_strict_bool(contract.get("available_vn"))
        if avail_vn is not True:
            blocking_reasons.append("E4_CONTRACT_UNAVAILABLE_VN")
        if str(contract.get("execution_status") or "") == "TERMS_VERIFIED_EXECUTION_UNMEASURED":
            warnings.append("E4_TERMS_VERIFIED_EXECUTION_UNMEASURED")
        contract_cap_usd = _parse_finite_float(contract.get("capital_usd"), strictly_positive=True)

    raw_prop_cap = prop.get("capital_usd", contract_cap_usd)
    prop_capital_usd = _parse_finite_float(raw_prop_cap, strictly_positive=True)
    if prop_capital_usd is None:
        blocking_reasons.append("E4_POISONED_PROPOSED_CAPITAL_USD")

    if not firm_id:
        blocking_reasons.append("E4_MISSING_FIRM_ID")

    # Normalize fleet_policy limits
    if isinstance(fleet_policy, FleetPolicy):
        pol_dict = fleet_policy.to_dict(usd_vnd_rate=25_765.94)
    elif isinstance(fleet_policy, Mapping):
        pol_dict = dict(fleet_policy)
    else:
        pol_dict = {}

    concurrency_mode = str(pol_dict.get("concurrency_mode") or "GATED_STAGGER")
    max_evals = _parse_strict_int(pol_dict.get("max_concurrent_evals", 2), min_value=0)
    max_funded = _parse_strict_int(pol_dict.get("max_concurrent_funded", 4), min_value=0)
    max_per_firm = _parse_strict_int(pol_dict.get("max_accounts_per_firm", 3), min_value=1)
    if max_evals is None or max_funded is None or max_per_firm is None:
        blocking_reasons.append("E4_POISONED_FLEET_POLICY")
        max_evals = 0 if max_evals is None else max_evals
        max_funded = 0 if max_funded is None else max_funded
        max_per_firm = 1 if max_per_firm is None else max_per_firm

    # Optional per-contract catalog override for firm slot limit
    if contract is not None and contract.get("max_active_accounts") is not None:
        cat_slots = _parse_strict_int(contract.get("max_active_accounts"), min_value=1)
        if cat_slots is None:
            blocking_reasons.append("E4_POISONED_CATALOG_SLOT_LIMIT")
        else:
            max_per_firm = min(max_per_firm, cat_slots)

    # Aggregate existing fleet capital & active counts (deduplicating proposed_account if already registered at S0)
    existing_firm_funded_usd = 0.0
    existing_firm_eval_usd = 0.0
    existing_firm_active_count = 0
    existing_active_evals = 0
    existing_active_funded = 0
    any_passed_p1_or_beyond = False

    for acct in accounts:
        aid = str(acct.get("account_id") or "")
        st = str(acct.get("state") or "")
        if aid == prop_id and st == FleetState.S0_PRE_CHALLENGE.value:
            continue
        afirm = _normalize_firm_key(acct.get("firm_id") or acct.get("firm_profile"))
        # Use base_capital_usd (excluding organic Scaling Plan growth) when evaluating FTMO 400K base cap
        raw_base_cap = acct.get("base_capital_usd", acct.get("capital_usd"))
        base_cap = _parse_finite_float(raw_base_cap, strictly_positive=True)
        if base_cap is None and st in _OCCUPYING_FIRM_SLOT_STATES:
            blocking_reasons.append("E4_POISONED_EXISTING_ACCOUNT_CAPITAL")
            base_cap = 0.0

        if st in _ACTIVE_EVAL_STATES:
            existing_active_evals += 1
        if st in _ACTIVE_FUNDED_STATES:
            existing_active_funded += 1
        if st in _PASSED_P1_OR_BEYOND_STATES:
            any_passed_p1_or_beyond = True

        if afirm == firm_id:
            if st in _OCCUPYING_FIRM_SLOT_STATES:
                existing_firm_active_count += 1
            if st in _COMMITTED_FUNDED_CAP_STATES and base_cap is not None:
                existing_firm_funded_usd += base_cap
            elif st in _ALL_EVAL_PIPELINE_STATES and base_cap is not None:
                existing_firm_eval_usd += base_cap

    # Capital cap checks
    firm_caps = dict(DEFAULT_FIRM_CAP_LIMITS.get(firm_id, {}))
    if contract is not None:
        if contract.get("max_active_funded_usd") is not None:
            ov = _parse_finite_float(contract.get("max_active_funded_usd"), strictly_positive=True)
            if ov is None:
                blocking_reasons.append("E4_POISONED_CATALOG_CAP")
            else:
                firm_caps["max_active_funded_usd"] = ov
        if contract.get("max_single_challenge_usd") is not None:
            ov = _parse_finite_float(contract.get("max_single_challenge_usd"), strictly_positive=True)
            if ov is None:
                blocking_reasons.append("E4_POISONED_CATALOG_CAP")
            else:
                firm_caps["max_single_challenge_usd"] = ov

    target_phase = str(prop.get("target_phase") or prop.get("account_phase") or "EVAL").strip().upper()
    is_funded_admission = target_phase == "FUNDED" or str(prop.get("state") or "") == FleetState.S5_FUNDED_ACTIVE.value

    max_single_challenge = firm_caps.get("max_single_challenge_usd")
    max_active_funded = firm_caps.get("max_active_funded_usd")
    projected_firm_funded_usd = existing_firm_funded_usd + (prop_capital_usd or 0.0)
    projected_firm_total_usd = existing_firm_funded_usd + existing_firm_eval_usd + (prop_capital_usd or 0.0)

    if prop_capital_usd is not None:
        if (
            not is_funded_admission
            and max_single_challenge is not None
            and prop_capital_usd > max_single_challenge + 1e-9
        ):
            code = (
                "E4_FTMO_SINGLE_CHALLENGE_200K_CAP_EXCEEDED"
                if firm_id == "ftmo"
                else "E4_SINGLE_CHALLENGE_CAP_EXCEEDED"
            )
            blocking_reasons.append(code)
        if max_active_funded is not None:
            if projected_firm_funded_usd > max_active_funded + 1e-9:
                code = (
                    "E4_FTMO_400K_FUNDED_CAP_EXCEEDED"
                    if firm_id == "ftmo"
                    else "E4_FIRM_FUNDED_CAP_EXCEEDED"
                )
                blocking_reasons.append(code)
            elif projected_firm_total_usd > max_active_funded + 1e-9:
                code = (
                    "E4_FTMO_400K_PROJECTED_ALLOCATION_EXCEEDED"
                    if firm_id == "ftmo"
                    else "E4_FIRM_PROJECTED_ALLOCATION_EXCEEDED"
                )
                blocking_reasons.append(code)

    # Firm slot & concurrency limits
    if existing_firm_active_count + 1 > max_per_firm:
        blocking_reasons.append("E4_FIRM_SLOT_LIMIT_EXCEEDED")

    if is_funded_admission:
        if existing_active_funded + 1 > max_funded:
            blocking_reasons.append("E4_MAX_CONCURRENT_FUNDED_EXCEEDED")
    else:
        if existing_active_evals + 1 > max_evals:
            blocking_reasons.append("E4_MAX_CONCURRENT_EVALS_EXCEEDED")
        if concurrency_mode in ("SINGLE_TICKET", "CONSERVATIVE_1_TICKET") and existing_active_evals >= 1:
            blocking_reasons.append("E4_SINGLE_TICKET_CONCURRENCY_LOCK")
        elif concurrency_mode == "GATED_STAGGER" and existing_active_evals >= 1 and not any_passed_p1_or_beyond:
            blocking_reasons.append("E4_GATED_STAGGER_PRECONDITION_UNMET")

    # VPS capacity budget check (`naqex-node1`)
    vps_details: dict[str, Any] = {"node_name": budget.node_name}
    if vps_telemetry is None or not isinstance(vps_telemetry, Mapping):
        blocking_reasons.append("E4_VPS_TELEMETRY_MISSING")
    else:
        cpu_pct = _parse_finite_float(vps_telemetry.get("cpu_util_pct"), min_value=0.0, max_value=100.0)
        free_ram = _parse_finite_float(vps_telemetry.get("free_ram_gb"), min_value=0.0)
        active_terms = _parse_strict_int(vps_telemetry.get("active_mt5_terminals"), min_value=0)
        max_terms_override = vps_telemetry.get("max_mt5_terminals")
        if max_terms_override is not None:
            eff_max_terms = _parse_strict_int(max_terms_override, min_value=1)
            if eff_max_terms is None:
                blocking_reasons.append("E4_POISONED_VPS_MAX_TERMINALS")
                eff_max_terms = budget.max_mt5_terminals
        else:
            eff_max_terms = budget.max_mt5_terminals

        requires_new_term_raw = prop.get("requires_new_terminal", True)
        requires_new_term = _parse_strict_bool(requires_new_term_raw)
        if requires_new_term is None:
            blocking_reasons.append("E4_POISONED_REQUIRES_NEW_TERMINAL_FLAG")
            requires_new_term = True

        if cpu_pct is None:
            blocking_reasons.append("E4_POISONED_OR_MISSING_VPS_CPU")
        elif cpu_pct > budget.max_cpu_util_pct + 1e-9:
            blocking_reasons.append("E4_VPS_CPU_OVERFLOW")

        if free_ram is None:
            blocking_reasons.append("E4_POISONED_OR_MISSING_VPS_RAM")
        else:
            post_add_ram = free_ram - (budget.ram_per_terminal_gb if requires_new_term else 0.0)
            if free_ram + 1e-9 < budget.min_free_ram_gb or post_add_ram + 1e-9 < budget.min_post_add_ram_gb:
                blocking_reasons.append("E4_VPS_RAM_OVERFLOW")

        if "ram_util_pct" in vps_telemetry and vps_telemetry.get("ram_util_pct") is not None:
            ram_util = _parse_finite_float(vps_telemetry.get("ram_util_pct"), min_value=0.0, max_value=100.0)
            if ram_util is None:
                blocking_reasons.append("E4_POISONED_VPS_RAM_UTIL_PCT")
            elif ram_util > budget.max_ram_util_pct + 1e-9:
                blocking_reasons.append("E4_VPS_RAM_UTIL_OVERFLOW")

        if "disk_c_free_gb" in vps_telemetry and vps_telemetry.get("disk_c_free_gb") is not None:
            disk_c = _parse_finite_float(vps_telemetry.get("disk_c_free_gb"), min_value=0.0)
            if disk_c is None:
                blocking_reasons.append("E4_POISONED_VPS_DISK_C")
            elif disk_c + 1e-9 < budget.min_disk_c_free_gb:
                blocking_reasons.append("E4_VPS_DISK_C_LOW")

        if active_terms is None:
            blocking_reasons.append("E4_POISONED_OR_MISSING_VPS_MT5_TERMINALS")
        else:
            projected_terms = active_terms + (1 if requires_new_term else 0)
            if projected_terms > eff_max_terms:
                blocking_reasons.append("E4_VPS_MAX_MT5_TERMINALS_EXCEEDED")
            vps_details["projected_mt5_terminals"] = projected_terms

        vps_details.update(
            {
                "node_name": str(vps_telemetry.get("node_name") or budget.node_name),
                "cpu_util_pct": cpu_pct,
                "max_cpu_util_pct": budget.max_cpu_util_pct,
                "free_ram_gb": free_ram,
                "min_free_ram_gb": budget.min_free_ram_gb,
                "active_mt5_terminals": active_terms,
                "max_mt5_terminals": eff_max_terms,
            }
        )

    blocking = len(blocking_reasons) > 0
    status = "BLOCK" if blocking else ("WARNING" if warnings else "PASS")
    return GuardResult(
        guard_id=GUARD_E4,
        passed=not blocking,
        blocking=blocking,
        status=status,
        blocking_reasons=_dedupe_codes(blocking_reasons),
        warnings=_dedupe_codes(warnings),
        details={
            "firm_id": firm_id,
            "contract_id": contract_id,
            "proposed_capital_usd": prop_capital_usd,
            "existing_firm_funded_usd": round(existing_firm_funded_usd, 2),
            "existing_firm_eval_usd": round(existing_firm_eval_usd, 2),
            "projected_firm_funded_usd": round(projected_firm_funded_usd, 2),
            "projected_firm_total_usd": round(projected_firm_total_usd, 2),
            "firm_max_active_funded_usd": max_active_funded,
            "firm_max_single_challenge_usd": max_single_challenge,
            "existing_firm_active_count": existing_firm_active_count,
            "max_accounts_per_firm": max_per_firm,
            "existing_active_evals": existing_active_evals,
            "max_concurrent_evals": max_evals,
            "existing_active_funded": existing_active_funded,
            "max_concurrent_funded": max_funded,
            "vps": vps_details,
        },
    )


# ---------------------------------------------------------------------------
# E5: Cross-Account Opposite Hedge, Duplicate Magic Ranges & Portable Dirs
# ---------------------------------------------------------------------------
def evaluate_e5_cross_account_opposite_hedge(
    accounts: Sequence[Mapping[str, Any]],
    proposed_account: Mapping[str, Any] | FleetAccount | None,
    *,
    active_signals: Sequence[Mapping[str, Any]] | None = None,
    hedging_window_sec: int = 3600,
) -> GuardResult:
    """E5: Reject same-firm opposite directional exposure, duplicate MagicNumber ranges, or duplicate Portable dirs."""
    blocking_reasons: list[str] = []
    hedge_conflicts: list[dict[str, Any]] = []
    magic_collisions: list[dict[str, Any]] = []
    portable_collisions: list[dict[str, Any]] = []

    prop = _account_to_record(proposed_account) if proposed_account is not None else {}
    prop_id = str(prop.get("account_id") or "PROPOSED_ACCOUNT").strip() or "PROPOSED_ACCOUNT"

    # Build combined active fleet roster (existing active/locked accounts + proposed account)
    roster: list[dict[str, Any]] = []
    for acct in accounts:
        aid = str(acct.get("account_id") or "")
        st = str(acct.get("state") or "")
        if aid == prop_id and st == FleetState.S0_PRE_CHALLENGE.value:
            continue
        if st in (FleetState.CLOSED_ARCHIVED.value, FleetState.E1_EVAL_FAIL_COOLDOWN.value):
            continue
        roster.append(dict(acct))
    if prop:
        roster.append(dict(prop))

    # 1. Cross-account same-firm opposite directional exposure (composes OPS-2 check_multi_account_compliance)
    combined_signals: list[dict[str, Any]] = []
    if active_signals is not None:
        if not isinstance(active_signals, Sequence) or isinstance(active_signals, (str, bytes)):
            blocking_reasons.append("E5_INVALID_ACTIVE_SIGNALS_CONTAINER")
        else:
            for item in active_signals:
                if isinstance(item, Mapping):
                    combined_signals.append(dict(item))
                else:
                    blocking_reasons.append("E5_INVALID_EXPOSURE_RECORD")

    for rec in roster:
        aid = str(rec.get("account_id") or "UNKNOWN")
        firm = _normalize_firm_key(rec.get("firm_id") or rec.get("firm_profile"))
        for key_name in ("active_positions", "active_signals", "open_exposures"):
            raw_sigs = rec.get(key_name)
            if raw_sigs is None:
                continue
            if not isinstance(raw_sigs, Sequence) or isinstance(raw_sigs, (str, bytes)):
                blocking_reasons.append("E5_INVALID_EXPOSURE_RECORD")
                continue
            for sig in raw_sigs:
                if not isinstance(sig, Mapping):
                    blocking_reasons.append("E5_INVALID_EXPOSURE_RECORD")
                    continue
                item = dict(sig)
                item.setdefault("account_login", aid)
                item.setdefault("account_id", aid)
                if not (item.get("firm") or item.get("firm_id") or item.get("firm_profile")):
                    item["firm"] = firm.upper()
                combined_signals.append(item)

    if combined_signals:
        # Normalize for OPS-2 compliance reuse
        ops2_signals: list[dict[str, Any]] = []
        for sig in combined_signals:
            firm_val = _normalize_firm_key(sig.get("firm") or sig.get("firm_id") or sig.get("firm_profile"))
            acct_key = sig.get("account_id") or sig.get("account_login")
            sym = str(sig.get("symbol") or "").strip()
            direction = _normalize_direction(sig.get("direction") or sig.get("side"))
            raw_ts = sig.get("timestamp_utc")
            ts_val: float | None = None
            if raw_ts is not None:
                parsed_dt = _parse_utc_datetime(raw_ts)
                if parsed_dt is None:
                    blocking_reasons.append("E5_INVALID_EXPOSURE_TIMESTAMP")
                    continue
                ts_val = parsed_dt.timestamp()
            if not firm_val or acct_key is None or not sym or direction is None:
                blocking_reasons.append("E5_INVALID_EXPOSURE_RECORD")
                continue
            ops2_signals.append(
                {
                    "firm": firm_val.upper(),
                    "account_login": str(acct_key),
                    "symbol": sym,
                    "direction": direction,
                    "timestamp_utc": ts_val,
                }
            )

        if ops2_signals:
            comp_findings, _, _ = check_multi_account_compliance(
                active_signals=ops2_signals,
                hedging_window_sec=hedging_window_sec,
            )
            for f in comp_findings:
                if f.code == "GROUP_HEDGING_CONFLICT":
                    blocking_reasons.append("E5_SAME_FIRM_OPPOSITE_HEDGE")
                    hedge_conflicts.append(
                        {
                            "code": f.code,
                            "symbol_root": f.subject,
                            "actual": f.actual,
                            "message": f.message,
                        }
                    )
                elif f.severity == "REJECT":
                    blocking_reasons.append(f"E5_{f.code}")

    # 2. Fleet-wide MagicNumber & MagicNumber range collision check across ALL accounts
    seen_single_magics: dict[int, str] = {}
    seen_ranges: list[tuple[int, int, str]] = []

    for rec in roster:
        aid = str(rec.get("account_id") or "UNKNOWN")
        single_magics: list[Any] = []
        for k in ("magic_number", "magic"):
            if k in rec and rec[k] is not None:
                single_magics.append(rec[k])
        if "magics" in rec and rec["magics"] is not None:
            raw_ms = rec["magics"]
            if not isinstance(raw_ms, Sequence) or isinstance(raw_ms, (str, bytes)):
                blocking_reasons.append("E5_INVALID_MAGIC_SPEC")
            else:
                single_magics.extend(list(raw_ms))

        for m_raw in single_magics:
            m_val = _parse_strict_int(m_raw, min_value=1)
            if m_val is None:
                blocking_reasons.append("E5_INVALID_MAGIC_SPEC")
                continue
            if m_val in seen_single_magics and seen_single_magics[m_val] != aid:
                blocking_reasons.append("E5_DUPLICATE_MAGIC_NUMBER")
                magic_collisions.append(
                    {
                        "type": "SINGLE_MAGIC",
                        "magic": m_val,
                        "accounts": [seen_single_magics[m_val], aid],
                    }
                )
            else:
                seen_single_magics[m_val] = aid

        raw_rng = rec.get("magic_range")
        if raw_rng is not None:
            if (
                isinstance(raw_rng, Sequence)
                and not isinstance(raw_rng, (str, bytes))
                and len(raw_rng) == 2
            ):
                lo = _parse_strict_int(raw_rng[0], min_value=1)
                hi = _parse_strict_int(raw_rng[1], min_value=1)
                if lo is None or hi is None or lo > hi:
                    blocking_reasons.append("E5_INVALID_MAGIC_RANGE")
                else:
                    for prev_lo, prev_hi, prev_aid in seen_ranges:
                        if prev_aid != aid and not (hi < prev_lo or lo > prev_hi):
                            blocking_reasons.append("E5_MAGIC_RANGE_COLLISION")
                            magic_collisions.append(
                                {
                                    "type": "RANGE_OVERLAP",
                                    "ranges": [[prev_lo, prev_hi], [lo, hi]],
                                    "accounts": [prev_aid, aid],
                                }
                            )
                    seen_ranges.append((lo, hi, aid))
            else:
                blocking_reasons.append("E5_INVALID_MAGIC_RANGE")

    # Cross-check individual magics falling inside another account's magic_range
    for m_val, aid in seen_single_magics.items():
        for lo, hi, rng_aid in seen_ranges:
            if rng_aid != aid and lo <= m_val <= hi:
                blocking_reasons.append("E5_MAGIC_RANGE_COLLISION")
                magic_collisions.append(
                    {
                        "type": "MAGIC_IN_RANGE",
                        "magic": m_val,
                        "range": [lo, hi],
                        "accounts": [aid, rng_aid],
                    }
                )

    # 3. Duplicate MT5 Portable Directory Paths (and broken-latch E: drive guard)
    seen_portable_dirs: dict[str, str] = {}
    for rec in roster:
        aid = str(rec.get("account_id") or "UNKNOWN")
        has_dir_key = any(k in rec for k in ("mt5_portable_dir", "portable_dir", "terminal_dir"))
        if not has_dir_key:
            continue
        raw_dir = (
            rec.get("mt5_portable_dir")
            if "mt5_portable_dir" in rec
            else (rec.get("portable_dir") if "portable_dir" in rec else rec.get("terminal_dir"))
        )
        if raw_dir is None:
            blocking_reasons.append("E5_INVALID_PORTABLE_DIR")
            continue
        norm_dir = _normalize_portable_dir(raw_dir)
        if norm_dir is None:
            blocking_reasons.append("E5_INVALID_PORTABLE_DIR")
            continue
        if norm_dir.startswith("e:\\") or norm_dir == "e:":
            blocking_reasons.append("E5_FORBIDDEN_PORTABLE_DRIVE_E")
            portable_collisions.append(
                {
                    "type": "FORBIDDEN_E_DRIVE",
                    "account_id": aid,
                    "portable_dir": norm_dir,
                }
            )
        if norm_dir in seen_portable_dirs and seen_portable_dirs[norm_dir] != aid:
            blocking_reasons.append("E5_DUPLICATE_PORTABLE_DIR")
            portable_collisions.append(
                {
                    "type": "DUPLICATE_DIR",
                    "portable_dir": norm_dir,
                    "accounts": [seen_portable_dirs[norm_dir], aid],
                }
            )
        else:
            seen_portable_dirs[norm_dir] = aid

    blocking = len(blocking_reasons) > 0
    return GuardResult(
        guard_id=GUARD_E5,
        passed=not blocking,
        blocking=blocking,
        status="BLOCK" if blocking else "PASS",
        blocking_reasons=_dedupe_codes(blocking_reasons),
        details={
            "accounts_inspected": len(roster),
            "signals_inspected": len(combined_signals),
            "hedge_conflicts": hedge_conflicts,
            "magic_collisions": magic_collisions,
            "portable_dir_collisions": portable_collisions,
            "canonical_symbol_roots_checked": sorted(
                {canonical_symbol_root(str(s.get("symbol") or "")) for s in combined_signals if s.get("symbol")}
            ),
        },
    )


# ---------------------------------------------------------------------------
# E6: Inactivity (21/27/30d), Heartbeat/Flag Ordering, NTP >= 1000ms & Preset SHA Drift
# ---------------------------------------------------------------------------
def evaluate_e6_inactivity_or_feed_stale_lock(
    accounts: Sequence[Mapping[str, Any]],
    proposed_account: Mapping[str, Any] | FleetAccount | None,
    vps_telemetry: Mapping[str, Any] | None,
    *,
    now_dt: datetime,
    max_heartbeat_age_sec: float = DEFAULT_MAX_HEARTBEAT_AGE_SEC,
    ntp_max_offset_ms: float = DEFAULT_NTP_MAX_OFFSET_MS,
    require_flat: bool = False,
) -> GuardResult:
    """E6: Enforce inactivity 21/27/30d tiers, fresh post-flag heartbeat, NTP < 1000ms, and PRESET_SHA256_DRIFT."""
    hb_limit_sec = _parse_finite_float(max_heartbeat_age_sec, strictly_positive=True)
    ntp_limit_ms = _parse_finite_float(ntp_max_offset_ms, strictly_positive=True)
    if hb_limit_sec is None or ntp_limit_ms is None:
        return GuardResult(
            guard_id=GUARD_E6,
            passed=False,
            blocking=True,
            status="BLOCK",
            blocking_reasons=("E6_INVALID_CONFIG_THRESHOLDS",),
        )

    blocking_reasons: list[str] = []
    warnings: list[str] = []
    inactivity_report: list[dict[str, Any]] = []
    preset_drift_accounts: list[dict[str, Any]] = []
    urgent_seen = False

    prop = _account_to_record(proposed_account) if proposed_account is not None else {}
    prop_id = str(prop.get("account_id") or "PROPOSED_ACCOUNT")

    # 1. Trading inactivity (21d warning / 27d urgent / 30d fail-closed lock) & PRESET_SHA256_DRIFT
    inspect_list: list[tuple[dict[str, Any], bool]] = []
    for acct in accounts:
        st = str(acct.get("state") or "")
        if st in _LIVE_RUNNING_STATES:
            inspect_list.append((dict(acct), False))
    if prop:
        inspect_list.append((dict(prop), True))

    for rec, is_proposed in inspect_list:
        aid = str(rec.get("account_id") or prop_id)
        # Inactivity check (fail-closed on None/bool/NaN/Inf/negative when live or explicitly provided)
        if (not is_proposed) or ("days_since_last_trade" in rec):
            raw_days = rec.get("days_since_last_trade")
            days_val = _parse_finite_float(raw_days, min_value=0.0)
            if days_val is None:
                blocking_reasons.append("E6_POISONED_INACTIVITY_DAYS")
                inactivity_report.append(
                    {"account_id": aid, "days_since_last_trade": None, "level": "INVALID_POISONED"}
                )
            elif days_val >= float(INACTIVITY_HARD_LIMIT_DAYS):
                blocking_reasons.append("E6_INACTIVITY_30D_LOCK")
                inactivity_report.append(
                    {"account_id": aid, "days_since_last_trade": round(days_val, 3), "level": "LOCK_30D"}
                )
            elif days_val >= float(INACTIVITY_RED_DAYS):
                urgent_seen = True
                warnings.append("E6_INACTIVITY_27D_URGENT")
                inactivity_report.append(
                    {"account_id": aid, "days_since_last_trade": round(days_val, 3), "level": "URGENT_27D"}
                )
            elif days_val >= float(INACTIVITY_AMBER_DAYS):
                warnings.append("E6_INACTIVITY_21D_WARNING")
                inactivity_report.append(
                    {"account_id": aid, "days_since_last_trade": round(days_val, 3), "level": "WARNING_21D"}
                )
            else:
                inactivity_report.append(
                    {"account_id": aid, "days_since_last_trade": round(days_val, 3), "level": "GREEN"}
                )

        # Open positions strict check (`None` or `bool` or `NaN` MUST fail closed!)
        if (not is_proposed) or ("open_positions" in rec):
            open_pos = _parse_strict_int(rec.get("open_positions"), min_value=0)
            if open_pos is None:
                blocking_reasons.append("E6_INVALID_OPEN_POSITIONS")
            elif require_flat and open_pos != 0:
                blocking_reasons.append("E6_OPEN_POSITIONS_NONZERO")

        # PRESET_SHA256_DRIFT check
        obs_sha = rec.get("preset_sha256")
        exp_sha = rec.get("expected_preset_sha256")
        if not is_proposed:
            if not _is_valid_sha256_hex(obs_sha):
                blocking_reasons.append("E6_PRESET_SHA256_MISSING_OR_INVALID")
                preset_drift_accounts.append({"account_id": aid, "reason": "MISSING_OR_INVALID_OBSERVED_SHA"})
            elif exp_sha not in (None, ""):
                if not _is_valid_sha256_hex(exp_sha):
                    blocking_reasons.append("E6_EXPECTED_PRESET_SHA256_INVALID")
                    preset_drift_accounts.append({"account_id": aid, "reason": "INVALID_EXPECTED_SHA"})
                elif obs_sha != exp_sha:
                    blocking_reasons.append("PRESET_SHA256_DRIFT")
                    preset_drift_accounts.append(
                        {"account_id": aid, "observed_sha256": obs_sha, "expected_sha256": exp_sha}
                    )
        else:
            has_obs = obs_sha not in (None, "")
            has_exp = exp_sha not in (None, "")
            if has_obs and not _is_valid_sha256_hex(obs_sha):
                blocking_reasons.append("E6_PRESET_SHA256_MISSING_OR_INVALID")
                preset_drift_accounts.append({"account_id": aid, "reason": "INVALID_PROPOSED_OBSERVED_SHA"})
            if has_exp and not _is_valid_sha256_hex(exp_sha):
                blocking_reasons.append("E6_EXPECTED_PRESET_SHA256_INVALID")
                preset_drift_accounts.append({"account_id": aid, "reason": "INVALID_PROPOSED_EXPECTED_SHA"})
            if has_obs and has_exp and _is_valid_sha256_hex(obs_sha) and _is_valid_sha256_hex(exp_sha):
                if obs_sha != exp_sha:
                    blocking_reasons.append("PRESET_SHA256_DRIFT")
                    preset_drift_accounts.append(
                        {"account_id": aid, "observed_sha256": obs_sha, "expected_sha256": exp_sha}
                    )
            elif has_exp and not has_obs:
                blocking_reasons.append("PRESET_SHA256_DRIFT")
                preset_drift_accounts.append({"account_id": aid, "reason": "EXPECTED_SHA_SET_BUT_OBSERVED_MISSING"})

    # 2. Heartbeat freshness, post-flag-write ordering & NTP offset (`>= 1000 ms` fail-closed)
    hb_details: dict[str, Any] = {}
    ntp_details: dict[str, Any] = {"max_offset_ms": ntp_limit_ms}

    if vps_telemetry is None or not isinstance(vps_telemetry, Mapping):
        blocking_reasons.append("E6_HEARTBEAT_MISSING")
        blocking_reasons.append("E6_NTP_OFFSET_MISSING")
    else:
        hb = vps_telemetry.get("heartbeat")
        if hb is None or not isinstance(hb, Mapping):
            blocking_reasons.append("E6_HEARTBEAT_MISSING")
        else:
            hb_dt = _parse_utc_datetime(hb.get("utc_ts"))
            if hb_dt is None:
                blocking_reasons.append("E6_HEARTBEAT_INVALID_TIMESTAMP")
            else:
                age_sec = (now_dt - hb_dt).total_seconds()
                hb_details["heartbeat_utc"] = _format_utc_iso(hb_dt)
                hb_details["age_sec"] = round(age_sec, 3)
                if age_sec > hb_limit_sec + 1e-9:
                    blocking_reasons.append("E6_HEARTBEAT_STALE")
                elif age_sec < -DEFAULT_MAX_FUTURE_HEARTBEAT_SKEW_SEC:
                    blocking_reasons.append("E6_HEARTBEAT_FUTURE_TIMESTAMP")

            # Post-write halt flag ordering (`heartbeat.utc_ts < flag_write_utc_ts` -> fail-closed!)
            raw_flag_ts = (
                hb.get("flag_write_utc_ts")
                if "flag_write_utc_ts" in hb
                else vps_telemetry.get("flag_write_utc_ts")
            )
            if raw_flag_ts is not None:
                flag_dt = _parse_utc_datetime(raw_flag_ts)
                if flag_dt is None:
                    blocking_reasons.append("E6_INVALID_FLAG_WRITE_TIMESTAMP")
                else:
                    hb_details["flag_write_utc"] = _format_utc_iso(flag_dt)
                    if hb_dt is not None and hb_dt < flag_dt:
                        blocking_reasons.append("E6_STALE_HEARTBEAT_PRE_FLAG_WRITE")

            # Heartbeat `open_positions`: `None` / `bool` / `NaN` MUST fail closed (`0` is valid!)
            hb_open_pos = _parse_strict_int(hb.get("open_positions"), min_value=0)
            hb_details["open_positions"] = hb_open_pos
            if hb_open_pos is None:
                blocking_reasons.append("E6_HEARTBEAT_INVALID_OPEN_POSITIONS")
            elif (
                (require_flat or str(hb.get("halt_action") or "").upper() == "FLATTEN_ALL")
                and hb_open_pos != 0
            ):
                blocking_reasons.append("E6_HEARTBEAT_OPEN_POSITIONS_NONZERO")

            if "terminal_connected" in hb:
                tc = _parse_strict_bool(hb.get("terminal_connected"))
                if tc is not True:
                    blocking_reasons.append("E6_TERMINAL_DISCONNECTED")

            if "kill_switch" in hb:
                ks = _parse_strict_bool(hb.get("kill_switch"))
                if ks is None or ks is True:
                    blocking_reasons.append("E6_KILL_SWITCH_ACTIVE")

            if "orphan_no_sl" in hb:
                orph = _parse_strict_int(hb.get("orphan_no_sl"), min_value=0)
                if orph is None or orph != 0:
                    blocking_reasons.append("E6_ORPHAN_NO_SL_DETECTED")

            # Optional heartbeat-level preset SHA drift check
            if "preset_sha256" in hb or "expected_preset_sha256" in hb:
                hb_obs_sha = hb.get("preset_sha256")
                hb_exp_sha = hb.get("expected_preset_sha256")
                if not _is_valid_sha256_hex(hb_obs_sha) or (
                    hb_exp_sha not in (None, "") and not _is_valid_sha256_hex(hb_exp_sha)
                ):
                    blocking_reasons.append("E6_PRESET_SHA256_MISSING_OR_INVALID")
                elif hb_exp_sha not in (None, "") and hb_obs_sha != hb_exp_sha:
                    blocking_reasons.append("PRESET_SHA256_DRIFT")
                    preset_drift_accounts.append(
                        {
                            "account_id": "VPS_HEARTBEAT",
                            "observed_sha256": hb_obs_sha,
                            "expected_sha256": hb_exp_sha,
                        }
                    )

        # NTP offset check (`abs(ntp_offset_ms) >= 1000.0` -> fail-closed!)
        ntp_ms: float | None = None
        if "ntp_offset_ms" in vps_telemetry:
            ntp_ms = _parse_finite_float(vps_telemetry.get("ntp_offset_ms"))
        elif "ntp_offset_sec" in vps_telemetry:
            sec_v = _parse_finite_float(vps_telemetry.get("ntp_offset_sec"))
            ntp_ms = sec_v * 1000.0 if sec_v is not None else None

        ntp_details["ntp_offset_ms"] = round(ntp_ms, 3) if ntp_ms is not None else None
        if ntp_ms is None:
            blocking_reasons.append("E6_POISONED_OR_MISSING_NTP_OFFSET")
        elif abs(ntp_ms) >= ntp_limit_ms:
            blocking_reasons.append("E6_NTP_OFFSET_EXCEEDED")

    blocking = len(blocking_reasons) > 0
    if blocking:
        status = "BLOCK"
    elif urgent_seen:
        status = "URGENT"
    elif warnings:
        status = "WARNING"
    else:
        status = "PASS"

    return GuardResult(
        guard_id=GUARD_E6,
        passed=not blocking,
        blocking=blocking,
        status=status,
        blocking_reasons=_dedupe_codes(blocking_reasons),
        warnings=_dedupe_codes(warnings),
        details={
            "inactivity_thresholds_days": {
                "warning": INACTIVITY_AMBER_DAYS,
                "urgent": INACTIVITY_RED_DAYS,
                "lock": INACTIVITY_HARD_LIMIT_DAYS,
            },
            "inactivity_accounts": inactivity_report,
            "heartbeat": hb_details,
            "max_heartbeat_age_sec": hb_limit_sec,
            "ntp": ntp_details,
            "preset_sha256_drift_accounts": preset_drift_accounts,
        },
    )


# ---------------------------------------------------------------------------
# FTMO Scaling Plan Tracker (+25% every 4m, >= +10% net, >= 2 payouts, up to 2M USD)
# ---------------------------------------------------------------------------
def evaluate_ftmo_scaling_plan(
    account: FleetAccount | Mapping[str, Any],
    *,
    now_utc: datetime | str | int | float | None = None,
) -> AccountScalingStatus:
    """Evaluate FTMO Scaling Plan eligibility for a single account (fail-closed on poisoned inputs)."""
    _assert_runtime_safety_invariants()
    rec = _account_to_record(account)
    aid = str(rec.get("account_id") or "UNKNOWN")
    firm_id = _normalize_firm_key(rec.get("firm_id") or rec.get("firm_profile"))
    state = str(rec.get("state") or "")

    now_dt = datetime.now(UTC) if now_utc is None else _parse_utc_datetime(now_utc)
    if now_dt is None:
        return AccountScalingStatus(
            account_id=aid,
            firm_id=firm_id,
            state=state,
            eligible=False,
            at_max_cap=False,
            initial_capital_usd=0.0,
            current_capital_usd=0.0,
            next_capital_usd=0.0,
            increment_usd=0.0,
            current_payout_split_frac=0.80,
            next_payout_split_frac=0.80,
            elapsed_days=0.0,
            elapsed_months=0.0,
            net_profit_frac=0.0,
            payouts_in_window=0,
            missing_requirements=("SCALING_INVALID_NOW_UTC",),
            status_reason="SCALING_INVALID_NOW_UTC",
        )

    cur_cap = _parse_finite_float(rec.get("capital_usd"), strictly_positive=True)
    init_cap = _parse_finite_float(rec.get("initial_capital_usd", rec.get("capital_usd")), strictly_positive=True)
    split_frac = _parse_finite_float(rec.get("payout_split_frac", 0.80), strictly_positive=True, max_value=1.0)
    balance_usd = _parse_finite_float(rec.get("balance_usd", cur_cap), min_value=0.0)
    equity_usd = _parse_finite_float(rec.get("equity_usd", cur_cap), min_value=0.0)

    if cur_cap is None or init_cap is None or split_frac is None or balance_usd is None or equity_usd is None:
        return AccountScalingStatus(
            account_id=aid,
            firm_id=firm_id,
            state=state,
            eligible=False,
            at_max_cap=False,
            initial_capital_usd=init_cap or 0.0,
            current_capital_usd=cur_cap or 0.0,
            next_capital_usd=cur_cap or 0.0,
            increment_usd=0.0,
            current_payout_split_frac=split_frac or 0.80,
            next_payout_split_frac=split_frac or 0.80,
            elapsed_days=0.0,
            elapsed_months=0.0,
            net_profit_frac=0.0,
            payouts_in_window=0,
            missing_requirements=("SCALING_POISONED_ACCOUNT_NUMERIC",),
            status_reason="SCALING_POISONED_ACCOUNT_NUMERIC",
        )

    # Compute elapsed window (prefer explicit scaling_window_months/days, else timestamp delta)
    elapsed_days: float | None = None
    if rec.get("scaling_window_days") is not None:
        elapsed_days = _parse_finite_float(rec.get("scaling_window_days"), min_value=0.0)
    elif rec.get("scaling_window_months") is not None:
        m_val = _parse_finite_float(rec.get("scaling_window_months"), min_value=0.0)
        elapsed_days = m_val * 30.0 if m_val is not None else None
    else:
        anchor_raw = rec.get("last_scale_utc") or rec.get("funded_opened_utc") or rec.get("opened_utc")
        anchor_dt = _parse_utc_datetime(anchor_raw)
        if anchor_dt is not None:
            delta_sec = (now_dt - anchor_dt).total_seconds()
            elapsed_days = delta_sec / 86400.0 if delta_sec >= 0.0 else None

    # Compute 4-month net profit fraction
    net_profit_frac: float | None = None
    if rec.get("scaling_net_profit_frac") is not None:
        net_profit_frac = _parse_finite_float(rec.get("scaling_net_profit_frac"))
    elif rec.get("scaling_net_profit_usd") is not None:
        p_usd = _parse_finite_float(rec.get("scaling_net_profit_usd"))
        net_profit_frac = (p_usd / cur_cap) if p_usd is not None else None
    else:
        cum_gross = _parse_finite_float(rec.get("cumulative_gross_payout_usd", 0.0), min_value=0.0)
        if cum_gross is not None:
            open_profit = equity_usd - cur_cap
            net_profit_frac = (cum_gross + open_profit) / cur_cap

    payouts_raw = rec.get("payouts_since_last_scale", rec.get("payout_cycles_completed", 0))
    payouts_cnt = _parse_strict_int(payouts_raw, min_value=0)

    if elapsed_days is None or net_profit_frac is None or payouts_cnt is None:
        return AccountScalingStatus(
            account_id=aid,
            firm_id=firm_id,
            state=state,
            eligible=False,
            at_max_cap=cur_cap >= FTMO_SCALING_MAX_CAPITAL_USD - 1e-9,
            initial_capital_usd=init_cap,
            current_capital_usd=cur_cap,
            next_capital_usd=cur_cap,
            increment_usd=0.0,
            current_payout_split_frac=split_frac,
            next_payout_split_frac=split_frac,
            elapsed_days=0.0 if elapsed_days is None else elapsed_days,
            elapsed_months=0.0 if elapsed_days is None else elapsed_days / 30.0,
            net_profit_frac=0.0 if net_profit_frac is None else net_profit_frac,
            payouts_in_window=0 if payouts_cnt is None else payouts_cnt,
            missing_requirements=("SCALING_POISONED_PROGRESS_METRICS",),
            status_reason="SCALING_POISONED_PROGRESS_METRICS",
        )

    elapsed_months = elapsed_days / 30.0
    at_max_cap = cur_cap >= FTMO_SCALING_MAX_CAPITAL_USD - 1e-9
    missing: list[str] = []

    if firm_id != "ftmo":
        missing.append("NOT_FTMO_ACCOUNT")
    if state not in _ACTIVE_FUNDED_STATES:
        missing.append("ACCOUNT_NOT_ACTIVE_FUNDED")
    if at_max_cap:
        missing.append("FTMO_SCALING_MAX_2M_CAP_REACHED")
    if elapsed_days + 1e-9 < float(FTMO_SCALING_INTERVAL_CAL_DAYS):
        missing.append("SCALING_WINDOW_LT_4_MONTHS")
    if net_profit_frac + 1e-9 < FTMO_SCALING_MIN_NET_PROFIT_FRAC:
        missing.append("SCALING_PROFIT_LT_10_PCT")
    if payouts_cnt < FTMO_SCALING_MIN_PAYOUTS:
        missing.append("SCALING_PAYOUTS_LT_2")
    if balance_usd + 1e-9 < cur_cap or equity_usd + 1e-9 < cur_cap:
        missing.append("SCALING_ACCOUNT_NOT_IN_PROFIT")
    if str(rec.get("ops4_traffic_light") or "GREEN") == "RED":
        missing.append("SCALING_OPS4_RED_ACTIVE")

    eligible = len(missing) == 0
    if eligible:
        step_usd = init_cap * FTMO_SCALING_STEP_FRAC
        next_cap = min(FTMO_SCALING_MAX_CAPITAL_USD, cur_cap + step_usd)
        inc_usd = max(0.0, next_cap - cur_cap)
        next_split = max(split_frac, FTMO_SCALING_UPGRADED_SPLIT_FRAC)
        reason = "ELIGIBLE_FOR_25PCT_SCALE_UP"
    else:
        next_cap = min(FTMO_SCALING_MAX_CAPITAL_USD, cur_cap)
        inc_usd = 0.0
        next_split = split_frac
        reason = missing[0]

    return AccountScalingStatus(
        account_id=aid,
        firm_id=firm_id,
        state=state,
        eligible=eligible,
        at_max_cap=at_max_cap,
        initial_capital_usd=init_cap,
        current_capital_usd=cur_cap,
        next_capital_usd=next_cap,
        increment_usd=inc_usd,
        current_payout_split_frac=split_frac,
        next_payout_split_frac=next_split,
        elapsed_days=elapsed_days,
        elapsed_months=elapsed_months,
        net_profit_frac=net_profit_frac,
        payouts_in_window=payouts_cnt,
        missing_requirements=tuple(missing),
        status_reason=reason,
    )


def evaluate_fleet_scaling_tracker(
    accounts: Sequence[FleetAccount | Mapping[str, Any]],
    *,
    now_utc: datetime | str | int | float | None = None,
) -> ScalingTrackerSummary:
    """Evaluate FTMO Scaling Plan eligibility across all FTMO Funded accounts in the fleet."""
    statuses: list[AccountScalingStatus] = []
    for acct in accounts:
        rec = _account_to_record(acct)
        firm_id = _normalize_firm_key(rec.get("firm_id") or rec.get("firm_profile"))
        state = str(rec.get("state") or "")
        if firm_id == "ftmo" and state in _ACTIVE_FUNDED_STATES:
            statuses.append(evaluate_ftmo_scaling_plan(rec, now_utc=now_utc))
    statuses.sort(key=lambda s: s.account_id)
    eligible_ids = tuple(s.account_id for s in statuses if s.eligible)
    return ScalingTrackerSummary(
        eligible_count=len(eligible_ids),
        eligible_account_ids=eligible_ids,
        accounts=tuple(statuses),
    )


# ---------------------------------------------------------------------------
# OPS-2 Composition Check on Proposed Admission
# ---------------------------------------------------------------------------
def _evaluate_ops2_admission_checks(
    proposed_account: Mapping[str, Any] | FleetAccount | None,
    *,
    require_ops2_pass: bool = False,
) -> tuple[list[str], list[str]]:
    """Compose OPS-2 preflight & Funded 1.0x lock verification on `proposed_account`."""
    blocking: list[str] = []
    warnings: list[str] = []
    if proposed_account is None:
        return blocking, warnings
    prop = _account_to_record(proposed_account)

    target_phase = str(prop.get("target_phase") or prop.get("account_phase") or "EVAL").strip().upper()
    is_funded = target_phase == "FUNDED" or str(prop.get("state") or "") == FleetState.S5_FUNDED_ACTIVE.value

    if "ops2_preflight_pass" in prop:
        flag = _parse_strict_bool(prop.get("ops2_preflight_pass"))
        if flag is None:
            blocking.append("OPS2_INVALID_PREFLIGHT_FLAG")
        elif flag is False:
            if require_ops2_pass or is_funded:
                blocking.append("OPS2_PREFLIGHT_NOT_PASSED")
            else:
                warnings.append("OPS2_PREFLIGHT_PENDING_BEFORE_LAUNCH")
    elif require_ops2_pass or is_funded:
        blocking.append("OPS2_PREFLIGHT_NOT_PASSED")

    ops2_report = prop.get("ops2_report")
    if ops2_report is not None:
        if isinstance(ops2_report, PreflightReport):
            if ops2_report.order_send_capable is not False or ops2_report.order_send_count != 0:
                raise FleetGuardError(
                    "ORDER_SEND_CAPABLE_TAMPER",
                    "OPS-2 PreflightReport violated ORDER_SEND_CAPABLE == False / ORDER_SEND_COUNT == 0.",
                )
            if ops2_report.passed is not True or ops2_report.can_launch is not True:
                blocking.append("OPS2_PREFLIGHT_REPORT_REJECTED")
                blocking.extend(ops2_report.reject_codes)
        elif isinstance(ops2_report, Mapping):
            if ops2_report.get("order_send_capable") is not False:
                raise FleetGuardError(
                    "ORDER_SEND_CAPABLE_TAMPER",
                    "OPS-2 report dict violated order_send_capable == False.",
                )
            if _parse_strict_bool(ops2_report.get("passed")) is not True:
                blocking.append("OPS2_PREFLIGHT_REPORT_REJECTED")
        else:
            blocking.append("OPS2_INVALID_REPORT_TYPE")

    preset_params = prop.get("preset_params")
    if preset_params is not None:
        if not isinstance(preset_params, Mapping):
            blocking.append("OPS2_INVALID_PRESET_PARAMS")
        elif is_funded:
            lock_findings = check_eval_vs_funded_lock(
                account_phase="FUNDED",
                preset=preset_params,
                preset_name=str(prop.get("preset_name") or "") or None,
                strict_funded_1x=True,
            )
            reject_codes = [f.code for f in lock_findings if f.severity == "REJECT"]
            if reject_codes:
                blocking.extend(reject_codes)

    return blocking, warnings


# ---------------------------------------------------------------------------
# Master Admission Gate Evaluator (`evaluate_fleet_admission`)
# ---------------------------------------------------------------------------
def evaluate_fleet_admission(
    ledger: PropFleetOrchestrator | Mapping[str, Any] | None,
    proposed_account: FleetAccount | Mapping[str, Any] | None,
    vps_telemetry: Mapping[str, Any] | None,
    now_utc: datetime | str | int | float | None = None,
    *,
    catalog_path: Path | str | None = None,
    contracts: Mapping[str, Mapping[str, Any]] | None = None,
    vps_budget: VpsCapacityBudget | None = None,
    ops6_eval_receipt: Mapping[str, Any] | None = None,
    ops6_postmortems: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | None = None,
    active_signals: Sequence[Mapping[str, Any]] | None = None,
    max_heartbeat_age_sec: float = DEFAULT_MAX_HEARTBEAT_AGE_SEC,
    ntp_max_offset_ms: float = DEFAULT_NTP_MAX_OFFSET_MS,
    require_ops2_pass: bool = False,
    require_flat: bool = False,
) -> AdmissionVerdict:
    """Evaluate ALL 6 Fleet Guards (`E1..E6`), OPS-2 composition, and FTMO Scaling Plan fail-closed."""
    _assert_runtime_safety_invariants()

    now_dt = datetime.now(UTC) if now_utc is None else _parse_utc_datetime(now_utc)
    if now_dt is None:
        return AdmissionVerdict(
            allowed=False,
            active_guards=(GUARD_E6,),
            blocking_reasons=("INVALID_NOW_UTC_FAIL_CLOSED",),
            scaling_eligibility=ScalingTrackerSummary(),
            order_send_capable=False,
            order_send_count=0,
            evaluated_utc="",
            fleet_scale_factor=0.0,
            proposed_account_id="",
        )

    accounts, transitions, policy_dict, ledger_meta, ledger_errors = _extract_ledger_view(ledger)

    eff_eval_receipt = ops6_eval_receipt if ops6_eval_receipt is not None else ledger_meta.get("ops6_eval_receipt")
    eff_postmortems = ops6_postmortems if ops6_postmortems is not None else ledger_meta.get("ops6_postmortems")
    eff_signals = active_signals if active_signals is not None else ledger_meta.get("active_signals")

    prop_rec = _account_to_record(proposed_account) if proposed_account is not None else {}
    prop_id = str(prop_rec.get("account_id") or "")

    # Always evaluate ALL 6 guards independently (no short-circuiting)
    g_e1 = evaluate_e1_eval_fail_cooldown(
        accounts,
        transitions,
        now_dt=now_dt,
        ops6_eval_receipt=eff_eval_receipt,
    )
    g_e2 = evaluate_e2_funded_dd_freeze(accounts)
    g_e3 = evaluate_e3_funded_breach_postmortem(
        accounts,
        transitions,
        now_dt=now_dt,
        ops6_postmortems=eff_postmortems,
    )
    g_e4 = evaluate_e4_cap_or_vps_overflow(
        accounts,
        proposed_account,
        vps_telemetry,
        fleet_policy=policy_dict,
        contracts=contracts,
        catalog_path=catalog_path,
        vps_budget=vps_budget,
    )
    g_e5 = evaluate_e5_cross_account_opposite_hedge(
        accounts,
        proposed_account,
        active_signals=eff_signals,
    )
    g_e6 = evaluate_e6_inactivity_or_feed_stale_lock(
        accounts,
        proposed_account,
        vps_telemetry,
        now_dt=now_dt,
        max_heartbeat_age_sec=max_heartbeat_age_sec,
        ntp_max_offset_ms=ntp_max_offset_ms,
        require_flat=require_flat,
    )

    guard_results: dict[str, GuardResult] = {
        GUARD_E1: g_e1,
        GUARD_E2: g_e2,
        GUARD_E3: g_e3,
        GUARD_E4: g_e4,
        GUARD_E5: g_e5,
        GUARD_E6: g_e6,
    }

    ops2_blocking, ops2_warnings = _evaluate_ops2_admission_checks(
        proposed_account,
        require_ops2_pass=require_ops2_pass,
    )

    active_guards: list[str] = []
    blocking_reasons: list[str] = list(ledger_errors)
    warnings: list[str] = list(ops2_warnings)

    for gid in ALL_GUARD_IDS:
        gr = guard_results[gid]
        if gr.blocking:
            active_guards.append(gid)
            blocking_reasons.extend(gr.blocking_reasons)
        warnings.extend(gr.warnings)

    if ops2_blocking:
        blocking_reasons.extend(ops2_blocking)
        if "OPS2_PREFLIGHT" not in active_guards:
            active_guards.append("OPS2_PREFLIGHT")

    scaling_summary = evaluate_fleet_scaling_tracker(accounts, now_utc=now_dt)
    fleet_scale_factor = float(g_e2.details.get("scale_factor", E2_SCALE_GREEN))
    allowed = len(blocking_reasons) == 0

    return AdmissionVerdict(
        allowed=allowed,
        active_guards=tuple(active_guards),
        blocking_reasons=_dedupe_codes(blocking_reasons),
        scaling_eligibility=scaling_summary,
        order_send_capable=False,
        order_send_count=0,
        holdout_cutoff_date=HOLDOUT_CUTOFF_DATE,
        holdout_rows_analysed=HOLDOUT_ROWS_ANALYSED,
        evaluated_utc=_format_utc_iso(now_dt),
        fleet_scale_factor=fleet_scale_factor,
        warnings=_dedupe_codes(warnings),
        guard_results=guard_results,
        proposed_account_id=prop_id,
    )


# ---------------------------------------------------------------------------
# CLI Entrypoint (Read-Only Offline Verification)
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Naqex Fleet Admission & Edge-Case Guards (E1..E6) + FTMO Scaling Plan Tracker "
            "(ORDER_SEND_CAPABLE=False, Holdout 2025+ SEALED)."
        )
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_SAMPLE_FIXTURE_PATH,
        help="Path to fleet_ledger.json (default: sample_fleet_ledger.json).",
    )
    parser.add_argument(
        "--proposed-contract",
        type=str,
        default="ftmo_standard_25k",
        help="Catalog contract_id for proposed new account admission check.",
    )
    parser.add_argument(
        "--proposed-account-id",
        type=str,
        default="FTMO-STD25K-004",
        help="Proposed account_id to evaluate.",
    )
    parser.add_argument(
        "--now-utc",
        type=str,
        default="2026-11-27T08:01:00Z",
        help="Evaluation UTC timestamp (ISO-8601).",
    )
    args = parser.parse_args(argv)

    orch = PropFleetOrchestrator.load(args.ledger, verify_sha256=True)
    catalog = load_firms_catalog()
    proposed = FleetAccount.from_catalog_contract(
        account_id=args.proposed_account_id,
        contract_id=args.proposed_contract,
        contracts=catalog,
    )
    default_vps = {
        "node_name": DEFAULT_VPS_NODE_NAME,
        "cpu_util_pct": 22.5,
        "free_ram_gb": 5.2,
        "active_mt5_terminals": 2,
        "ntp_offset_ms": 18.0,
        "heartbeat": {
            "utc_ts": args.now_utc,
            "open_positions": 0,
            "terminal_connected": True,
            "kill_switch": False,
            "orphan_no_sl": 0,
        },
    }
    verdict = evaluate_fleet_admission(
        orch,
        proposed,
        default_vps,
        now_utc=args.now_utc,
        contracts=catalog,
    )
    print(json.dumps(verdict.to_dict(), indent=2, ensure_ascii=False))
    return 0 if verdict.allowed else 2


__all__ = [
    "ALL_GUARD_IDS",
    "DEFAULT_FIRM_CAP_LIMITS",
    "DEFAULT_FIRMS_CATALOG_PATH",
    "DEFAULT_MAX_HEARTBEAT_AGE_SEC",
    "DEFAULT_NTP_MAX_OFFSET_MS",
    "DEFAULT_VPS_MAX_CPU_PCT",
    "DEFAULT_VPS_MAX_MT5_TERMINALS",
    "DEFAULT_VPS_MIN_DISK_C_FREE_GB",
    "DEFAULT_VPS_MIN_FREE_RAM_GB",
    "DEFAULT_VPS_NODE_NAME",
    "E1_MAX_FAILED_EVALS_BEFORE_BLOCK",
    "E1_TRAILING_WINDOW_DAYS",
    "E2_AMBER_DD_PCT",
    "E2_RED_DD_PCT",
    "E2_SCALE_AMBER",
    "E2_SCALE_GREEN",
    "E2_SCALE_RED",
    "FLEET_GUARDS_SCHEMA_VERSION",
    "FTMO_MAX_ACTIVE_FUNDED_USD",
    "FTMO_MAX_SINGLE_CHALLENGE_USD",
    "FTMO_SCALING_INTERVAL_CAL_DAYS",
    "FTMO_SCALING_INTERVAL_MONTHS",
    "FTMO_SCALING_MAX_CAPITAL_USD",
    "FTMO_SCALING_MIN_NET_PROFIT_FRAC",
    "FTMO_SCALING_MIN_PAYOUTS",
    "FTMO_SCALING_STEP_FRAC",
    "FTMO_SCALING_UPGRADED_SPLIT_FRAC",
    "GUARD_E1",
    "GUARD_E2",
    "GUARD_E3",
    "GUARD_E4",
    "GUARD_E5",
    "GUARD_E6",
    "HOLDOUT_CUTOFF_DATE",
    "HOLDOUT_ROWS_ANALYSED",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "VALID_OPS6_BREACH_CLASSES",
    "AccountScalingStatus",
    "AdmissionVerdict",
    "FleetGuardError",
    "GuardResult",
    "ScalingTrackerSummary",
    "VpsCapacityBudget",
    "evaluate_e1_eval_fail_cooldown",
    "evaluate_e2_funded_dd_freeze",
    "evaluate_e3_funded_breach_postmortem",
    "evaluate_e4_cap_or_vps_overflow",
    "evaluate_e5_cross_account_opposite_hedge",
    "evaluate_e6_inactivity_or_feed_stale_lock",
    "evaluate_fleet_admission",
    "evaluate_fleet_scaling_tracker",
    "evaluate_ftmo_scaling_plan",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
