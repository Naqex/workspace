"""Canonical Prop Fleet Lifecycle State Machine (S0..S7) & Audit-Trail Ledger CLI.

Total Offensive #4 Wave 1A (`W4-G10`): fail-closed offline state machine governing the
full multi-account prop-firm lifecycle from pre-challenge readiness (`S0`) through
P1/P2 sprint evaluations (`S1..S4`), Funded Safe `1.0x` operation (`S5`), OPS-5
white-box payout audit (`S6`), and post-payout 3-bucket capital allocation (`S7`),
plus incident/terminal states (`E1..E3`, `CLOSED_ARCHIVED`).

HARD SAFETY & IMMUTABILITY INVARIANTS (`[ARCH-02]`, `G02`, `G11`, `G16`):
  - Strictly offline & read-only on trading systems:
      `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`.
  - Holdout 2025+ strictly sealed:
      `HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `holdout_rows_analysed = 0`.
  - ZERO `MetaTrader5` imports, ZERO SSH/network calls, ZERO bare `assert` statements.
  - Reuses & composes existing SSOT modules with ZERO duplication:
      * `quant_core.tca` (`canonical_payload_sha256`, `write_atomic_sha256_json`)
      * `quant_factory.live_ops.account_phase_preflight` (OPS-2 lock & inactivity bounds)
      * `quant_factory.prop_challenge_tracker` (`PROP_PROFILES`)
      * `quant_factory.treasury_ledger` (`TreasuryLedger`, `SettledCashEvent`, 3-bucket math)
      * `configs/ssot/firms_catalog.json` & `configs/ssot/fx_rates.json`
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

QUANT_FACTORY_DIR: Final[Path] = Path(__file__).resolve().parents[1]
AI_ENGINES_DIR: Final[Path] = QUANT_FACTORY_DIR.parent
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.tca import canonical_payload_sha256, write_atomic_sha256_json  # noqa: E402

from quant_factory.live_ops.account_phase_preflight import (  # noqa: E402
    INACTIVITY_AMBER_DAYS,
    INACTIVITY_HARD_LIMIT_DAYS,
    INACTIVITY_RED_DAYS,
    PreflightReport,
    check_eval_vs_funded_lock,
    normalize_firm_profile,
)
from quant_factory.prop_challenge_tracker import PROP_PROFILES, PropProfileSpec  # noqa: E402
from quant_factory.treasury_ledger import (  # noqa: E402
    DEFAULT_USD_VND_RATE,
    BucketPolicy,
    PropAccountRecord,
    SettledCashEvent,
    TreasuryEvent,
    TreasuryLedger,
    compute_settled_cash_summary,
)
from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE  # noqa: E402
from quant_factory.wave4 import ORDER_SEND_CAPABLE as _WAVE4_ORDER_SEND_CAPABLE  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety & Schema Constants
# ---------------------------------------------------------------------------
ORDER_SEND_CAPABLE: bool = _WAVE4_ORDER_SEND_CAPABLE
ORDER_SEND_COUNT: int = 0
HOLDOUT_ROWS_ANALYSED: Final[int] = 0

FLEET_LEDGER_SCHEMA_VERSION: Final[str] = "naqex-prop-fleet-ledger-v1"
DEFAULT_FIRMS_CATALOG_PATH: Final[Path] = AI_ENGINES_DIR / "configs" / "ssot" / "firms_catalog.json"
DEFAULT_FX_RATES_PATH: Final[Path] = AI_ENGINES_DIR / "configs" / "ssot" / "fx_rates.json"
DEFAULT_SAMPLE_FIXTURE_PATH: Final[Path] = (
    WORKSPACE_ROOT / ".runtime" / "offensive4" / "fleet" / "sample_fleet_ledger.json"
)

GENESIS_EVENT_SHA256: Final[str] = "0" * 64
_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_EVAL_PRESET_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[_\-\s.])(EVAL|P1|P2|PHASE1|PHASE2|SPRINT|CHALLENGE|VERIFY|VERIFICATION)(?:$|[_\-\s.])",
    re.IGNORECASE,
)

# Canonical preset mode identifiers
PRESET_MODE_NONE: Final[str] = "NONE"
PRESET_MODE_EVAL_P1_SPRINT: Final[str] = "EVAL_P1_SPRINT_4_5X"
PRESET_MODE_EVAL_P2_SPRINT: Final[str] = "EVAL_P2_SPRINT_3_5X"
PRESET_MODE_FUNDED_1X: Final[str] = "FUNDED_1X"

VALID_EVAL_P1_PRESET_MODES: Final[frozenset[str]] = frozenset(
    {
        PRESET_MODE_EVAL_P1_SPRINT,
        "EVAL_P1_SPRINT_4X",
        "EVAL_P1_BALANCED_3X",
    }
)
VALID_EVAL_P2_PRESET_MODES: Final[frozenset[str]] = frozenset(
    {
        PRESET_MODE_EVAL_P2_SPRINT,
        "EVAL_P2_VERIFY_2X",
    }
)
VALID_PRESET_MODES: Final[frozenset[str]] = (
    frozenset({PRESET_MODE_NONE, PRESET_MODE_FUNDED_1X})
    | VALID_EVAL_P1_PRESET_MODES
    | VALID_EVAL_P2_PRESET_MODES
)

VALID_TRAFFIC_LIGHTS: Final[frozenset[str]] = frozenset({"GREEN", "AMBER", "RED"})
VALID_CONCURRENCY_MODES: Final[frozenset[str]] = frozenset(
    {"SINGLE_TICKET", "GATED_STAGGER", "PARALLEL_CAPPED"}
)


# ---------------------------------------------------------------------------
# Canonical 8 Lifecycle States (S0..S7) + 4 Terminal/Incident States
# ---------------------------------------------------------------------------
class FleetState(StrEnum):
    S0_PRE_CHALLENGE = "S0_PRE_CHALLENGE"
    S1_CHALLENGE_P1 = "S1_CHALLENGE_P1"
    S2_PASS_P1_HANDOFF = "S2_PASS_P1_HANDOFF"
    S3_CHALLENGE_P2 = "S3_CHALLENGE_P2"
    S4_PASS_P2_TO_FUNDED_LOCK = "S4_PASS_P2_TO_FUNDED_LOCK"
    S5_FUNDED_ACTIVE = "S5_FUNDED_ACTIVE"
    S6_PAYOUT_AUDIT_AND_HARVEST = "S6_PAYOUT_AUDIT_AND_HARVEST"
    S7_AFTER_PAYOUT_ALLOCATOR = "S7_AFTER_PAYOUT_ALLOCATOR"
    E1_EVAL_FAIL_COOLDOWN = "E1_EVAL_FAIL_COOLDOWN"
    E2_FUNDED_DD_FREEZE = "E2_FUNDED_DD_FREEZE"
    E3_FUNDED_BREACH_POSTMORTEM = "E3_FUNDED_BREACH_POSTMORTEM"
    CLOSED_ARCHIVED = "CLOSED_ARCHIVED"


CANONICAL_LIFECYCLE_STATES: Final[tuple[FleetState, ...]] = (
    FleetState.S0_PRE_CHALLENGE,
    FleetState.S1_CHALLENGE_P1,
    FleetState.S2_PASS_P1_HANDOFF,
    FleetState.S3_CHALLENGE_P2,
    FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
    FleetState.S5_FUNDED_ACTIVE,
    FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
    FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
)

INCIDENT_TERMINAL_STATES: Final[tuple[FleetState, ...]] = (
    FleetState.E1_EVAL_FAIL_COOLDOWN,
    FleetState.E2_FUNDED_DD_FREEZE,
    FleetState.E3_FUNDED_BREACH_POSTMORTEM,
    FleetState.CLOSED_ARCHIVED,
)

# Exact 7 forward lifecycle transitions across the 8 canonical states (S0..S7)
FORWARD_TRANSITIONS: Final[tuple[tuple[FleetState, FleetState], ...]] = (
    (FleetState.S0_PRE_CHALLENGE, FleetState.S1_CHALLENGE_P1),
    (FleetState.S1_CHALLENGE_P1, FleetState.S2_PASS_P1_HANDOFF),
    (FleetState.S2_PASS_P1_HANDOFF, FleetState.S3_CHALLENGE_P2),
    (FleetState.S3_CHALLENGE_P2, FleetState.S4_PASS_P2_TO_FUNDED_LOCK),
    (FleetState.S4_PASS_P2_TO_FUNDED_LOCK, FleetState.S5_FUNDED_ACTIVE),
    (FleetState.S5_FUNDED_ACTIVE, FleetState.S6_PAYOUT_AUDIT_AND_HARVEST),
    (FleetState.S6_PAYOUT_AUDIT_AND_HARVEST, FleetState.S7_AFTER_PAYOUT_ALLOCATOR),
)

ALLOWED_TRANSITIONS: Final[dict[FleetState, frozenset[FleetState]]] = {
    FleetState.S0_PRE_CHALLENGE: frozenset(
        {
            FleetState.S1_CHALLENGE_P1,
            FleetState.CLOSED_ARCHIVED,
        }
    ),
    FleetState.S1_CHALLENGE_P1: frozenset(
        {
            FleetState.S2_PASS_P1_HANDOFF,
            FleetState.E1_EVAL_FAIL_COOLDOWN,
        }
    ),
    FleetState.S2_PASS_P1_HANDOFF: frozenset(
        {
            FleetState.S3_CHALLENGE_P2,
            FleetState.CLOSED_ARCHIVED,
        }
    ),
    FleetState.S3_CHALLENGE_P2: frozenset(
        {
            FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
            FleetState.E1_EVAL_FAIL_COOLDOWN,
        }
    ),
    FleetState.S4_PASS_P2_TO_FUNDED_LOCK: frozenset(
        {
            FleetState.S5_FUNDED_ACTIVE,
            FleetState.CLOSED_ARCHIVED,
        }
    ),
    FleetState.S5_FUNDED_ACTIVE: frozenset(
        {
            FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
            FleetState.E2_FUNDED_DD_FREEZE,
            FleetState.E3_FUNDED_BREACH_POSTMORTEM,
        }
    ),
    FleetState.S6_PAYOUT_AUDIT_AND_HARVEST: frozenset(
        {
            FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
            FleetState.E2_FUNDED_DD_FREEZE,
            FleetState.E3_FUNDED_BREACH_POSTMORTEM,
        }
    ),
    FleetState.S7_AFTER_PAYOUT_ALLOCATOR: frozenset(
        {
            FleetState.S5_FUNDED_ACTIVE,
            FleetState.S0_PRE_CHALLENGE,
            FleetState.CLOSED_ARCHIVED,
        }
    ),
    FleetState.E1_EVAL_FAIL_COOLDOWN: frozenset(
        {
            FleetState.S0_PRE_CHALLENGE,
            FleetState.CLOSED_ARCHIVED,
        }
    ),
    FleetState.E2_FUNDED_DD_FREEZE: frozenset(
        {
            FleetState.S5_FUNDED_ACTIVE,
            FleetState.E3_FUNDED_BREACH_POSTMORTEM,
            FleetState.CLOSED_ARCHIVED,
        }
    ),
    FleetState.E3_FUNDED_BREACH_POSTMORTEM: frozenset(
        {
            FleetState.CLOSED_ARCHIVED,
        }
    ),
    FleetState.CLOSED_ARCHIVED: frozenset(),
}

# Transitions that MUST strictly verify open_positions == 0 (fail-closed)
FLAT_REQUIRED_TRANSITIONS: Final[frozenset[tuple[FleetState, FleetState]]] = frozenset(
    {
        (FleetState.S1_CHALLENGE_P1, FleetState.S2_PASS_P1_HANDOFF),
        (FleetState.S2_PASS_P1_HANDOFF, FleetState.S3_CHALLENGE_P2),
        (FleetState.S3_CHALLENGE_P2, FleetState.S4_PASS_P2_TO_FUNDED_LOCK),
        (FleetState.S4_PASS_P2_TO_FUNDED_LOCK, FleetState.S5_FUNDED_ACTIVE),
        (FleetState.S5_FUNDED_ACTIVE, FleetState.S6_PAYOUT_AUDIT_AND_HARVEST),
        (FleetState.S6_PAYOUT_AUDIT_AND_HARVEST, FleetState.S7_AFTER_PAYOUT_ALLOCATOR),
        (FleetState.S7_AFTER_PAYOUT_ALLOCATOR, FleetState.S5_FUNDED_ACTIVE),
        (FleetState.S7_AFTER_PAYOUT_ALLOCATOR, FleetState.S0_PRE_CHALLENGE),
        (FleetState.E2_FUNDED_DD_FREEZE, FleetState.S5_FUNDED_ACTIVE),
    }
)

# Transitions entering or resuming live Funded operation (CỔNG 2 KHÓA BẮT BUỘC)
FUNDED_ENTRY_TRANSITIONS: Final[frozenset[tuple[FleetState, FleetState]]] = frozenset(
    {
        (FleetState.S4_PASS_P2_TO_FUNDED_LOCK, FleetState.S5_FUNDED_ACTIVE),
        (FleetState.S7_AFTER_PAYOUT_ALLOCATOR, FleetState.S5_FUNDED_ACTIVE),
        (FleetState.E2_FUNDED_DD_FREEZE, FleetState.S5_FUNDED_ACTIVE),
    }
)

STATE_METADATA: Final[dict[str, dict[str, Any]]] = {
    FleetState.S0_PRE_CHALLENGE.value: {
        "order": 0,
        "category": "PRE_CHALLENGE",
        "label_vi": "Chưa thi — kiểm tra đủ cổng tiền kiểm & vốn đệm trước mở vé",
        "label_en": "Pre-Challenge Readiness & Bankroll Gate",
        "expected_preset_mode": PRESET_MODE_NONE,
        "flat_required_on_exit": False,
    },
    FleetState.S1_CHALLENGE_P1.value: {
        "order": 1,
        "category": "EVAL",
        "label_vi": "Đang thi Vòng 1 (Eval Sprint 4.5x, OPS-2 khóa login P1, Taper >= 8.5%)",
        "label_en": "Challenge Phase 1 Active (Eval Sprint 4.5x)",
        "expected_preset_mode": PRESET_MODE_EVAL_P1_SPRINT,
        "flat_required_on_exit": True,
    },
    FleetState.S2_PASS_P1_HANDOFF.value: {
        "order": 2,
        "category": "HANDOFF",
        "label_vi": "Đậu P1 — phẳng lệnh (0 vị thế), chốt log P1, xét mở vé #2 (Gated Stagger)",
        "label_en": "Phase 1 Passed Handoff (Flat Verified)",
        "expected_preset_mode": PRESET_MODE_NONE,
        "flat_required_on_exit": True,
    },
    FleetState.S3_CHALLENGE_P2.value: {
        "order": 3,
        "category": "EVAL",
        "label_vi": "Đang thi Vòng 2 (Eval Sprint 3.5x, mục tiêu +5%, Best-Day & Daily DD guard)",
        "label_en": "Challenge Phase 2 Active (Eval Sprint 3.5x)",
        "expected_preset_mode": PRESET_MODE_EVAL_P2_SPRINT,
        "flat_required_on_exit": True,
    },
    FleetState.S4_PASS_P2_TO_FUNDED_LOCK.value: {
        "order": 4,
        "category": "LOCK_GATE",
        "label_vi": "Đậu P2 — CỔNG 2 KHÓA BẮT BUỘC (0 vị thế, CẤM .set Eval, ÉP Funded 1.0x KS 8%, OPS-2 PASS)",
        "label_en": "Phase 2 Passed — Mandatory Funded 1.0x Dual-Lock Gate",
        "expected_preset_mode": PRESET_MODE_FUNDED_1X,
        "flat_required_on_exit": True,
    },
    FleetState.S5_FUNDED_ACTIVE.value: {
        "order": 5,
        "category": "FUNDED",
        "label_vi": "Đang cầm Funded (1.0x, OPS-4 Xanh/Vàng/Đỏ, theo dõi inactivity 21/27/30 ngày)",
        "label_en": "Funded Account Active (1.0x Safe, OPS-4 + Inactivity Watch)",
        "expected_preset_mode": PRESET_MODE_FUNDED_1X,
        "flat_required_on_exit": True,
    },
    FleetState.S6_PAYOUT_AUDIT_AND_HARVEST.value: {
        "order": 6,
        "category": "PAYOUT",
        "label_vi": "Đủ ngày & lãi >= ngưỡng rút -> 0 vị thế -> OPS-5 gói SHA-256 hộp trắng -> rút tiền",
        "label_en": "Payout Audit (OPS-5 White-Box SHA-256) & Harvest",
        "expected_preset_mode": PRESET_MODE_FUNDED_1X,
        "flat_required_on_exit": True,
    },
    FleetState.S7_AFTER_PAYOUT_ALLOCATOR.value: {
        "order": 7,
        "category": "ALLOCATOR",
        "label_vi": "Tiền đã về + Hoàn phí P1 -> phân bổ 3 giỏ (House Money / Nâng cấp-Thêm vé S0 / Own-Book)",
        "label_en": "Settled Cash & Fee Refund 3-Bucket Allocator",
        "expected_preset_mode": PRESET_MODE_NONE,
        "flat_required_on_exit": True,
    },
    FleetState.E1_EVAL_FAIL_COOLDOWN.value: {
        "order": 91,
        "category": "INCIDENT",
        "label_vi": "Rớt Eval — thời gian làm nguội & hậu kiểm trước khi mở vé mới",
        "label_en": "Eval Failure Cooldown & Review",
        "expected_preset_mode": PRESET_MODE_NONE,
        "flat_required_on_exit": False,
    },
    FleetState.E2_FUNDED_DD_FREEZE.value: {
        "order": 92,
        "category": "INCIDENT",
        "label_vi": "Đóng băng tạm tài khoản Funded (OPS-4 Đỏ / cảnh báo DD)",
        "label_en": "Funded Account DD / OPS-4 Freeze",
        "expected_preset_mode": PRESET_MODE_NONE,
        "flat_required_on_exit": True,
    },
    FleetState.E3_FUNDED_BREACH_POSTMORTEM.value: {
        "order": 93,
        "category": "INCIDENT",
        "label_vi": "Vi phạm cứng Funded — kiểm toán hậu sự cố bắt buộc",
        "label_en": "Funded Breach Mandatory Postmortem",
        "expected_preset_mode": PRESET_MODE_NONE,
        "flat_required_on_exit": False,
    },
    FleetState.CLOSED_ARCHIVED.value: {
        "order": 99,
        "category": "TERMINAL",
        "label_vi": "Đã đóng & lưu trữ vĩnh viễn",
        "label_en": "Closed & Archived (Terminal)",
        "expected_preset_mode": PRESET_MODE_NONE,
        "flat_required_on_exit": False,
    },
}


# ---------------------------------------------------------------------------
# Fail-Closed Exceptions
# ---------------------------------------------------------------------------
class FleetLifecycleError(ValueError):
    """Base fail-closed error carrying machine-readable reason codes."""

    def __init__(self, code: str, message: str, *, reason_codes: Sequence[str] | None = None) -> None:
        self.code = code
        codes = tuple(reason_codes) if reason_codes else (code,)
        if code not in codes:
            codes = (code, *codes)
        self.reason_codes: tuple[str, ...] = codes
        super().__init__(f"[{code}] {message}")


class FleetTransitionError(FleetLifecycleError):
    """Raised when an FSM transition violates state graph or fail-closed safety guards."""


class LedgerValidationError(FleetLifecycleError):
    """Raised when a serialized `fleet_ledger.json` fails schema, integrity, or safety validation."""


# ---------------------------------------------------------------------------
# Strict Primitive Validators (Zero bool/NaN/Inf Fail-Open)
# ---------------------------------------------------------------------------
def _assert_runtime_safety_invariants() -> None:
    if ORDER_SEND_CAPABLE is not False:
        raise FleetTransitionError(
            "ORDER_SEND_CAPABLE_TAMPER",
            f"ORDER_SEND_CAPABLE must be strictly False, observed {ORDER_SEND_CAPABLE!r}.",
        )
    if type(ORDER_SEND_COUNT) is not int or ORDER_SEND_COUNT != 0:
        raise FleetTransitionError(
            "ORDER_SEND_COUNT_TAMPER",
            f"ORDER_SEND_COUNT must be strictly 0, observed {ORDER_SEND_COUNT!r}.",
        )
    if _WAVE4_ORDER_SEND_CAPABLE is not False:
        raise FleetTransitionError(
            "ORDER_SEND_CAPABLE_TAMPER",
            f"quant_factory.wave4.ORDER_SEND_CAPABLE must be strictly False, observed {_WAVE4_ORDER_SEND_CAPABLE!r}.",
        )


def _require_strict_non_negative_int(value: Any, *, field_name: str, error_code: str) -> int:
    if type(value) is not int or value < 0:
        raise FleetTransitionError(
            error_code,
            f"{field_name} must be a strict non-negative int (rejecting bool/None/float/NaN), got {value!r}.",
        )
    return value


def _require_finite_float(
    value: Any,
    *,
    field_name: str,
    error_code: str = "NON_FINITE_OR_INVALID_NUMERIC",
    min_value: float | None = None,
    strictly_positive: bool = False,
    max_value: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FleetTransitionError(
            error_code,
            f"{field_name} must be a finite int/float (rejecting bool/None/str), got {value!r}.",
        )
    out = float(value)
    if not math.isfinite(out):
        raise FleetTransitionError(
            error_code,
            f"{field_name} must be finite (no NaN/Inf), got {value!r}.",
        )
    if strictly_positive and out <= 0.0:
        raise FleetTransitionError(
            error_code,
            f"{field_name} must be strictly > 0, got {out}.",
        )
    if min_value is not None and out < min_value:
        raise FleetTransitionError(
            error_code,
            f"{field_name} must be >= {min_value}, got {out}.",
        )
    if max_value is not None and out > max_value:
        raise FleetTransitionError(
            error_code,
            f"{field_name} must be <= {max_value}, got {out}.",
        )
    return out


def _require_strict_bool(value: Any, *, field_name: str, error_code: str) -> bool:
    if type(value) is not bool:
        raise FleetTransitionError(
            error_code,
            f"{field_name} must be a strict native bool, got {value!r}.",
        )
    return value


def _is_valid_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_HEX_RE.match(value))


def _require_safe_id(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_RE.match(value.strip()):
        raise FleetTransitionError(
            "INVALID_IDENTIFIER",
            f"{field_name} must match ^[A-Za-z0-9][A-Za-z0-9._-]{{0,63}}$, got {value!r}.",
        )
    return value.strip()


def _normalize_utc_ts(value: datetime | str | None = None) -> str:
    if value is None:
        return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise FleetTransitionError(
                "INVALID_UTC_TIMESTAMP",
                f"utc_ts datetime must be timezone-aware, got naive {value!r}.",
            )
        return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise FleetTransitionError("INVALID_UTC_TIMESTAMP", "utc_ts string cannot be empty.")
        parsed_raw = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
        try:
            dt = datetime.fromisoformat(parsed_raw)
        except ValueError as exc:
            raise FleetTransitionError(
                "INVALID_UTC_TIMESTAMP",
                f"Malformed ISO-8601 utc_ts {value!r}: {exc}",
            ) from exc
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise FleetTransitionError(
                "INVALID_UTC_TIMESTAMP",
                f"utc_ts string must include UTC offset or trailing Z, got {value!r}.",
            )
        return dt.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise FleetTransitionError(
        "INVALID_UTC_TIMESTAMP",
        f"Unsupported utc_ts type {type(value).__name__}.",
    )


def _parse_fleet_state(raw: FleetState | str) -> FleetState:
    if isinstance(raw, FleetState):
        return raw
    if isinstance(raw, str):
        try:
            return FleetState(raw.strip())
        except ValueError as exc:
            raise FleetTransitionError(
                "UNKNOWN_STATE",
                f"Unknown fleet state {raw!r}. Expected one of {[s.value for s in FleetState]}.",
            ) from exc
    raise FleetTransitionError("UNKNOWN_STATE", f"Invalid state type {type(raw).__name__}.")


def compute_inactivity_status(days_since_last_trade: float | int) -> str:
    """Reuse exact OPS-2 inactivity thresholds (`21d AMBER` / `27d RED` / `>=30d EXPIRED`)."""
    days = _require_finite_float(
        days_since_last_trade,
        field_name="days_since_last_trade",
        error_code="INVALID_INACTIVITY_DAYS",
        min_value=0.0,
    )
    if days >= float(INACTIVITY_HARD_LIMIT_DAYS):
        return "EXPIRED"
    if days >= float(INACTIVITY_RED_DAYS):
        return "RED"
    if days >= float(INACTIVITY_AMBER_DAYS):
        return "AMBER"
    return "GREEN"


# ---------------------------------------------------------------------------
# SSOT Loaders (firms_catalog.json & fx_rates.json)
# ---------------------------------------------------------------------------
def load_firms_catalog(catalog_path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Read `firms_catalog.json` SSOT contracts (strictly read-only)."""
    path = Path(catalog_path) if catalog_path is not None else DEFAULT_FIRMS_CATALOG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"SSOT firms_catalog.json not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("contracts"), dict):
        raise ValueError(f"Malformed firms_catalog.json (missing contracts dict): {path}")
    return {str(k): dict(v) for k, v in raw["contracts"].items() if isinstance(v, Mapping)}


def load_usd_vnd_rate(fx_path: Path | str | None = None) -> float:
    """Read verified USD/VND rate from `fx_rates.json`, falling back to treasury default if absent."""
    path = Path(fx_path) if fx_path is not None else DEFAULT_FX_RATES_PATH
    if not path.is_file():
        return float(DEFAULT_USD_VND_RATE)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Malformed fx_rates.json: {path}")
    return _require_finite_float(
        raw.get("usd_vnd"),
        field_name="usd_vnd",
        error_code="INVALID_FX_RATE",
        strictly_positive=True,
    )


def _resolve_firm_profile_from_contract(contract: Mapping[str, Any]) -> str:
    firm_id = str(contract.get("firm_id") or "").strip().upper()
    acct_type = str(contract.get("account_type") or "").strip().upper()
    contract_id = str(contract.get("contract_id") or "").strip().upper()
    for candidate in (contract_id, f"{firm_id}_{acct_type}", firm_id):
        norm = normalize_firm_profile(candidate)
        if norm is not None:
            return norm
    return f"{firm_id}_{acct_type}".strip("_") or "UNKNOWN_FIRM"


def resolve_tracker_profile_spec(contract_id: str) -> PropProfileSpec | None:
    """Map an SSOT `contract_id` to its matching `prop_challenge_tracker.PROP_PROFILES` entry if present."""
    alias_map: dict[str, str] = {
        "ftmo_standard_10k": "ftmo_std_10k",
        "ftmo_swing_10k": "ftmo_swing_10k",
        "ftmo_swing_25k": "ftmo_swing_25k",
        "ftmo_swing_50k": "ftmo_swing_50k",
        "ftmo_swing_100k": "ftmo_swing_100k",
        "the5ers_hs_5k_classic": "the5ers_hs_5k",
        "the5ers_hs_5k_new": "the5ers_hs_5k",
    }
    key = alias_map.get(contract_id, contract_id)
    return PROP_PROFILES.get(key)


# ---------------------------------------------------------------------------
# Policies & Typed Ledger Records
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AfterPayoutAllocationPolicy:
    """S7 3-bucket Pareto post-payout allocation policy composed with `treasury_ledger.py`."""

    policy_name: str = "PARETO_3_BUCKET_DEFAULT"
    house_money_pct: float = 0.30
    upgrade_challenge_pct: float = 0.30
    own_book_pct: float = 0.40
    reserve_cap_tickets: float = 5.0
    reference_ticket_usd: float = 109.69

    def validate(self) -> None:
        hm = _require_finite_float(
            self.house_money_pct,
            field_name="house_money_pct",
            error_code="INVALID_ALLOCATION_POLICY",
            min_value=0.0,
            max_value=1.0,
        )
        uc = _require_finite_float(
            self.upgrade_challenge_pct,
            field_name="upgrade_challenge_pct",
            error_code="INVALID_ALLOCATION_POLICY",
            min_value=0.0,
            max_value=1.0,
        )
        ob = _require_finite_float(
            self.own_book_pct,
            field_name="own_book_pct",
            error_code="INVALID_ALLOCATION_POLICY",
            min_value=0.0,
            max_value=1.0,
        )
        if abs((hm + uc + ob) - 1.0) > 1e-6:
            raise FleetTransitionError(
                "INVALID_ALLOCATION_POLICY",
                f"3-bucket percentages must sum to 1.0, got {hm + uc + ob:.6f}.",
            )
        _require_finite_float(
            self.reserve_cap_tickets,
            field_name="reserve_cap_tickets",
            error_code="INVALID_ALLOCATION_POLICY",
            strictly_positive=True,
        )
        _require_finite_float(
            self.reference_ticket_usd,
            field_name="reference_ticket_usd",
            error_code="INVALID_ALLOCATION_POLICY",
            strictly_positive=True,
        )

    def to_treasury_bucket_policy(self) -> BucketPolicy:
        """Bridge cleanly into `treasury_ledger.BucketPolicy`."""
        self.validate()
        pol = BucketPolicy(
            reserve_pct=self.upgrade_challenge_pct,
            own_book_pct=self.own_book_pct,
            ops_tax_pct=self.house_money_pct,
            reserve_cap_tickets=self.reserve_cap_tickets,
            reference_ticket_usd=self.reference_ticket_usd,
        )
        pol.validate()
        return pol

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "policy_name": self.policy_name,
            "house_money_pct": round(self.house_money_pct, 6),
            "upgrade_challenge_pct": round(self.upgrade_challenge_pct, 6),
            "own_book_pct": round(self.own_book_pct, 6),
            "reserve_cap_tickets": round(self.reserve_cap_tickets, 4),
            "reference_ticket_usd": round(self.reference_ticket_usd, 2),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> AfterPayoutAllocationPolicy:
        obj = cls(
            policy_name=str(raw.get("policy_name", "PARETO_3_BUCKET_DEFAULT")),
            house_money_pct=_require_finite_float(
                raw.get("house_money_pct", 0.30),
                field_name="house_money_pct",
                error_code="INVALID_ALLOCATION_POLICY",
                min_value=0.0,
                max_value=1.0,
            ),
            upgrade_challenge_pct=_require_finite_float(
                raw.get("upgrade_challenge_pct", 0.30),
                field_name="upgrade_challenge_pct",
                error_code="INVALID_ALLOCATION_POLICY",
                min_value=0.0,
                max_value=1.0,
            ),
            own_book_pct=_require_finite_float(
                raw.get("own_book_pct", 0.40),
                field_name="own_book_pct",
                error_code="INVALID_ALLOCATION_POLICY",
                min_value=0.0,
                max_value=1.0,
            ),
            reserve_cap_tickets=_require_finite_float(
                raw.get("reserve_cap_tickets", 5.0),
                field_name="reserve_cap_tickets",
                error_code="INVALID_ALLOCATION_POLICY",
                strictly_positive=True,
            ),
            reference_ticket_usd=_require_finite_float(
                raw.get("reference_ticket_usd", 109.69),
                field_name="reference_ticket_usd",
                error_code="INVALID_ALLOCATION_POLICY",
                strictly_positive=True,
            ),
        )
        obj.validate()
        return obj


@dataclass(frozen=True)
class FleetPolicy:
    """Fleet concurrency & bankroll envelope consumed by admission guards & Web UI."""

    concurrency_mode: str = "GATED_STAGGER"
    max_concurrent_evals: int = 2
    max_concurrent_funded: int = 4
    max_accounts_per_firm: int = 3
    bankroll_budget_usd: float = 600.0

    def validate(self) -> None:
        if self.concurrency_mode not in VALID_CONCURRENCY_MODES:
            raise FleetTransitionError(
                "INVALID_FLEET_POLICY",
                f"concurrency_mode must be in {sorted(VALID_CONCURRENCY_MODES)}, got {self.concurrency_mode!r}.",
            )
        _require_strict_non_negative_int(
            self.max_concurrent_evals, field_name="max_concurrent_evals", error_code="INVALID_FLEET_POLICY"
        )
        _require_strict_non_negative_int(
            self.max_concurrent_funded, field_name="max_concurrent_funded", error_code="INVALID_FLEET_POLICY"
        )
        _require_strict_non_negative_int(
            self.max_accounts_per_firm, field_name="max_accounts_per_firm", error_code="INVALID_FLEET_POLICY"
        )
        _require_finite_float(
            self.bankroll_budget_usd,
            field_name="bankroll_budget_usd",
            error_code="INVALID_FLEET_POLICY",
            strictly_positive=True,
        )

    def to_dict(self, *, usd_vnd_rate: float) -> dict[str, Any]:
        self.validate()
        return {
            "concurrency_mode": self.concurrency_mode,
            "max_concurrent_evals": self.max_concurrent_evals,
            "max_concurrent_funded": self.max_concurrent_funded,
            "max_accounts_per_firm": self.max_accounts_per_firm,
            "bankroll_budget_usd": round(self.bankroll_budget_usd, 2),
            "bankroll_budget_vnd": round(self.bankroll_budget_usd * usd_vnd_rate, 0),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> FleetPolicy:
        obj = cls(
            concurrency_mode=str(raw.get("concurrency_mode", "GATED_STAGGER")),
            max_concurrent_evals=_require_strict_non_negative_int(
                raw.get("max_concurrent_evals", 2),
                field_name="max_concurrent_evals",
                error_code="INVALID_FLEET_POLICY",
            ),
            max_concurrent_funded=_require_strict_non_negative_int(
                raw.get("max_concurrent_funded", 4),
                field_name="max_concurrent_funded",
                error_code="INVALID_FLEET_POLICY",
            ),
            max_accounts_per_firm=_require_strict_non_negative_int(
                raw.get("max_accounts_per_firm", 3),
                field_name="max_accounts_per_firm",
                error_code="INVALID_FLEET_POLICY",
            ),
            bankroll_budget_usd=_require_finite_float(
                raw.get("bankroll_budget_usd", 600.0),
                field_name="bankroll_budget_usd",
                error_code="INVALID_FLEET_POLICY",
                strictly_positive=True,
            ),
        )
        obj.validate()
        return obj


@dataclass
class FleetAccount:
    """Single prop account state tracked through `S0..S7` + incident/terminal states."""

    account_id: str
    contract_id: str
    firm_id: str
    firm_profile: str
    display_name: str
    capital_usd: float
    ticket_fee_usd: float
    payout_split_frac: float = 0.80
    p1_target_frac: float = 0.10
    p2_target_frac: float = 0.05
    daily_loss_limit_frac: float = 0.05
    static_loss_limit_frac: float = 0.10
    min_trading_days: int = 4
    min_payout_usd: float = 50.0
    payout_cycle_cal_days: int = 14
    fee_refund_external_cash_frac: float = 1.0
    fee_refund_hub_credit_frac: float = 0.0
    reset_tz: str = "Europe/Prague"
    available_vn: bool = True
    state: FleetState = FleetState.S0_PRE_CHALLENGE
    preset_mode: str = PRESET_MODE_NONE
    preset_name: str = ""
    preset_sha256: str = ""
    expected_preset_sha256: str = ""
    ops2_preflight_pass: bool = False
    ops4_traffic_light: str = "GREEN"
    open_positions: int = 0
    equity_usd: float | None = None
    balance_usd: float | None = None
    peak_equity_usd: float | None = None
    daily_dd_pct: float = 0.0
    static_dd_pct: float = 0.0
    trading_days_completed: int = 0
    cycle_days_elapsed: int = 0
    days_since_last_trade: float = 0.0
    best_day_share: float = 0.0
    payout_cycles_completed: int = 0
    cumulative_gross_payout_usd: float = 0.0
    cumulative_net_payout_usd: float = 0.0
    fee_refunded: bool = False
    fee_refund_usd: float = 0.0
    ops5_audit_bundle_sha256: str = ""
    parent_account_id: str | None = None
    cooldown_until_utc: str | None = None
    opened_utc: str = ""
    last_transition_utc: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        self.account_id = _require_safe_id(self.account_id, field_name="account_id")
        self.contract_id = _require_safe_id(self.contract_id, field_name="contract_id")
        self.state = _parse_fleet_state(self.state)
        self.capital_usd = _require_finite_float(
            self.capital_usd, field_name="capital_usd", error_code="INVALID_CAPITAL_USD", strictly_positive=True
        )
        self.ticket_fee_usd = _require_finite_float(
            self.ticket_fee_usd, field_name="ticket_fee_usd", error_code="INVALID_TICKET_FEE_USD", min_value=0.0
        )
        self.payout_split_frac = _require_finite_float(
            self.payout_split_frac,
            field_name="payout_split_frac",
            error_code="INVALID_SPLIT_FRAC",
            strictly_positive=True,
            max_value=1.0,
        )
        self.p1_target_frac = _require_finite_float(
            self.p1_target_frac, field_name="p1_target_frac", min_value=0.0, max_value=1.0
        )
        self.p2_target_frac = _require_finite_float(
            self.p2_target_frac, field_name="p2_target_frac", min_value=0.0, max_value=1.0
        )
        self.daily_loss_limit_frac = _require_finite_float(
            self.daily_loss_limit_frac, field_name="daily_loss_limit_frac", strictly_positive=True, max_value=1.0
        )
        self.static_loss_limit_frac = _require_finite_float(
            self.static_loss_limit_frac, field_name="static_loss_limit_frac", strictly_positive=True, max_value=1.0
        )
        self.min_trading_days = _require_strict_non_negative_int(
            self.min_trading_days, field_name="min_trading_days", error_code="INVALID_MIN_TRADING_DAYS"
        )
        self.min_payout_usd = _require_finite_float(
            self.min_payout_usd, field_name="min_payout_usd", min_value=0.0
        )
        self.payout_cycle_cal_days = _require_strict_non_negative_int(
            self.payout_cycle_cal_days, field_name="payout_cycle_cal_days", error_code="INVALID_PAYOUT_CYCLE_DAYS"
        )
        self.fee_refund_external_cash_frac = _require_finite_float(
            self.fee_refund_external_cash_frac,
            field_name="fee_refund_external_cash_frac",
            min_value=0.0,
            max_value=1.0,
        )
        self.fee_refund_hub_credit_frac = _require_finite_float(
            self.fee_refund_hub_credit_frac,
            field_name="fee_refund_hub_credit_frac",
            min_value=0.0,
            max_value=1.0,
        )
        self.available_vn = _require_strict_bool(
            self.available_vn, field_name="available_vn", error_code="INVALID_AVAILABLE_VN"
        )
        self.ops2_preflight_pass = _require_strict_bool(
            self.ops2_preflight_pass, field_name="ops2_preflight_pass", error_code="INVALID_OPS2_PREFLIGHT_FLAG"
        )
        if self.ops4_traffic_light not in VALID_TRAFFIC_LIGHTS:
            raise FleetTransitionError(
                "INVALID_OPS4_TRAFFIC_LIGHT",
                f"ops4_traffic_light must be in {sorted(VALID_TRAFFIC_LIGHTS)}, got {self.ops4_traffic_light!r}.",
            )
        self.open_positions = _require_strict_non_negative_int(
            self.open_positions, field_name="open_positions", error_code="INVALID_OPEN_POSITIONS"
        )
        raw_eq = self.capital_usd if self.equity_usd is None else self.equity_usd
        self.equity_usd = _require_finite_float(
            raw_eq, field_name="equity_usd", error_code="INVALID_EQUITY_USD", min_value=0.0
        )
        raw_bal = self.equity_usd if self.balance_usd is None else self.balance_usd
        self.balance_usd = _require_finite_float(
            raw_bal, field_name="balance_usd", error_code="INVALID_BALANCE_USD", min_value=0.0
        )
        raw_peak = max(self.capital_usd, self.equity_usd) if self.peak_equity_usd is None else self.peak_equity_usd
        self.peak_equity_usd = _require_finite_float(
            raw_peak, field_name="peak_equity_usd", error_code="INVALID_PEAK_EQUITY_USD", min_value=0.0
        )
        self.daily_dd_pct = _require_finite_float(
            self.daily_dd_pct,
            field_name="daily_dd_pct",
            error_code="INVALID_DAILY_DD_PCT",
            min_value=0.0,
            max_value=100.0,
        )
        self.static_dd_pct = _require_finite_float(
            self.static_dd_pct,
            field_name="static_dd_pct",
            error_code="INVALID_STATIC_DD_PCT",
            min_value=0.0,
            max_value=100.0,
        )
        self.trading_days_completed = _require_strict_non_negative_int(
            self.trading_days_completed, field_name="trading_days_completed", error_code="INVALID_TRADING_DAYS"
        )
        self.cycle_days_elapsed = _require_strict_non_negative_int(
            self.cycle_days_elapsed, field_name="cycle_days_elapsed", error_code="INVALID_CYCLE_DAYS"
        )
        self.days_since_last_trade = _require_finite_float(
            self.days_since_last_trade,
            field_name="days_since_last_trade",
            error_code="INVALID_INACTIVITY_DAYS",
            min_value=0.0,
        )
        self.best_day_share = _require_finite_float(
            self.best_day_share, field_name="best_day_share", error_code="INVALID_BEST_DAY_SHARE", min_value=0.0
        )
        self.payout_cycles_completed = _require_strict_non_negative_int(
            self.payout_cycles_completed, field_name="payout_cycles_completed", error_code="INVALID_PAYOUT_CYCLES"
        )
        self.cumulative_gross_payout_usd = _require_finite_float(
            self.cumulative_gross_payout_usd, field_name="cumulative_gross_payout_usd", min_value=0.0
        )
        self.cumulative_net_payout_usd = _require_finite_float(
            self.cumulative_net_payout_usd, field_name="cumulative_net_payout_usd", min_value=0.0
        )
        self.fee_refunded = _require_strict_bool(
            self.fee_refunded, field_name="fee_refunded", error_code="INVALID_FEE_REFUNDED_FLAG"
        )
        self.fee_refund_usd = _require_finite_float(
            self.fee_refund_usd, field_name="fee_refund_usd", min_value=0.0
        )
        if self.opened_utc:
            self.opened_utc = _normalize_utc_ts(self.opened_utc)
        if self.last_transition_utc:
            self.last_transition_utc = _normalize_utc_ts(self.last_transition_utc)
        if self.cooldown_until_utc is not None:
            self.cooldown_until_utc = _normalize_utc_ts(self.cooldown_until_utc)

    @classmethod
    def from_catalog_contract(
        cls,
        *,
        account_id: str,
        contract_id: str,
        contracts: Mapping[str, Mapping[str, Any]] | None = None,
        use_promo_fee: bool = True,
        display_name: str | None = None,
        parent_account_id: str | None = None,
        opened_utc: str | None = None,
        notes: str = "",
    ) -> FleetAccount:
        catalog = contracts if contracts is not None else load_firms_catalog()
        if contract_id not in catalog:
            raise FleetTransitionError(
                "UNKNOWN_CONTRACT_ID",
                f"Contract '{contract_id}' not found in SSOT firms_catalog.json.",
            )
        c = catalog[contract_id]
        available_vn = bool(c.get("available_vn", False))
        raw_fee = c.get("fee_promo_usd") if use_promo_fee else c.get("fee_orig_usd")
        if raw_fee is None:
            raw_fee = c.get("fee_orig_usd")
        if not available_vn or raw_fee is None:
            raise FleetTransitionError(
                "CONTRACT_UNAVAILABLE_VN",
                f"Contract '{contract_id}' is unavailable in VN or has no verified checkout fee.",
            )
        tracker_spec = resolve_tracker_profile_spec(contract_id)
        reset_tz = str(c.get("reset_tz") or (tracker_spec.reset_tz if tracker_spec else "Europe/Prague"))
        capital = float(c["capital_usd"])
        ts = _normalize_utc_ts(opened_utc)
        return cls(
            account_id=account_id,
            contract_id=contract_id,
            firm_id=str(c["firm_id"]),
            firm_profile=_resolve_firm_profile_from_contract(c),
            display_name=display_name or f"{c.get('display_name', contract_id)} ({account_id})",
            capital_usd=capital,
            ticket_fee_usd=float(raw_fee),
            payout_split_frac=float(c.get("payout_split_frac", 0.80)),
            p1_target_frac=float(c.get("p1_target_frac", 0.10)),
            p2_target_frac=float(c.get("p2_target_frac", 0.05)),
            daily_loss_limit_frac=float(c.get("daily_loss_limit_frac", 0.05)),
            static_loss_limit_frac=float(c.get("static_loss_limit_frac", 0.10)),
            min_trading_days=int(c.get("min_trading_days", 4)),
            min_payout_usd=float(c.get("min_payout_usd", 50.0)),
            payout_cycle_cal_days=int(c.get("payout_cycle_cal_days", 14)),
            fee_refund_external_cash_frac=float(c.get("fee_refund_external_cash_frac", 1.0)),
            fee_refund_hub_credit_frac=float(c.get("fee_refund_hub_credit_frac", 0.0)),
            reset_tz=reset_tz,
            available_vn=available_vn,
            state=FleetState.S0_PRE_CHALLENGE,
            equity_usd=capital,
            balance_usd=capital,
            peak_equity_usd=capital,
            parent_account_id=parent_account_id,
            opened_utc=ts,
            last_transition_utc=ts,
            notes=notes,
        )

    def to_treasury_account_record(self) -> PropAccountRecord:
        if self.state in (FleetState.S1_CHALLENGE_P1, FleetState.S2_PASS_P1_HANDOFF):
            phase = "CHALLENGE_P1"
            status = "ACTIVE"
        elif self.state in (FleetState.S3_CHALLENGE_P2, FleetState.S4_PASS_P2_TO_FUNDED_LOCK):
            phase = "CHALLENGE_P2"
            status = "ACTIVE"
        elif self.state in (
            FleetState.S5_FUNDED_ACTIVE,
            FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
            FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
        ):
            phase = "FUNDED"
            status = "ACTIVE"
        elif self.state == FleetState.E2_FUNDED_DD_FREEZE:
            phase = "FUNDED"
            status = "FROZEN"
        else:
            phase = "CLOSED"
            status = self.state.value
        return PropAccountRecord(
            account_id=self.account_id,
            firm=self.firm_id.upper(),
            phase=phase,
            nominal_usd=self.capital_usd,
            ticket_fee_usd=self.ticket_fee_usd,
            split_pct=self.payout_split_frac,
            status=status,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "contract_id": self.contract_id,
            "firm_id": self.firm_id,
            "firm_profile": self.firm_profile,
            "display_name": self.display_name,
            "capital_usd": round(self.capital_usd, 2),
            "ticket_fee_usd": round(self.ticket_fee_usd, 2),
            "payout_split_frac": round(self.payout_split_frac, 4),
            "p1_target_frac": round(self.p1_target_frac, 4),
            "p2_target_frac": round(self.p2_target_frac, 4),
            "daily_loss_limit_frac": round(self.daily_loss_limit_frac, 4),
            "static_loss_limit_frac": round(self.static_loss_limit_frac, 4),
            "min_trading_days": self.min_trading_days,
            "min_payout_usd": round(self.min_payout_usd, 2),
            "payout_cycle_cal_days": self.payout_cycle_cal_days,
            "fee_refund_external_cash_frac": round(self.fee_refund_external_cash_frac, 4),
            "fee_refund_hub_credit_frac": round(self.fee_refund_hub_credit_frac, 4),
            "reset_tz": self.reset_tz,
            "available_vn": self.available_vn,
            "state": self.state.value,
            "preset_mode": self.preset_mode,
            "preset_name": self.preset_name,
            "preset_sha256": self.preset_sha256,
            "expected_preset_sha256": self.expected_preset_sha256,
            "ops2_preflight_pass": self.ops2_preflight_pass,
            "ops4_traffic_light": self.ops4_traffic_light,
            "open_positions": self.open_positions,
            "equity_usd": round(self.equity_usd, 2),
            "balance_usd": round(self.balance_usd, 2),
            "peak_equity_usd": round(self.peak_equity_usd, 2),
            "daily_dd_pct": round(self.daily_dd_pct, 4),
            "static_dd_pct": round(self.static_dd_pct, 4),
            "trading_days_completed": self.trading_days_completed,
            "cycle_days_elapsed": self.cycle_days_elapsed,
            "days_since_last_trade": round(self.days_since_last_trade, 2),
            "inactivity_status": compute_inactivity_status(self.days_since_last_trade),
            "best_day_share": round(self.best_day_share, 4),
            "payout_cycles_completed": self.payout_cycles_completed,
            "cumulative_gross_payout_usd": round(self.cumulative_gross_payout_usd, 2),
            "cumulative_net_payout_usd": round(self.cumulative_net_payout_usd, 2),
            "fee_refunded": self.fee_refunded,
            "fee_refund_usd": round(self.fee_refund_usd, 2),
            "ops5_audit_bundle_sha256": self.ops5_audit_bundle_sha256,
            "parent_account_id": self.parent_account_id,
            "cooldown_until_utc": self.cooldown_until_utc,
            "opened_utc": self.opened_utc,
            "last_transition_utc": self.last_transition_utc,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> FleetAccount:
        return cls(
            account_id=str(raw["account_id"]),
            contract_id=str(raw["contract_id"]),
            firm_id=str(raw["firm_id"]),
            firm_profile=str(raw["firm_profile"]),
            display_name=str(raw.get("display_name", raw["account_id"])),
            capital_usd=raw["capital_usd"],
            ticket_fee_usd=raw["ticket_fee_usd"],
            payout_split_frac=raw.get("payout_split_frac", 0.80),
            p1_target_frac=raw.get("p1_target_frac", 0.10),
            p2_target_frac=raw.get("p2_target_frac", 0.05),
            daily_loss_limit_frac=raw.get("daily_loss_limit_frac", 0.05),
            static_loss_limit_frac=raw.get("static_loss_limit_frac", 0.10),
            min_trading_days=raw.get("min_trading_days", 4),
            min_payout_usd=raw.get("min_payout_usd", 50.0),
            payout_cycle_cal_days=raw.get("payout_cycle_cal_days", 14),
            fee_refund_external_cash_frac=raw.get("fee_refund_external_cash_frac", 1.0),
            fee_refund_hub_credit_frac=raw.get("fee_refund_hub_credit_frac", 0.0),
            reset_tz=str(raw.get("reset_tz", "Europe/Prague")),
            available_vn=raw.get("available_vn", False),
            state=_parse_fleet_state(raw["state"]),
            preset_mode=str(raw.get("preset_mode", PRESET_MODE_NONE)),
            preset_name=str(raw.get("preset_name", "")),
            preset_sha256=str(raw.get("preset_sha256", "")),
            expected_preset_sha256=str(raw.get("expected_preset_sha256", "")),
            ops2_preflight_pass=raw.get("ops2_preflight_pass", False),
            ops4_traffic_light=str(raw.get("ops4_traffic_light", "GREEN")),
            open_positions=raw.get("open_positions", 0),
            equity_usd=raw.get("equity_usd", raw["capital_usd"]),
            balance_usd=raw.get("balance_usd", raw["capital_usd"]),
            peak_equity_usd=raw.get("peak_equity_usd", raw["capital_usd"]),
            daily_dd_pct=raw.get("daily_dd_pct", 0.0),
            static_dd_pct=raw.get("static_dd_pct", 0.0),
            trading_days_completed=raw.get("trading_days_completed", 0),
            cycle_days_elapsed=raw.get("cycle_days_elapsed", 0),
            days_since_last_trade=raw.get("days_since_last_trade", 0.0),
            best_day_share=raw.get("best_day_share", 0.0),
            payout_cycles_completed=raw.get("payout_cycles_completed", 0),
            cumulative_gross_payout_usd=raw.get("cumulative_gross_payout_usd", 0.0),
            cumulative_net_payout_usd=raw.get("cumulative_net_payout_usd", 0.0),
            fee_refunded=raw.get("fee_refunded", False),
            fee_refund_usd=raw.get("fee_refund_usd", 0.0),
            ops5_audit_bundle_sha256=str(raw.get("ops5_audit_bundle_sha256", "")),
            parent_account_id=raw.get("parent_account_id"),
            cooldown_until_utc=raw.get("cooldown_until_utc"),
            opened_utc=str(raw.get("opened_utc", "")),
            last_transition_utc=str(raw.get("last_transition_utc", "")),
            notes=str(raw.get("notes", "")),
        )


@dataclass(frozen=True)
class TransitionEvent:
    """Immutable hash-chained audit-trail entry emitted for every accepted FSM transition."""

    event_id: str
    seq: int
    utc_ts: str
    account_id: str
    from_state: str
    to_state: str
    actor: str
    ops2_preflight_pass: bool
    open_positions: int
    preset_mode: str
    preset_sha256: str
    reason_codes: tuple[str, ...]
    order_send_capable: bool = False
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)
    allocation_result: dict[str, Any] | None = None
    prev_event_sha256: str = GENESIS_EVENT_SHA256
    event_sha256: str = ""

    def body_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "seq": self.seq,
            "utc_ts": self.utc_ts,
            "account_id": self.account_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor,
            "ops2_preflight_pass": self.ops2_preflight_pass,
            "open_positions": self.open_positions,
            "preset_mode": self.preset_mode,
            "preset_sha256": self.preset_sha256,
            "reason_codes": list(self.reason_codes),
            "order_send_capable": self.order_send_capable,
            "metrics_snapshot": self.metrics_snapshot,
            "allocation_result": self.allocation_result,
            "prev_event_sha256": self.prev_event_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        out = self.body_dict()
        out["event_sha256"] = self.event_sha256 or compute_event_sha256(out)
        return out


def compute_event_sha256(event_body: Mapping[str, Any]) -> str:
    """Deterministic SHA-256 over a single transition event excluding `event_sha256`."""
    cleaned = {k: v for k, v in event_body.items() if k != "event_sha256"}
    raw = json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Prop Fleet Lifecycle Orchestrator (S0..S7 FSM + Treasury Composition)
# ---------------------------------------------------------------------------
class PropFleetOrchestrator:
    """Fail-closed Prop Fleet Lifecycle State Machine & Audit-Trail Ledger."""

    def __init__(
        self,
        *,
        ledger_id: str = "naqex-prop-fleet-main",
        usd_vnd_rate: float | None = None,
        allocation_policy: AfterPayoutAllocationPolicy | None = None,
        fleet_policy: FleetPolicy | None = None,
        created_utc: str | None = None,
    ) -> None:
        _assert_runtime_safety_invariants()
        self.ledger_id: str = _require_safe_id(ledger_id, field_name="ledger_id")
        self.usd_vnd_rate: float = _require_finite_float(
            usd_vnd_rate if usd_vnd_rate is not None else load_usd_vnd_rate(),
            field_name="usd_vnd_rate",
            error_code="INVALID_FX_RATE",
            strictly_positive=True,
        )
        self.allocation_policy: AfterPayoutAllocationPolicy = allocation_policy or AfterPayoutAllocationPolicy()
        self.allocation_policy.validate()
        self.fleet_policy: FleetPolicy = fleet_policy or FleetPolicy()
        self.fleet_policy.validate()
        self.created_utc: str = _normalize_utc_ts(created_utc)
        self.updated_utc: str = self.created_utc

        self.accounts: dict[str, FleetAccount] = {}
        self.transitions: list[TransitionEvent] = []
        self._treasury_events: list[TreasuryEvent] = []
        self._settled_cash_events: list[SettledCashEvent] = []
        self._house_money_usd: float = 0.0
        self._upgrade_challenge_usd: float = 0.0
        self._own_book_usd: float = 0.0

    def register_account(self, account: FleetAccount) -> FleetAccount:
        """Register an account into the fleet (must be unique `account_id` and start at `S0_PRE_CHALLENGE`)."""
        _assert_runtime_safety_invariants()
        if account.account_id in self.accounts:
            raise FleetTransitionError(
                "DUPLICATE_ACCOUNT_ID",
                f"Account '{account.account_id}' is already registered in ledger '{self.ledger_id}'.",
            )
        if account.state != FleetState.S0_PRE_CHALLENGE:
            raise FleetTransitionError(
                "INITIAL_STATE_MUST_BE_S0",
                f"New account '{account.account_id}' must start at S0_PRE_CHALLENGE, got {account.state.value}.",
            )
        self.accounts[account.account_id] = account
        if account.opened_utc and account.opened_utc > self.updated_utc:
            self.updated_utc = account.opened_utc
        return account

    def register_from_catalog(
        self,
        *,
        account_id: str,
        contract_id: str,
        contracts: Mapping[str, Mapping[str, Any]] | None = None,
        use_promo_fee: bool = True,
        display_name: str | None = None,
        parent_account_id: str | None = None,
        opened_utc: str | None = None,
        notes: str = "",
    ) -> FleetAccount:
        acct = FleetAccount.from_catalog_contract(
            account_id=account_id,
            contract_id=contract_id,
            contracts=contracts,
            use_promo_fee=use_promo_fee,
            display_name=display_name,
            parent_account_id=parent_account_id,
            opened_utc=opened_utc,
            notes=notes,
        )
        return self.register_account(acct)

    def _validate_funded_lock_gate(
        self,
        *,
        account: FleetAccount,
        open_positions: int,
        preset_mode: str,
        preset_sha256: str,
        expected_preset_sha256: str | None,
        preset_name: str,
        ops2_preflight_pass: bool,
        preset_params: Mapping[str, Any] | None,
        ops2_report: PreflightReport | None,
    ) -> list[str]:
        """Enforce CỔNG 2 KHÓA BẮT BUỘC for entering/resuming `S5_FUNDED_ACTIVE`."""
        reasons: list[str] = []
        if open_positions != 0:
            raise FleetTransitionError(
                "OPEN_POSITIONS_NONZERO_HANDOFF",
                f"Account '{account.account_id}' cannot enter Funded with open_positions={open_positions} (must be 0).",
            )
        if preset_mode != PRESET_MODE_FUNDED_1X:
            code = (
                "EVAL_PRESET_FORBIDDEN_ON_FUNDED"
                if "EVAL" in preset_mode.upper() or "SPRINT" in preset_mode.upper()
                else "FUNDED_PRESET_MODE_REQUIRED"
            )
            raise FleetTransitionError(
                code,
                f"HARD REJECT: S4->S5 / Funded entry requires preset_mode=='{PRESET_MODE_FUNDED_1X}', "
                f"got {preset_mode!r}.",
            )
        if preset_name and _EVAL_PRESET_NAME_RE.search(preset_name):
            raise FleetTransitionError(
                "EVAL_PRESET_FORBIDDEN_ON_FUNDED",
                f"HARD REJECT: Eval/Sprint preset filename '{preset_name}' forbidden on Funded account.",
            )
        if ops2_preflight_pass is not True:
            raise FleetTransitionError(
                "OPS2_PREFLIGHT_NOT_PASSED",
                f"Account '{account.account_id}' requires ops2_preflight_pass is True before entering Funded.",
            )
        if not _is_valid_sha256_hex(preset_sha256):
            raise FleetTransitionError(
                "PRESET_SHA256_MISSING_OR_INVALID",
                f"Funded entry requires a valid 64-hex preset_sha256, got {preset_sha256!r}.",
            )
        eff_expected_sha = expected_preset_sha256 or account.expected_preset_sha256
        if eff_expected_sha:
            if not _is_valid_sha256_hex(eff_expected_sha):
                raise FleetTransitionError(
                    "EXPECTED_PRESET_SHA256_INVALID",
                    f"expected_preset_sha256 is malformed: {eff_expected_sha!r}.",
                )
            if preset_sha256 != eff_expected_sha:
                raise FleetTransitionError(
                    "PRESET_SHA256_DRIFT",
                    f"PRESET_SHA256_DRIFT: observed {preset_sha256} != expected {eff_expected_sha}.",
                )
            reasons.append("PRESET_SHA256_VERIFIED")

        if ops2_report is not None:
            if ops2_report.order_send_capable is not False or ops2_report.order_send_count != 0:
                raise FleetTransitionError(
                    "ORDER_SEND_CAPABLE_TAMPER",
                    "OPS-2 PreflightReport violated ORDER_SEND_CAPABLE == False / ORDER_SEND_COUNT == 0.",
                )
            if ops2_report.passed is not True or ops2_report.can_launch is not True:
                raise FleetTransitionError(
                    "OPS2_PREFLIGHT_REPORT_REJECTED",
                    f"OPS-2 PreflightReport failed: {ops2_report.reject_codes}.",
                    reason_codes=ops2_report.reject_codes or ("OPS2_PREFLIGHT_REPORT_REJECTED",),
                )
            if ops2_report.account_phase != "FUNDED":
                raise FleetTransitionError(
                    "OPS2_PHASE_MISMATCH_FOR_FUNDED",
                    f"OPS-2 PreflightReport was run for phase '{ops2_report.account_phase}', not 'FUNDED'.",
                )
            reasons.append("OPS2_REPORT_VERIFIED")

        if preset_params is not None:
            lock_findings = check_eval_vs_funded_lock(
                account_phase="FUNDED",
                preset=preset_params,
                preset_name=preset_name or None,
                strict_funded_1x=True,
            )
            reject_codes = tuple(f.code for f in lock_findings if f.severity == "REJECT")
            if reject_codes:
                raise FleetTransitionError(
                    reject_codes[0],
                    f"OPS-2 Funded 1.0x lock rejected preset: {reject_codes}.",
                    reason_codes=reject_codes,
                )
            reasons.append("OPS2_PRESET_PARAMS_FUNDED_1X_VERIFIED")

        reasons.extend(["FUNDED_DUAL_LOCK_PASS", "OPS2_PREFLIGHT_PASS", "FLAT_HANDOFF_VERIFIED"])
        return reasons

    def _allocate_settled_payout_s7(
        self,
        *,
        account: FleetAccount,
        utc_ts: str,
        payout_gross_usd: float,
        withdrawal_fee_usd: float,
        fx_bank_fee_usd: float,
        fee_refund_usd: float,
        cycle_id: str,
    ) -> dict[str, Any]:
        """Compute S7 3-bucket allocation and post events into composed `treasury_ledger.py`."""
        self.allocation_policy.validate()
        gross = _require_finite_float(
            payout_gross_usd, field_name="payout_gross_usd", error_code="INVALID_PAYOUT_AMOUNT", strictly_positive=True
        )
        w_fee = _require_finite_float(
            withdrawal_fee_usd, field_name="withdrawal_fee_usd", error_code="INVALID_PAYOUT_FEE", min_value=0.0
        )
        fx_fee = _require_finite_float(
            fx_bank_fee_usd, field_name="fx_bank_fee_usd", error_code="INVALID_PAYOUT_FEE", min_value=0.0
        )
        refund = _require_finite_float(
            fee_refund_usd, field_name="fee_refund_usd", error_code="INVALID_FEE_REFUND", min_value=0.0
        )

        split = account.payout_split_frac
        net_before_rails = gross * split
        net_settled_payout = max(0.0, net_before_rails - w_fee - fx_fee)
        cash_refund = round(refund * account.fee_refund_external_cash_frac, 2) if refund > 0.0 else 0.0
        hub_credit_refund = round(refund * account.fee_refund_hub_credit_frac, 2) if refund > 0.0 else 0.0
        total_settled_cash = round(net_settled_payout + cash_refund, 2)

        reserve_cap_usd = self.allocation_policy.reserve_cap_tickets * max(
            account.ticket_fee_usd, self.allocation_policy.reference_ticket_usd
        )
        raw_house = total_settled_cash * self.allocation_policy.house_money_pct
        raw_upgrade = total_settled_cash * self.allocation_policy.upgrade_challenge_pct
        raw_own = total_settled_cash * self.allocation_policy.own_book_pct

        upgrade_room = max(0.0, reserve_cap_usd - self._upgrade_challenge_usd)
        alloc_upgrade = min(raw_upgrade, upgrade_room)
        overflow_to_own = raw_upgrade - alloc_upgrade
        alloc_own = raw_own + overflow_to_own
        alloc_house = raw_house

        self._house_money_usd = round(self._house_money_usd + alloc_house, 2)
        self._upgrade_challenge_usd = round(self._upgrade_challenge_usd + alloc_upgrade, 2)
        self._own_book_usd = round(self._own_book_usd + alloc_own, 2)

        day_str = utc_ts[:10]
        self._treasury_events.append(
            TreasuryEvent(
                date=day_str,
                event_type="PROP_PAYOUT",
                amount_usd=gross,
                account_id=account.account_id,
                firm=account.firm_id.upper(),
                split_pct=split,
                note=f"S7 settled cycle={cycle_id}",
            )
        )
        self._settled_cash_events.append(
            SettledCashEvent(
                date=day_str,
                event_type="PAYOUT_SETTLED",
                amount_usd=round(net_before_rails, 2),
                account_id=account.account_id,
                firm=account.firm_id.upper(),
                settled_date=day_str,
                withdrawal_fee_usd=w_fee,
                fx_bank_fee_usd=fx_fee,
                cycle_id=cycle_id,
                note=f"S7 settled payout ({account.contract_id})",
            )
        )
        if cash_refund > 0.0:
            self._treasury_events.append(
                TreasuryEvent(
                    date=day_str,
                    event_type="FEE_REFUND",
                    amount_usd=cash_refund,
                    account_id=account.account_id,
                    firm=account.firm_id.upper(),
                    is_hub_credit=False,
                    note="P1 fee external cash refund",
                )
            )
            self._settled_cash_events.append(
                SettledCashEvent(
                    date=day_str,
                    event_type="EXTERNAL_CASH_REFUND",
                    amount_usd=cash_refund,
                    account_id=account.account_id,
                    firm=account.firm_id.upper(),
                    settled_date=day_str,
                    cycle_id=cycle_id,
                    note="P1 fee external cash refund",
                )
            )
        if hub_credit_refund > 0.0:
            self._treasury_events.append(
                TreasuryEvent(
                    date=day_str,
                    event_type="FEE_REFUND",
                    amount_usd=hub_credit_refund,
                    account_id=account.account_id,
                    firm=account.firm_id.upper(),
                    is_hub_credit=True,
                    note="P1 fee hub credit refund (non-withdrawable)",
                )
            )
            self._settled_cash_events.append(
                SettledCashEvent(
                    date=day_str,
                    event_type="HUB_CREDIT_GRANT",
                    amount_usd=hub_credit_refund,
                    account_id=account.account_id,
                    firm=account.firm_id.upper(),
                    settled_date=day_str,
                    cycle_id=cycle_id,
                    note="P1 fee hub credit refund (non-withdrawable)",
                )
            )

        account.payout_cycles_completed += 1
        account.cumulative_gross_payout_usd = round(account.cumulative_gross_payout_usd + gross, 2)
        account.cumulative_net_payout_usd = round(account.cumulative_net_payout_usd + net_settled_payout, 2)
        if refund > 0.0:
            account.fee_refunded = True
            account.fee_refund_usd = round(account.fee_refund_usd + refund, 2)

        return {
            "cycle_id": cycle_id,
            "policy_name": self.allocation_policy.policy_name,
            "gross_payout_usd": round(gross, 2),
            "split_frac": round(split, 4),
            "net_before_rails_usd": round(net_before_rails, 2),
            "withdrawal_and_fx_fees_usd": round(w_fee + fx_fee, 2),
            "net_settled_payout_usd": round(net_settled_payout, 2),
            "cash_fee_refund_usd": cash_refund,
            "hub_credit_refund_usd": hub_credit_refund,
            "total_settled_cash_usd": total_settled_cash,
            "total_settled_cash_vnd": round(total_settled_cash * self.usd_vnd_rate, 0),
            "buckets_usd": {
                "house_money_usd": round(alloc_house, 2),
                "upgrade_challenge_usd": round(alloc_upgrade, 2),
                "own_book_usd": round(alloc_own, 2),
                "overflow_to_own_book_usd": round(overflow_to_own, 2),
            },
            "buckets_vnd": {
                "house_money_vnd": round(alloc_house * self.usd_vnd_rate, 0),
                "upgrade_challenge_vnd": round(alloc_upgrade * self.usd_vnd_rate, 0),
                "own_book_vnd": round(alloc_own * self.usd_vnd_rate, 0),
            },
            "can_fund_next_s0_ticket": self._upgrade_challenge_usd >= account.ticket_fee_usd,
        }

    def transition(
        self,
        *,
        account_id: str,
        to_state: FleetState | str,
        actor: str = "operator",
        utc_ts: datetime | str | None = None,
        open_positions: int = 0,
        ops2_preflight_pass: bool | None = None,
        preset_mode: str | None = None,
        preset_name: str | None = None,
        preset_sha256: str | None = None,
        expected_preset_sha256: str | None = None,
        preset_params: Mapping[str, Any] | None = None,
        ops2_report: PreflightReport | None = None,
        ops4_traffic_light: str | None = None,
        ops5_audit_bundle_sha256: str | None = None,
        equity_usd: float | None = None,
        balance_usd: float | None = None,
        daily_dd_pct: float | None = None,
        static_dd_pct: float | None = None,
        trading_days_completed: int | None = None,
        cycle_days_elapsed: int | None = None,
        days_since_last_trade: float | None = None,
        best_day_share: float | None = None,
        payout_gross_usd: float | None = None,
        withdrawal_fee_usd: float = 0.0,
        fx_bank_fee_usd: float = 0.0,
        fee_refund_usd: float = 0.0,
        cooldown_until_utc: datetime | str | None = None,
        reason_codes: Sequence[str] | None = None,
        notes: str | None = None,
        order_send_capable: Any = False,
    ) -> TransitionEvent:
        """Execute a single fail-closed FSM transition and append an immutable hash-chained event."""
        _assert_runtime_safety_invariants()
        if order_send_capable is not False:
            raise FleetTransitionError(
                "ORDER_SEND_CAPABLE_TAMPER",
                f"Transition payload order_send_capable must be strictly False, got {order_send_capable!r}.",
            )
        if account_id not in self.accounts:
            raise FleetTransitionError("UNKNOWN_ACCOUNT_ID", f"Account '{account_id}' is not registered.")
        if not isinstance(actor, str) or not actor.strip():
            raise FleetTransitionError("INVALID_ACTOR", "actor must be a non-empty string.")

        acct = self.accounts[account_id]
        from_state = acct.state
        target_state = _parse_fleet_state(to_state)
        ts_str = _normalize_utc_ts(utc_ts)

        # 1. Strict transition graph guard (rejects all phase skips & closed-account exits)
        allowed_targets = ALLOWED_TRANSITIONS.get(from_state, frozenset())
        if target_state not in allowed_targets:
            raise FleetTransitionError(
                "INVALID_STATE_TRANSITION",
                f"Transition {from_state.value} -> {target_state.value} is forbidden for '{account_id}'. "
                f"Allowed targets: {sorted(s.value for s in allowed_targets)}.",
            )

        # 2. Strict numeric & type validation on every supplied telemetry field (rejects bool/NaN/Inf/None)
        validated_open_pos = _require_strict_non_negative_int(
            open_positions, field_name="open_positions", error_code="INVALID_OPEN_POSITIONS"
        )
        eff_equity = (
            _require_finite_float(
                equity_usd,
                field_name="equity_usd",
                error_code="INVALID_EQUITY_USD",
                strictly_positive=target_state
                not in (FleetState.E3_FUNDED_BREACH_POSTMORTEM, FleetState.CLOSED_ARCHIVED),
                min_value=0.0,
            )
            if equity_usd is not None
            else acct.equity_usd
        )
        eff_balance = (
            _require_finite_float(
                balance_usd,
                field_name="balance_usd",
                error_code="INVALID_BALANCE_USD",
                min_value=0.0,
            )
            if balance_usd is not None
            else (eff_equity if equity_usd is not None else acct.balance_usd)
        )
        eff_daily_dd = (
            _require_finite_float(
                daily_dd_pct,
                field_name="daily_dd_pct",
                error_code="INVALID_DAILY_DD_PCT",
                min_value=0.0,
                max_value=100.0,
            )
            if daily_dd_pct is not None
            else acct.daily_dd_pct
        )
        eff_static_dd = (
            _require_finite_float(
                static_dd_pct,
                field_name="static_dd_pct",
                error_code="INVALID_STATIC_DD_PCT",
                min_value=0.0,
                max_value=100.0,
            )
            if static_dd_pct is not None
            else acct.static_dd_pct
        )
        eff_trading_days = (
            _require_strict_non_negative_int(
                trading_days_completed, field_name="trading_days_completed", error_code="INVALID_TRADING_DAYS"
            )
            if trading_days_completed is not None
            else acct.trading_days_completed
        )
        eff_cycle_days = (
            _require_strict_non_negative_int(
                cycle_days_elapsed, field_name="cycle_days_elapsed", error_code="INVALID_CYCLE_DAYS"
            )
            if cycle_days_elapsed is not None
            else acct.cycle_days_elapsed
        )
        eff_inact_days = (
            _require_finite_float(
                days_since_last_trade,
                field_name="days_since_last_trade",
                error_code="INVALID_INACTIVITY_DAYS",
                min_value=0.0,
            )
            if days_since_last_trade is not None
            else acct.days_since_last_trade
        )
        eff_best_day = (
            _require_finite_float(
                best_day_share, field_name="best_day_share", error_code="INVALID_BEST_DAY_SHARE", min_value=0.0
            )
            if best_day_share is not None
            else acct.best_day_share
        )
        eff_traffic = ops4_traffic_light if ops4_traffic_light is not None else acct.ops4_traffic_light
        if eff_traffic not in VALID_TRAFFIC_LIGHTS:
            raise FleetTransitionError(
                "INVALID_OPS4_TRAFFIC_LIGHT",
                f"ops4_traffic_light must be in {sorted(VALID_TRAFFIC_LIGHTS)}, got {eff_traffic!r}.",
            )
        eff_ops2_pass = (
            _require_strict_bool(
                ops2_preflight_pass, field_name="ops2_preflight_pass", error_code="INVALID_OPS2_PREFLIGHT_FLAG"
            )
            if ops2_preflight_pass is not None
            else acct.ops2_preflight_pass
        )
        eff_preset_mode = preset_mode if preset_mode is not None else acct.preset_mode
        eff_preset_name = preset_name if preset_name is not None else acct.preset_name
        eff_preset_sha = preset_sha256 if preset_sha256 is not None else acct.preset_sha256
        eff_expected_sha = expected_preset_sha256 if expected_preset_sha256 is not None else acct.expected_preset_sha256
        eff_ops5_sha = (
            ops5_audit_bundle_sha256 if ops5_audit_bundle_sha256 is not None else acct.ops5_audit_bundle_sha256
        )

        # 3. Flat handoff guard on all phase handoffs (`S1->S2`, `S3->S4`, `S5->S6`, etc.)
        edge = (from_state, target_state)
        if edge in FLAT_REQUIRED_TRANSITIONS and validated_open_pos != 0:
            raise FleetTransitionError(
                "OPEN_POSITIONS_NONZERO_HANDOFF",
                f"Transition {from_state.value} -> {target_state.value} requires open_positions == 0, "
                f"got {validated_open_pos}.",
            )

        # 4. Edge-specific domain guards
        auto_reasons: list[str] = []
        allocation_result: dict[str, Any] | None = None

        if edge == (FleetState.S0_PRE_CHALLENGE, FleetState.S1_CHALLENGE_P1):
            if not acct.available_vn:
                raise FleetTransitionError(
                    "CONTRACT_UNAVAILABLE_VN",
                    f"Cannot open P1 on contract '{acct.contract_id}' (available_vn=False).",
                )
            if eff_ops2_pass is not True:
                raise FleetTransitionError(
                    "OPS2_PREFLIGHT_NOT_PASSED",
                    "S0->S1 requires ops2_preflight_pass is True (OPS-2 account login & phase lock).",
                )
            if eff_preset_mode not in VALID_EVAL_P1_PRESET_MODES:
                raise FleetTransitionError(
                    "INVALID_P1_PRESET_MODE",
                    f"S0->S1 requires a P1 Eval preset mode in {sorted(VALID_EVAL_P1_PRESET_MODES)}, "
                    f"got {eff_preset_mode!r}.",
                )
            if not _is_valid_sha256_hex(eff_preset_sha):
                raise FleetTransitionError(
                    "PRESET_SHA256_MISSING_OR_INVALID",
                    f"S0->S1 requires a valid 64-hex preset_sha256, got {eff_preset_sha!r}.",
                )
            if eff_expected_sha and eff_preset_sha != eff_expected_sha:
                raise FleetTransitionError(
                    "PRESET_SHA256_DRIFT",
                    f"PRESET_SHA256_DRIFT on S0->S1: observed {eff_preset_sha} != expected {eff_expected_sha}.",
                )
            auto_reasons.extend(["P1_PREFLIGHT_PASS", "P1_TICKET_OPENED"])

        elif edge == (FleetState.S1_CHALLENGE_P1, FleetState.S2_PASS_P1_HANDOFF):
            p1_gain_frac = (eff_equity - acct.capital_usd) / acct.capital_usd
            if p1_gain_frac + 1e-9 < acct.p1_target_frac:
                raise FleetTransitionError(
                    "P1_TARGET_NOT_MET",
                    f"S1->S2 requires gain >= {acct.p1_target_frac:.2%}, observed {p1_gain_frac:.2%}.",
                )
            if eff_trading_days < acct.min_trading_days:
                raise FleetTransitionError(
                    "MIN_TRADING_DAYS_NOT_MET",
                    f"S1->S2 requires trading_days_completed >= {acct.min_trading_days}, got {eff_trading_days}.",
                )
            auto_reasons.extend(["P1_PASSED_FLAT_VERIFIED", "P1_LOG_SEALED"])
            if self.fleet_policy.concurrency_mode == "GATED_STAGGER":
                auto_reasons.append("GATED_STAGGER_TICKET2_ELIGIBLE")

        elif edge == (FleetState.S2_PASS_P1_HANDOFF, FleetState.S3_CHALLENGE_P2):
            if eff_ops2_pass is not True:
                raise FleetTransitionError(
                    "OPS2_PREFLIGHT_NOT_PASSED",
                    "S2->S3 requires ops2_preflight_pass is True for Phase 2 account login.",
                )
            if eff_preset_mode not in VALID_EVAL_P2_PRESET_MODES:
                raise FleetTransitionError(
                    "INVALID_P2_PRESET_MODE",
                    f"S2->S3 requires a P2 Eval preset mode in {sorted(VALID_EVAL_P2_PRESET_MODES)}, "
                    f"got {eff_preset_mode!r}.",
                )
            if not _is_valid_sha256_hex(eff_preset_sha):
                raise FleetTransitionError(
                    "PRESET_SHA256_MISSING_OR_INVALID",
                    f"S2->S3 requires a valid 64-hex preset_sha256, got {eff_preset_sha!r}.",
                )
            if eff_expected_sha and eff_preset_sha != eff_expected_sha:
                raise FleetTransitionError(
                    "PRESET_SHA256_DRIFT",
                    f"PRESET_SHA256_DRIFT on S2->S3: observed {eff_preset_sha} != expected {eff_expected_sha}.",
                )
            auto_reasons.extend(["P2_PREFLIGHT_PASS", "P2_STARTED"])

        elif edge == (FleetState.S3_CHALLENGE_P2, FleetState.S4_PASS_P2_TO_FUNDED_LOCK):
            p2_gain_frac = (eff_equity - acct.capital_usd) / acct.capital_usd
            if p2_gain_frac + 1e-9 < acct.p2_target_frac:
                raise FleetTransitionError(
                    "P2_TARGET_NOT_MET",
                    f"S3->S4 requires gain >= {acct.p2_target_frac:.2%}, observed {p2_gain_frac:.2%}.",
                )
            if eff_trading_days < acct.min_trading_days:
                raise FleetTransitionError(
                    "MIN_TRADING_DAYS_NOT_MET",
                    f"S3->S4 requires trading_days_completed >= {acct.min_trading_days}, got {eff_trading_days}.",
                )
            auto_reasons.extend(["P2_PASSED_FLAT_VERIFIED", "FUNDED_LOCK_GATE_ENTERED"])

        elif edge in FUNDED_ENTRY_TRANSITIONS:
            lock_reasons = self._validate_funded_lock_gate(
                account=acct,
                open_positions=validated_open_pos,
                preset_mode=eff_preset_mode,
                preset_sha256=eff_preset_sha,
                expected_preset_sha256=eff_expected_sha or None,
                preset_name=eff_preset_name,
                ops2_preflight_pass=eff_ops2_pass,
                preset_params=preset_params,
                ops2_report=ops2_report,
            )
            auto_reasons.extend(lock_reasons)
            if edge == (FleetState.S7_AFTER_PAYOUT_ALLOCATOR, FleetState.S5_FUNDED_ACTIVE):
                auto_reasons.append("FUNDED_NEXT_CYCLE_RESUMED")
            elif edge == (FleetState.E2_FUNDED_DD_FREEZE, FleetState.S5_FUNDED_ACTIVE):
                if eff_traffic == "RED":
                    raise FleetTransitionError(
                        "OPS4_RED_BLOCKS_UNFREEZE",
                        "Cannot unfreeze Funded account back to S5 while ops4_traffic_light == 'RED'.",
                    )
                auto_reasons.append("FUNDED_UNFREEZE_RECLEARED")

        elif edge == (FleetState.S5_FUNDED_ACTIVE, FleetState.S6_PAYOUT_AUDIT_AND_HARVEST):
            if eff_traffic == "RED":
                raise FleetTransitionError(
                    "OPS4_RED_BLOCKS_PAYOUT",
                    "Cannot enter S6 payout audit while ops4_traffic_light == 'RED' (route to E2 freeze).",
                )
            inact_st = compute_inactivity_status(eff_inact_days)
            if inact_st == "EXPIRED":
                raise FleetTransitionError(
                    "INACTIVITY_LIMIT_BREACHED",
                    f"Account inactivity ({eff_inact_days}d >= {INACTIVITY_HARD_LIMIT_DAYS}d) blocks payout harvest.",
                )
            if eff_cycle_days < acct.payout_cycle_cal_days:
                raise FleetTransitionError(
                    "PAYOUT_CYCLE_DAYS_NOT_MET",
                    f"S5->S6 requires cycle_days_elapsed >= {acct.payout_cycle_cal_days}, got {eff_cycle_days}.",
                )
            harvestable_profit = eff_equity - acct.capital_usd
            if harvestable_profit + 1e-9 < acct.min_payout_usd:
                raise FleetTransitionError(
                    "PAYOUT_MIN_PROFIT_NOT_MET",
                    f"S5->S6 requires profit >= {acct.min_payout_usd:.2f} USD, observed {harvestable_profit:.2f} USD.",
                )
            if not _is_valid_sha256_hex(eff_ops5_sha):
                raise FleetTransitionError(
                    "OPS5_AUDIT_BUNDLE_SHA256_REQUIRED",
                    f"S5->S6 requires a valid 64-hex ops5_audit_bundle_sha256, got {eff_ops5_sha!r}.",
                )
            auto_reasons.extend(["PAYOUT_ELIGIBLE", "FLAT_HANDOFF_VERIFIED", "OPS5_WHITEBOX_SHA256_VERIFIED"])

        elif edge == (FleetState.S6_PAYOUT_AUDIT_AND_HARVEST, FleetState.S7_AFTER_PAYOUT_ALLOCATOR):
            if payout_gross_usd is None:
                raise FleetTransitionError(
                    "MISSING_PAYOUT_AMOUNT",
                    "S6->S7 requires explicit payout_gross_usd > 0 for settled-cash 3-bucket allocation.",
                )
            if not _is_valid_sha256_hex(eff_ops5_sha):
                raise FleetTransitionError(
                    "OPS5_AUDIT_BUNDLE_SHA256_REQUIRED",
                    "S6->S7 requires verified ops5_audit_bundle_sha256 from S6 payout audit.",
                )
            cycle_id = f"{acct.account_id}-PAYOUT-{acct.payout_cycles_completed + 1:02d}"
            allocation_result = self._allocate_settled_payout_s7(
                account=acct,
                utc_ts=ts_str,
                payout_gross_usd=payout_gross_usd,
                withdrawal_fee_usd=withdrawal_fee_usd,
                fx_bank_fee_usd=fx_bank_fee_usd,
                fee_refund_usd=fee_refund_usd,
                cycle_id=cycle_id,
            )
            auto_reasons.extend(["PAYOUT_SETTLED", "THREE_BUCKET_ALLOCATED"])
            if fee_refund_usd > 0.0:
                auto_reasons.append("P1_FEE_REFUND_RECORDED")

        elif edge == (FleetState.S7_AFTER_PAYOUT_ALLOCATOR, FleetState.S0_PRE_CHALLENGE):
            auto_reasons.append("POST_PAYOUT_RECYCLE_TO_S0")
        elif target_state == FleetState.E1_EVAL_FAIL_COOLDOWN:
            auto_reasons.append("EVAL_FAILED_COOLDOWN_ENTERED")
        elif target_state == FleetState.E2_FUNDED_DD_FREEZE:
            auto_reasons.append("FUNDED_DD_FREEZE_TRIGGERED")
        elif target_state == FleetState.E3_FUNDED_BREACH_POSTMORTEM:
            auto_reasons.append("FUNDED_BREACH_POSTMORTEM_REQUIRED")
        elif target_state == FleetState.CLOSED_ARCHIVED:
            auto_reasons.append("ACCOUNT_ARCHIVED")
        elif edge == (FleetState.E1_EVAL_FAIL_COOLDOWN, FleetState.S0_PRE_CHALLENGE):
            auto_reasons.append("COOLDOWN_CLEARED_REENTER_S0")

        # 5. Record P1 challenge fee in treasury ledger when S0 -> S1 succeeds
        if edge == (FleetState.S0_PRE_CHALLENGE, FleetState.S1_CHALLENGE_P1) and acct.ticket_fee_usd > 0.0:
            day_str = ts_str[:10]
            self._treasury_events.append(
                TreasuryEvent(
                    date=day_str,
                    event_type="CHALLENGE_FEE",
                    amount_usd=acct.ticket_fee_usd,
                    account_id=acct.account_id,
                    firm=acct.firm_id.upper(),
                    note=f"S0->S1 ticket fee ({acct.contract_id})",
                )
            )
            self._settled_cash_events.append(
                SettledCashEvent(
                    date=day_str,
                    event_type="OUT_OF_POCKET_FEE",
                    amount_usd=acct.ticket_fee_usd,
                    account_id=acct.account_id,
                    firm=acct.firm_id.upper(),
                    settled_date=day_str,
                    note=f"S0->S1 ticket fee ({acct.contract_id})",
                )
            )

        # 6. Commit mutated account state atomically ONLY after ALL guards pass
        acct.state = target_state
        acct.open_positions = validated_open_pos
        acct.ops2_preflight_pass = eff_ops2_pass
        acct.ops4_traffic_light = eff_traffic
        acct.ops5_audit_bundle_sha256 = eff_ops5_sha
        acct.daily_dd_pct = eff_daily_dd
        acct.static_dd_pct = eff_static_dd
        acct.trading_days_completed = eff_trading_days
        acct.cycle_days_elapsed = eff_cycle_days
        acct.days_since_last_trade = eff_inact_days
        acct.best_day_share = eff_best_day
        acct.last_transition_utc = ts_str
        if notes is not None:
            acct.notes = str(notes)
        if cooldown_until_utc is not None:
            acct.cooldown_until_utc = _normalize_utc_ts(cooldown_until_utc)
        elif target_state == FleetState.S0_PRE_CHALLENGE:
            acct.cooldown_until_utc = None

        # Reset phase balance/preset cleanly on phase boundaries
        if target_state in (
            FleetState.S0_PRE_CHALLENGE,
            FleetState.S2_PASS_P1_HANDOFF,
            FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
            FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
            FleetState.E1_EVAL_FAIL_COOLDOWN,
            FleetState.E2_FUNDED_DD_FREEZE,
            FleetState.E3_FUNDED_BREACH_POSTMORTEM,
            FleetState.CLOSED_ARCHIVED,
        ):
            acct.preset_mode = (
                eff_preset_mode
                if target_state == FleetState.S6_PAYOUT_AUDIT_AND_HARVEST
                else PRESET_MODE_NONE
            )
            if target_state == FleetState.S0_PRE_CHALLENGE:
                acct.equity_usd = acct.capital_usd
                acct.balance_usd = acct.capital_usd
                acct.peak_equity_usd = acct.capital_usd
                acct.trading_days_completed = 0
                acct.cycle_days_elapsed = 0
                acct.daily_dd_pct = 0.0
                acct.static_dd_pct = 0.0
                acct.ops2_preflight_pass = False
                acct.preset_sha256 = ""
                acct.expected_preset_sha256 = ""
                acct.preset_name = ""
            elif target_state in (FleetState.S2_PASS_P1_HANDOFF, FleetState.S4_PASS_P2_TO_FUNDED_LOCK):
                acct.equity_usd = eff_equity
                acct.balance_usd = eff_balance
                acct.peak_equity_usd = max(acct.peak_equity_usd, eff_equity)
                acct.ops2_preflight_pass = False
                acct.preset_sha256 = ""
                acct.expected_preset_sha256 = ""
                acct.preset_name = ""
            else:
                acct.equity_usd = eff_equity
                acct.balance_usd = eff_balance
                acct.peak_equity_usd = max(acct.peak_equity_usd, eff_equity)
        else:
            acct.preset_mode = eff_preset_mode
            acct.preset_name = eff_preset_name
            acct.preset_sha256 = eff_preset_sha
            if eff_expected_sha:
                acct.expected_preset_sha256 = eff_expected_sha
            if edge in (
                (FleetState.S2_PASS_P1_HANDOFF, FleetState.S3_CHALLENGE_P2),
                (FleetState.S4_PASS_P2_TO_FUNDED_LOCK, FleetState.S5_FUNDED_ACTIVE),
                (FleetState.S7_AFTER_PAYOUT_ALLOCATOR, FleetState.S5_FUNDED_ACTIVE),
            ):
                acct.equity_usd = eff_equity if equity_usd is not None else acct.capital_usd
                acct.balance_usd = eff_balance if balance_usd is not None else acct.equity_usd
                acct.peak_equity_usd = max(acct.capital_usd, acct.equity_usd)
                if trading_days_completed is None:
                    acct.trading_days_completed = 0
                if cycle_days_elapsed is None:
                    acct.cycle_days_elapsed = 0
            else:
                acct.equity_usd = eff_equity
                acct.balance_usd = eff_balance
                acct.peak_equity_usd = max(acct.peak_equity_usd, eff_equity)

        merged_reasons: list[str] = []
        for code in (*auto_reasons, *(reason_codes or ())):
            c_str = str(code).strip()
            if c_str and c_str not in merged_reasons:
                merged_reasons.append(c_str)

        seq = len(self.transitions) + 1
        prev_sha = self.transitions[-1].event_sha256 if self.transitions else GENESIS_EVENT_SHA256
        event_preset_sha = eff_preset_sha if _is_valid_sha256_hex(eff_preset_sha) else ""
        event_body = {
            "event_id": f"EVT-{seq:06d}",
            "seq": seq,
            "utc_ts": ts_str,
            "account_id": acct.account_id,
            "from_state": from_state.value,
            "to_state": target_state.value,
            "actor": actor.strip(),
            "ops2_preflight_pass": eff_ops2_pass,
            "open_positions": validated_open_pos,
            "preset_mode": eff_preset_mode,
            "preset_sha256": event_preset_sha,
            "reason_codes": merged_reasons,
            "order_send_capable": False,
            "metrics_snapshot": {
                "equity_usd": round(acct.equity_usd, 2),
                "balance_usd": round(acct.balance_usd, 2),
                "daily_dd_pct": round(acct.daily_dd_pct, 4),
                "static_dd_pct": round(acct.static_dd_pct, 4),
                "trading_days_completed": acct.trading_days_completed,
                "cycle_days_elapsed": acct.cycle_days_elapsed,
                "days_since_last_trade": round(acct.days_since_last_trade, 2),
                "inactivity_status": compute_inactivity_status(acct.days_since_last_trade),
                "ops4_traffic_light": acct.ops4_traffic_light,
            },
            "allocation_result": allocation_result,
            "prev_event_sha256": prev_sha,
        }
        ev = TransitionEvent(
            event_id=event_body["event_id"],
            seq=seq,
            utc_ts=ts_str,
            account_id=acct.account_id,
            from_state=from_state.value,
            to_state=target_state.value,
            actor=actor.strip(),
            ops2_preflight_pass=eff_ops2_pass,
            open_positions=validated_open_pos,
            preset_mode=eff_preset_mode,
            preset_sha256=event_preset_sha,
            reason_codes=tuple(merged_reasons),
            order_send_capable=False,
            metrics_snapshot=event_body["metrics_snapshot"],
            allocation_result=allocation_result,
            prev_event_sha256=prev_sha,
            event_sha256=compute_event_sha256(event_body),
        )
        self.transitions.append(ev)
        if ts_str > self.updated_utc:
            self.updated_utc = ts_str
        return ev

    def build_treasury_snapshot(self) -> dict[str, Any]:
        """Compose `treasury_ledger.py` summary + settled-cash summary alongside S7 3-bucket balances."""
        ordered_accounts = [self.accounts[k] for k in sorted(self.accounts.keys())]
        t_ledger = TreasuryLedger(
            pod_name=f"Naqex Prop Fleet ({self.ledger_id})",
            usd_vnd_rate=self.usd_vnd_rate,
            policy=self.allocation_policy.to_treasury_bucket_policy(),
            accounts=[a.to_treasury_account_record() for a in ordered_accounts],
            events=list(self._treasury_events),
        )
        t_summary = t_ledger.compute_summary()
        ref_ticket = (
            max((a.ticket_fee_usd for a in ordered_accounts if a.ticket_fee_usd > 0), default=0.0)
            or self.allocation_policy.reference_ticket_usd
        )
        settled_summary = compute_settled_cash_summary(
            list(self._settled_cash_events),
            required_next_ticket_fee_usd=ref_ticket,
            required_buffer_tickets=2.0,
            usd_vnd_rate=self.usd_vnd_rate,
        )
        return {
            "house_money_usd": round(self._house_money_usd, 2),
            "upgrade_challenge_usd": round(self._upgrade_challenge_usd, 2),
            "own_book_usd": round(self._own_book_usd, 2),
            "house_money_vnd": round(self._house_money_usd * self.usd_vnd_rate, 0),
            "upgrade_challenge_vnd": round(self._upgrade_challenge_usd * self.usd_vnd_rate, 0),
            "own_book_vnd": round(self._own_book_usd * self.usd_vnd_rate, 0),
            "treasury_ledger_summary": t_summary,
            "settled_cash_summary": settled_summary,
        }

    def build_fleet_summary(self, *, treasury_snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Produce morning-briefing & Web-UI ready fleet summary with USD & VND totals."""
        counts: dict[str, int] = {st.value: 0 for st in FleetState}
        active_eval = 0
        active_funded = 0
        frozen_or_breached = 0
        funded_nominal_usd = 0.0
        total_equity_usd = 0.0
        inactivity_alerts: list[dict[str, Any]] = []
        next_actions: list[dict[str, Any]] = []

        for acct_key in sorted(self.accounts.keys()):
            acct = self.accounts[acct_key]
            counts[acct.state.value] += 1
            total_equity_usd += acct.equity_usd
            if acct.state in (FleetState.S1_CHALLENGE_P1, FleetState.S3_CHALLENGE_P2):
                active_eval += 1
            elif acct.state in (
                FleetState.S5_FUNDED_ACTIVE,
                FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
                FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
            ):
                active_funded += 1
                funded_nominal_usd += acct.capital_usd
            elif acct.state in (FleetState.E2_FUNDED_DD_FREEZE, FleetState.E3_FUNDED_BREACH_POSTMORTEM):
                frozen_or_breached += 1

            inact = compute_inactivity_status(acct.days_since_last_trade)
            if acct.state == FleetState.S5_FUNDED_ACTIVE and inact in ("AMBER", "RED", "EXPIRED"):
                inactivity_alerts.append(
                    {
                        "account_id": acct.account_id,
                        "days_since_last_trade": round(acct.days_since_last_trade, 2),
                        "inactivity_status": inact,
                    }
                )

            if acct.state == FleetState.S4_PASS_P2_TO_FUNDED_LOCK:
                next_actions.append(
                    {
                        "account_id": acct.account_id,
                        "state": acct.state.value,
                        "action_code": "RUN_OPS2_AND_ATTACH_FUNDED_1X_PRESET",
                        "label_vi": "Chạy OPS-2 preflight & nạp .set Funded 1.0x (KS 8%) trước khi mở S5",
                    }
                )
            elif acct.state == FleetState.S2_PASS_P1_HANDOFF:
                next_actions.append(
                    {
                        "account_id": acct.account_id,
                        "state": acct.state.value,
                        "action_code": "PREPARE_P2_AND_EVALUATE_GATED_STAGGER",
                        "label_vi": "Chốt log P1, kiểm tra OPS-2 cho P2 và đánh giá mở vé #2 nếu Gated Stagger",
                    }
                )
            elif acct.state == FleetState.S0_PRE_CHALLENGE:
                next_actions.append(
                    {
                        "account_id": acct.account_id,
                        "state": acct.state.value,
                        "action_code": "VERIFY_PREFLIGHT_AND_OPEN_P1",
                        "label_vi": "Kiểm tra cổng tiền kiểm vốn đệm & OPS-2 trước khi mở vé P1",
                    }
                )

        tsnap = treasury_snapshot if treasury_snapshot is not None else self.build_treasury_snapshot()
        settled = tsnap.get("settled_cash_summary") or {}
        fees_spent = float(settled.get("out_of_pocket_paid_usd", 0.0))
        settled_payouts_net = float(settled.get("settled_payouts_net_usd", 0.0))

        return {
            "total_accounts": len(self.accounts),
            "counts_by_state": counts,
            "active_eval_count": active_eval,
            "active_funded_count": active_funded,
            "frozen_or_breached_count": frozen_or_breached,
            "total_funded_nominal_usd": round(funded_nominal_usd, 2),
            "total_funded_nominal_vnd": round(funded_nominal_usd * self.usd_vnd_rate, 0),
            "total_equity_usd": round(total_equity_usd, 2),
            "total_equity_vnd": round(total_equity_usd * self.usd_vnd_rate, 0),
            "total_fees_spent_usd": round(fees_spent, 2),
            "total_settled_payouts_net_usd": round(settled_payouts_net, 2),
            "total_settled_payouts_net_vnd": round(settled_payouts_net * self.usd_vnd_rate, 0),
            "inactivity_alerts": inactivity_alerts,
            "next_actions": next_actions,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete ledger with embedded `report_sha256`."""
        _assert_runtime_safety_invariants()
        treasury_snapshot = self.build_treasury_snapshot()
        fleet_summary = self.build_fleet_summary(treasury_snapshot=treasury_snapshot)
        payload: dict[str, Any] = {
            "schema_version": FLEET_LEDGER_SCHEMA_VERSION,
            "ledger_id": self.ledger_id,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
            "order_send_capable": False,
            "order_send_count": 0,
            "usd_vnd_rate": round(self.usd_vnd_rate, 4),
            "fsm_spec": {
                "canonical_states": [s.value for s in CANONICAL_LIFECYCLE_STATES],
                "incident_terminal_states": [s.value for s in INCIDENT_TERMINAL_STATES],
                "forward_transitions": [[a.value, b.value] for a, b in FORWARD_TRANSITIONS],
                "forward_transition_count": len(FORWARD_TRANSITIONS),
                "state_metadata": STATE_METADATA,
            },
            "allocation_policy": self.allocation_policy.to_dict(),
            "fleet_policy": self.fleet_policy.to_dict(usd_vnd_rate=self.usd_vnd_rate),
            "accounts": [self.accounts[k].to_dict() for k in sorted(self.accounts.keys())],
            "transitions": [ev.to_dict() for ev in self.transitions],
            "treasury_events": [asdict(te) for te in self._treasury_events],
            "settled_cash_events": [asdict(se) for se in self._settled_cash_events],
            "treasury_snapshot": treasury_snapshot,
            "fleet_summary": fleet_summary,
        }
        payload["report_sha256"] = canonical_payload_sha256(payload)
        return payload

    def save(self, path: Path | str) -> dict[str, Any]:
        """Validate & atomically save `fleet_ledger.json` with canonical SHA-256."""
        payload = self.to_dict()
        validate_ledger_dict(payload, verify_sha256=True)
        return write_atomic_sha256_json(path, payload)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], *, verify_sha256: bool = True) -> PropFleetOrchestrator:
        """Deserialize and verify a `fleet_ledger.json` dictionary fail-closed."""
        validate_ledger_dict(raw, verify_sha256=verify_sha256)
        orch = cls(
            ledger_id=str(raw["ledger_id"]),
            usd_vnd_rate=float(raw["usd_vnd_rate"]),
            allocation_policy=AfterPayoutAllocationPolicy.from_dict(raw["allocation_policy"]),
            fleet_policy=FleetPolicy.from_dict(raw["fleet_policy"]),
            created_utc=str(raw["created_utc"]),
        )
        orch.updated_utc = _normalize_utc_ts(str(raw["updated_utc"]))
        for raw_acct in raw["accounts"]:
            acct = FleetAccount.from_dict(raw_acct)
            orch.accounts[acct.account_id] = acct
        for raw_ev in raw["transitions"]:
            ev = TransitionEvent(
                event_id=str(raw_ev["event_id"]),
                seq=int(raw_ev["seq"]),
                utc_ts=str(raw_ev["utc_ts"]),
                account_id=str(raw_ev["account_id"]),
                from_state=str(raw_ev["from_state"]),
                to_state=str(raw_ev["to_state"]),
                actor=str(raw_ev["actor"]),
                ops2_preflight_pass=bool(raw_ev["ops2_preflight_pass"]),
                open_positions=int(raw_ev["open_positions"]),
                preset_mode=str(raw_ev["preset_mode"]),
                preset_sha256=str(raw_ev["preset_sha256"]),
                reason_codes=tuple(str(x) for x in raw_ev["reason_codes"]),
                order_send_capable=False,
                metrics_snapshot=dict(raw_ev.get("metrics_snapshot") or {}),
                allocation_result=(
                    dict(raw_ev["allocation_result"]) if raw_ev.get("allocation_result") is not None else None
                ),
                prev_event_sha256=str(raw_ev["prev_event_sha256"]),
                event_sha256=str(raw_ev["event_sha256"]),
            )
            orch.transitions.append(ev)
        for raw_te in raw.get("treasury_events") or []:
            orch._treasury_events.append(TreasuryEvent(**raw_te))
        for raw_se in raw.get("settled_cash_events") or []:
            orch._settled_cash_events.append(SettledCashEvent(**raw_se))
        tsnap = raw.get("treasury_snapshot") or {}
        orch._house_money_usd = float(tsnap.get("house_money_usd", 0.0))
        orch._upgrade_challenge_usd = float(tsnap.get("upgrade_challenge_usd", 0.0))
        orch._own_book_usd = float(tsnap.get("own_book_usd", 0.0))
        return orch

    @classmethod
    def load(cls, path: Path | str, *, verify_sha256: bool = True) -> PropFleetOrchestrator:
        p = Path(path)
        if not p.is_file():
            raise LedgerValidationError("LEDGER_FILE_NOT_FOUND", f"Fleet ledger not found: {p}")
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise LedgerValidationError("MALFORMED_LEDGER_JSON", f"Expected JSON object in {p}.")
        return cls.from_dict(raw, verify_sha256=verify_sha256)


# ---------------------------------------------------------------------------
# Fail-Closed Ledger Validator (Schema + Hash Chain + FSM Invariants)
# ---------------------------------------------------------------------------
def _scan_for_non_finite(obj: Any, path: str = "$") -> None:
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise LedgerValidationError("NON_FINITE_NUMBER", f"Non-finite float at {path}: {obj!r}")
        return
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            _scan_for_non_finite(v, f"{path}.{k}")
        return
    if isinstance(obj, Sequence):
        for idx, item in enumerate(obj):
            _scan_for_non_finite(item, f"{path}[{idx}]")


def validate_ledger_dict(raw: Mapping[str, Any], *, verify_sha256: bool = True) -> dict[str, Any]:
    """Fail-closed validation of `fleet_ledger.json` schema, invariants, and SHA-256 chain."""
    try:
        _assert_runtime_safety_invariants()
    except FleetTransitionError as exc:
        raise LedgerValidationError(exc.code, str(exc), reason_codes=exc.reason_codes) from exc

    if not isinstance(raw, Mapping):
        raise LedgerValidationError("MALFORMED_LEDGER_JSON", "Ledger payload must be a JSON object.")

    _scan_for_non_finite(raw)

    if raw.get("schema_version") != FLEET_LEDGER_SCHEMA_VERSION:
        raise LedgerValidationError(
            "INVALID_SCHEMA_VERSION",
            f"Expected schema_version='{FLEET_LEDGER_SCHEMA_VERSION}', got {raw.get('schema_version')!r}.",
        )
    if raw.get("order_send_capable") is not False:
        raise LedgerValidationError(
            "ORDER_SEND_CAPABLE_TAMPER",
            f"Ledger order_send_capable must be strictly False, got {raw.get('order_send_capable')!r}.",
        )
    if type(raw.get("order_send_count")) is not int or raw.get("order_send_count") != 0:
        raise LedgerValidationError(
            "ORDER_SEND_COUNT_TAMPER",
            f"Ledger order_send_count must be strictly 0, got {raw.get('order_send_count')!r}.",
        )
    if raw.get("holdout_cutoff_date") != HOLDOUT_CUTOFF_DATE:
        raise LedgerValidationError(
            "HOLDOUT_CUTOFF_DRIFT",
            f"Expected holdout_cutoff_date='{HOLDOUT_CUTOFF_DATE}', got {raw.get('holdout_cutoff_date')!r}.",
        )
    if type(raw.get("holdout_rows_analysed")) is not int or raw.get("holdout_rows_analysed") != 0:
        raise LedgerValidationError(
            "HOLDOUT_SEAL_BREACH",
            f"Expected holdout_rows_analysed == 0, got {raw.get('holdout_rows_analysed')!r}.",
        )

    if verify_sha256:
        declared_sha = raw.get("report_sha256")
        if not _is_valid_sha256_hex(declared_sha):
            raise LedgerValidationError(
                "REPORT_SHA256_MISSING_OR_INVALID",
                f"report_sha256 missing or invalid hex: {declared_sha!r}.",
            )
        actual_sha = canonical_payload_sha256(raw)
        if declared_sha != actual_sha:
            raise LedgerValidationError(
                "REPORT_SHA256_MISMATCH",
                f"Ledger tamper detected: report_sha256 {declared_sha} != recomputed {actual_sha}.",
            )

    try:
        _require_safe_id(raw.get("ledger_id"), field_name="ledger_id")
        _normalize_utc_ts(raw.get("created_utc"))
        _normalize_utc_ts(raw.get("updated_utc"))
        _require_finite_float(raw.get("usd_vnd_rate"), field_name="usd_vnd_rate", strictly_positive=True)
        AfterPayoutAllocationPolicy.from_dict(raw.get("allocation_policy") or {})
        FleetPolicy.from_dict(raw.get("fleet_policy") or {})
    except FleetTransitionError as exc:
        raise LedgerValidationError(exc.code, str(exc), reason_codes=exc.reason_codes) from exc

    raw_accounts = raw.get("accounts")
    raw_transitions = raw.get("transitions")
    if not isinstance(raw_accounts, list):
        raise LedgerValidationError("INVALID_ACCOUNTS_LIST", "accounts must be a list.")
    if not isinstance(raw_transitions, list):
        raise LedgerValidationError("INVALID_TRANSITIONS_LIST", "transitions must be a list.")

    accounts_by_id: dict[str, FleetAccount] = {}
    for idx, item in enumerate(raw_accounts):
        if not isinstance(item, Mapping):
            raise LedgerValidationError("INVALID_ACCOUNT_RECORD", f"accounts[{idx}] must be an object.")
        try:
            acct = FleetAccount.from_dict(item)
        except (FleetTransitionError, KeyError, TypeError, ValueError) as exc:
            code = exc.code if isinstance(exc, FleetTransitionError) else "INVALID_ACCOUNT_RECORD"
            raise LedgerValidationError(code, f"accounts[{idx}] invalid: {exc}") from exc
        if acct.account_id in accounts_by_id:
            raise LedgerValidationError("DUPLICATE_ACCOUNT_ID", f"Duplicate account_id '{acct.account_id}'.")
        if acct.state == FleetState.S5_FUNDED_ACTIVE:
            if acct.preset_mode != PRESET_MODE_FUNDED_1X:
                raise LedgerValidationError(
                    "EVAL_PRESET_FORBIDDEN_ON_FUNDED",
                    f"Funded account '{acct.account_id}' has illegal preset_mode={acct.preset_mode!r}.",
                )
            if acct.ops2_preflight_pass is not True:
                raise LedgerValidationError(
                    "OPS2_PREFLIGHT_NOT_PASSED",
                    f"Funded account '{acct.account_id}' has ops2_preflight_pass != True.",
                )
            if not _is_valid_sha256_hex(acct.preset_sha256):
                raise LedgerValidationError(
                    "PRESET_SHA256_MISSING_OR_INVALID",
                    f"Funded account '{acct.account_id}' missing valid preset_sha256.",
                )
        accounts_by_id[acct.account_id] = acct

    # Replay transitions & verify cryptographic hash chain
    expected_prev_sha = GENESIS_EVENT_SHA256
    replayed_state: dict[str, FleetState] = {}
    for idx, ev in enumerate(raw_transitions):
        if not isinstance(ev, Mapping):
            raise LedgerValidationError("INVALID_TRANSITION_EVENT", f"transitions[{idx}] must be an object.")
        if ev.get("order_send_capable") is not False:
            raise LedgerValidationError(
                "ORDER_SEND_CAPABLE_TAMPER",
                f"transitions[{idx}] order_send_capable must be strictly False, got {ev.get('order_send_capable')!r}.",
            )
        seq = ev.get("seq")
        if type(seq) is not int or seq != idx + 1:
            raise LedgerValidationError(
                "TRANSITION_SEQ_DISCONTINUITY",
                f"transitions[{idx}].seq expected {idx + 1}, got {seq!r}.",
            )
        acct_id = str(ev.get("account_id") or "")
        if acct_id not in accounts_by_id:
            raise LedgerValidationError(
                "UNKNOWN_ACCOUNT_IN_TRANSITION",
                f"transitions[{idx}] references unregistered account '{acct_id}'.",
            )
        try:
            _normalize_utc_ts(ev.get("utc_ts"))
            from_st = _parse_fleet_state(str(ev.get("from_state")))
            to_st = _parse_fleet_state(str(ev.get("to_state")))
            open_pos = _require_strict_non_negative_int(
                ev.get("open_positions"), field_name="open_positions", error_code="INVALID_OPEN_POSITIONS"
            )
            ops2_pass = _require_strict_bool(
                ev.get("ops2_preflight_pass"),
                field_name="ops2_preflight_pass",
                error_code="INVALID_OPS2_PREFLIGHT_FLAG",
            )
        except FleetTransitionError as exc:
            raise LedgerValidationError(exc.code, f"transitions[{idx}] invalid: {exc}") from exc

        if to_st not in ALLOWED_TRANSITIONS.get(from_st, frozenset()):
            raise LedgerValidationError(
                "INVALID_STATE_TRANSITION",
                f"transitions[{idx}] illegal edge {from_st.value} -> {to_st.value}.",
            )
        edge = (from_st, to_st)
        if edge in FLAT_REQUIRED_TRANSITIONS and open_pos != 0:
            raise LedgerValidationError(
                "OPEN_POSITIONS_NONZERO_HANDOFF",
                f"transitions[{idx}] {from_st.value}->{to_st.value} had open_positions={open_pos} (must be 0).",
            )
        if edge in FUNDED_ENTRY_TRANSITIONS:
            pm = str(ev.get("preset_mode") or "")
            psha = str(ev.get("preset_sha256") or "")
            if pm != PRESET_MODE_FUNDED_1X:
                raise LedgerValidationError(
                    "EVAL_PRESET_FORBIDDEN_ON_FUNDED",
                    f"transitions[{idx}] Funded entry had preset_mode={pm!r} != '{PRESET_MODE_FUNDED_1X}'.",
                )
            if ops2_pass is not True:
                raise LedgerValidationError(
                    "OPS2_PREFLIGHT_NOT_PASSED",
                    f"transitions[{idx}] Funded entry had ops2_preflight_pass != True.",
                )
            if not _is_valid_sha256_hex(psha):
                raise LedgerValidationError(
                    "PRESET_SHA256_MISSING_OR_INVALID",
                    f"transitions[{idx}] Funded entry missing valid preset_sha256.",
                )

        if acct_id not in replayed_state:
            if from_st != FleetState.S0_PRE_CHALLENGE:
                raise LedgerValidationError(
                    "ACCOUNT_HISTORY_NOT_ANCHORED_AT_S0",
                    f"First transition for '{acct_id}' started at {from_st.value} instead of S0_PRE_CHALLENGE.",
                )
        elif replayed_state[acct_id] != from_st:
            raise LedgerValidationError(
                "ACCOUNT_STATE_CHAIN_BROKEN",
                f"transitions[{idx}] for '{acct_id}' expected from_state={replayed_state[acct_id].value}, "
                f"got {from_st.value}.",
            )
        replayed_state[acct_id] = to_st

        if ev.get("prev_event_sha256") != expected_prev_sha:
            raise LedgerValidationError(
                "EVENT_HASH_CHAIN_BROKEN",
                f"transitions[{idx}].prev_event_sha256 mismatch.",
            )
        declared_ev_sha = ev.get("event_sha256")
        if not _is_valid_sha256_hex(declared_ev_sha):
            raise LedgerValidationError(
                "EVENT_SHA256_INVALID",
                f"transitions[{idx}].event_sha256 missing or invalid.",
            )
        recomputed_ev_sha = compute_event_sha256(ev)
        if declared_ev_sha != recomputed_ev_sha:
            raise LedgerValidationError(
                "EVENT_SHA256_MISMATCH",
                f"transitions[{idx}] event tamper detected: {declared_ev_sha} != {recomputed_ev_sha}.",
            )
        expected_prev_sha = declared_ev_sha

    # Verify final account states match replayed transition history
    for acct_id, acct in accounts_by_id.items():
        expected_state = replayed_state.get(acct_id, FleetState.S0_PRE_CHALLENGE)
        if acct.state != expected_state:
            raise LedgerValidationError(
                "ACCOUNT_STATE_DESYNC",
                f"Account '{acct_id}' state is {acct.state.value} but log replays to {expected_state.value}.",
            )

    return {
        "valid": True,
        "schema_version": FLEET_LEDGER_SCHEMA_VERSION,
        "ledger_id": str(raw["ledger_id"]),
        "accounts_count": len(accounts_by_id),
        "transitions_count": len(raw_transitions),
        "report_sha256": raw.get("report_sha256"),
        "order_send_capable": False,
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
    }


def validate_ledger_file(path: Path | str, *, verify_sha256: bool = True) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise LedgerValidationError("LEDGER_FILE_NOT_FOUND", f"Fleet ledger not found: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise LedgerValidationError("MALFORMED_LEDGER_JSON", f"Expected JSON object in {p}.")
    report = validate_ledger_dict(raw, verify_sha256=verify_sha256)
    report["path"] = str(p)
    return report


# ---------------------------------------------------------------------------
# Deterministic Sample Fixture Builder (for UI Contract, Web UI & Guard Lanes)
# ---------------------------------------------------------------------------
def _synthetic_sha256(label: str) -> str:
    return hashlib.sha256(f"NAQEX_WAVE4_SAMPLE_FIXTURE|{label}".encode()).hexdigest()


def build_sample_fleet_orchestrator(
    *,
    catalog_path: Path | str | None = None,
    fx_path: Path | str | None = None,
) -> PropFleetOrchestrator:
    """Build a verified multi-account sample fleet fixture covering S0..S7 lifecycle & Gated Stagger."""
    contracts = load_firms_catalog(catalog_path)
    usd_vnd = load_usd_vnd_rate(fx_path)

    orch = PropFleetOrchestrator(
        ledger_id="naqex-prop-fleet-sample-v1",
        usd_vnd_rate=usd_vnd,
        allocation_policy=AfterPayoutAllocationPolicy(
            policy_name="PARETO_3_BUCKET_DEFAULT",
            house_money_pct=0.30,
            upgrade_challenge_pct=0.30,
            own_book_pct=0.40,
            reserve_cap_tickets=5.0,
            reference_ticket_usd=109.69,
        ),
        fleet_policy=FleetPolicy(
            concurrency_mode="GATED_STAGGER",
            max_concurrent_evals=2,
            max_concurrent_funded=4,
            max_accounts_per_firm=3,
            bankroll_budget_usd=600.0,
        ),
        created_utc="2026-10-01T08:00:00Z",
    )

    sha_p1_std10k = _synthetic_sha256("FTMO_Std10K_P1_Sprint_4_5x.set")
    sha_p2_std10k = _synthetic_sha256("FTMO_Std10K_P2_Sprint_3_5x.set")
    sha_funded_std10k = _synthetic_sha256("FTMO_Std10K_Funded_Safe_1x.set")
    sha_ops5_cycle1 = _synthetic_sha256("OPS5_WHITEBOX_BUNDLE_FTMO_STD10K_001_C1")

    sha_p1_swing10k = _synthetic_sha256("FTMO_Swing10K_P1_Sprint_4_5x.set")
    sha_p2_swing10k = _synthetic_sha256("FTMO_Swing10K_P2_Sprint_3_5x.set")

    sha_p1_5ers5k = _synthetic_sha256("The5ers_HS5K_P1_Sprint_4_5x.set")

    # Account 1: Full lifecycle S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S7 -> S5 (Funded Cycle 2)
    orch.register_from_catalog(
        account_id="FTMO-STD10K-001",
        contract_id="ftmo_standard_10k",
        contracts=contracts,
        use_promo_fee=True,
        opened_utc="2026-10-01T08:00:00Z",
        notes="Ticket #1 anchor (Black Friday VN checkout reference).",
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S1_CHALLENGE_P1,
        actor="operator",
        utc_ts="2026-10-01T08:15:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=PRESET_MODE_EVAL_P1_SPRINT,
        preset_name="FTMO_Std10K_P1_Sprint_4_5x.set",
        preset_sha256=sha_p1_std10k,
        expected_preset_sha256=sha_p1_std10k,
        equity_usd=10000.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S2_PASS_P1_HANDOFF,
        actor="ops-monitor",
        utc_ts="2026-10-14T16:30:00Z",
        open_positions=0,
        equity_usd=11042.50,
        daily_dd_pct=1.15,
        static_dd_pct=2.10,
        trading_days_completed=6,
        best_day_share=0.31,
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S3_CHALLENGE_P2,
        actor="operator",
        utc_ts="2026-10-15T07:45:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=PRESET_MODE_EVAL_P2_SPRINT,
        preset_name="FTMO_Std10K_P2_Sprint_3_5x.set",
        preset_sha256=sha_p2_std10k,
        expected_preset_sha256=sha_p2_std10k,
        equity_usd=10000.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        actor="ops-monitor",
        utc_ts="2026-10-26T17:00:00Z",
        open_positions=0,
        equity_usd=10528.00,
        daily_dd_pct=0.90,
        static_dd_pct=1.40,
        trading_days_completed=5,
        best_day_share=0.34,
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S5_FUNDED_ACTIVE,
        actor="operator",
        utc_ts="2026-10-28T07:30:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
        preset_sha256=sha_funded_std10k,
        expected_preset_sha256=sha_funded_std10k,
        preset_params={
            "phase": "FUNDED",
            "InpBasePhaseMult": 1.0,
            "InpProfitLockMult": 1.0,
            "InpAmberDdPct": 3.5,
            "InpRedDdPct": 6.0,
            "InpKillDailyDdPct": 2.5,
            "InpKillStaticDdPct": 8.0,
            "InpTargetProfitPct": 0.0,
        },
        ops4_traffic_light="GREEN",
        equity_usd=10000.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S6_PAYOUT_AUDIT_AND_HARVEST,
        actor="ops5-packager",
        utc_ts="2026-11-12T17:15:00Z",
        open_positions=0,
        ops4_traffic_light="GREEN",
        ops5_audit_bundle_sha256=sha_ops5_cycle1,
        equity_usd=10620.00,
        daily_dd_pct=0.40,
        static_dd_pct=0.80,
        trading_days_completed=9,
        cycle_days_elapsed=15,
        days_since_last_trade=1.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S7_AFTER_PAYOUT_ALLOCATOR,
        actor="treasury-allocator",
        utc_ts="2026-11-15T10:00:00Z",
        open_positions=0,
        payout_gross_usd=620.00,
        withdrawal_fee_usd=7.44,
        fx_bank_fee_usd=2.48,
        fee_refund_usd=68.70,
        equity_usd=10000.0,
    )
    orch.transition(
        account_id="FTMO-STD10K-001",
        to_state=FleetState.S5_FUNDED_ACTIVE,
        actor="operator",
        utc_ts="2026-11-16T07:30:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=PRESET_MODE_FUNDED_1X,
        preset_name="FTMO_Std10K_Funded_Safe_1x.set",
        preset_sha256=sha_funded_std10k,
        expected_preset_sha256=sha_funded_std10k,
        ops4_traffic_light="GREEN",
        equity_usd=10245.00,
        cycle_days_elapsed=11,
        trading_days_completed=7,
        days_since_last_trade=2.0,
        notes="Funded Cycle #2 running smoothly at 1.0x Safe.",
    )

    # Account 2: Gated Stagger Ticket #2 spawned after Account 1 passed P1 — now awaiting Funded 1.0x lock (S4)
    orch.register_from_catalog(
        account_id="FTMO-SWING10K-002",
        contract_id="ftmo_swing_10k",
        contracts=contracts,
        use_promo_fee=True,
        parent_account_id="FTMO-STD10K-001",
        opened_utc="2026-10-16T08:00:00Z",
        notes="Gated Stagger ticket #2 opened after FTMO-STD10K-001 passed P1.",
    )
    orch.transition(
        account_id="FTMO-SWING10K-002",
        to_state=FleetState.S1_CHALLENGE_P1,
        actor="operator",
        utc_ts="2026-10-16T08:10:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=PRESET_MODE_EVAL_P1_SPRINT,
        preset_name="FTMO_Swing10K_P1_Sprint_4_5x.set",
        preset_sha256=sha_p1_swing10k,
        expected_preset_sha256=sha_p1_swing10k,
        equity_usd=10000.0,
    )
    orch.transition(
        account_id="FTMO-SWING10K-002",
        to_state=FleetState.S2_PASS_P1_HANDOFF,
        actor="ops-monitor",
        utc_ts="2026-11-04T16:40:00Z",
        open_positions=0,
        equity_usd=11018.00,
        trading_days_completed=7,
        best_day_share=0.29,
    )
    orch.transition(
        account_id="FTMO-SWING10K-002",
        to_state=FleetState.S3_CHALLENGE_P2,
        actor="operator",
        utc_ts="2026-11-05T07:45:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=PRESET_MODE_EVAL_P2_SPRINT,
        preset_name="FTMO_Swing10K_P2_Sprint_3_5x.set",
        preset_sha256=sha_p2_swing10k,
        expected_preset_sha256=sha_p2_swing10k,
        equity_usd=10000.0,
    )
    orch.transition(
        account_id="FTMO-SWING10K-002",
        to_state=FleetState.S4_PASS_P2_TO_FUNDED_LOCK,
        actor="ops-monitor",
        utc_ts="2026-11-25T16:50:00Z",
        open_positions=0,
        equity_usd=10515.00,
        trading_days_completed=5,
        best_day_share=0.33,
        notes="Awaiting operator OPS-2 preflight + Funded 1.0x preset lock.",
    )

    # Account 3: Diversified second-firm Eval active in P1 (S1)
    orch.register_from_catalog(
        account_id="THE5ERS-HS5K-003",
        contract_id="the5ers_hs_5k_classic",
        contracts=contracts,
        use_promo_fee=True,
        parent_account_id="FTMO-STD10K-001",
        opened_utc="2026-11-18T08:00:00Z",
        notes="Second-firm diversification ticket funded from S7 upgrade bucket.",
    )
    orch.transition(
        account_id="THE5ERS-HS5K-003",
        to_state=FleetState.S1_CHALLENGE_P1,
        actor="operator",
        utc_ts="2026-11-18T08:15:00Z",
        open_positions=0,
        ops2_preflight_pass=True,
        preset_mode=PRESET_MODE_EVAL_P1_SPRINT,
        preset_name="The5ers_HS5K_P1_Sprint_4_5x.set",
        preset_sha256=sha_p1_5ers5k,
        expected_preset_sha256=sha_p1_5ers5k,
        equity_usd=5185.00,
        trading_days_completed=2,
        days_since_last_trade=1.0,
    )

    # Account 4: Queued upgrade ticket sitting at S0_PRE_CHALLENGE
    orch.register_from_catalog(
        account_id="FTMO-STD25K-004",
        contract_id="ftmo_standard_25k",
        contracts=contracts,
        use_promo_fee=True,
        parent_account_id="FTMO-STD10K-001",
        opened_utc="2026-11-27T08:00:00Z",
        notes="Queued 25K upgrade ticket pending next S7 reserve fill & OPS-2 gate.",
    )

    return orch


def emit_sample_fixture(
    output_path: Path | str = DEFAULT_SAMPLE_FIXTURE_PATH,
    *,
    catalog_path: Path | str | None = None,
    fx_path: Path | str | None = None,
) -> dict[str, Any]:
    """Generate, verify, and atomically write `sample_fleet_ledger.json`."""
    orch = build_sample_fleet_orchestrator(catalog_path=catalog_path, fx_path=fx_path)
    write_info = orch.save(output_path)
    validation = validate_ledger_file(output_path, verify_sha256=True)
    return {
        "schema_version": FLEET_LEDGER_SCHEMA_VERSION,
        "output_path": str(Path(output_path)),
        "report_sha256": write_info["report_sha256"],
        "file_sha256": write_info["file_sha256"],
        "bytes": write_info["bytes"],
        "validation": validation,
        "fleet_summary": orch.build_fleet_summary(),
    }


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Naqex Canonical Prop Fleet Lifecycle State Machine (S0..S7) & Audit-Trail Ledger CLI "
            "(ORDER_SEND_CAPABLE=False, Holdout 2025+ SEALED)."
        )
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Validate ledger (or --ledger path) and print JSON fleet status summary.",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_SAMPLE_FIXTURE_PATH,
        help="Path to fleet_ledger.json (used with --status).",
    )
    parser.add_argument(
        "--validate-ledger",
        type=Path,
        default=None,
        help="Validate an existing fleet_ledger.json fail-closed (exit 0 on PASS, 2 on FAIL).",
    )
    parser.add_argument(
        "--emit-sample-fixture",
        nargs="?",
        const=str(DEFAULT_SAMPLE_FIXTURE_PATH),
        default=None,
        help="Emit and verify sample_fleet_ledger.json (default: .runtime/offensive4/fleet/sample_fleet_ledger.json).",
    )
    args = parser.parse_args(argv)

    if args.emit_sample_fixture is not None:
        res = emit_sample_fixture(Path(args.emit_sample_fixture))
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    if args.validate_ledger is not None:
        try:
            res = validate_ledger_file(args.validate_ledger, verify_sha256=True)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0
        except LedgerValidationError as exc:
            err = {
                "valid": False,
                "error_code": exc.code,
                "reason_codes": list(exc.reason_codes),
                "message": str(exc),
                "order_send_capable": False,
            }
            print(json.dumps(err, indent=2, ensure_ascii=False))
            return 2

    if args.status:
        try:
            orch = PropFleetOrchestrator.load(args.ledger, verify_sha256=True)
        except LedgerValidationError as exc:
            err = {
                "valid": False,
                "error_code": exc.code,
                "reason_codes": list(exc.reason_codes),
                "message": str(exc),
                "order_send_capable": False,
            }
            print(json.dumps(err, indent=2, ensure_ascii=False))
            return 2
        payload = {
            "schema_version": FLEET_LEDGER_SCHEMA_VERSION,
            "ledger_id": orch.ledger_id,
            "updated_utc": orch.updated_utc,
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "fleet_summary": orch.build_fleet_summary(),
            "treasury_snapshot": orch.build_treasury_snapshot(),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 0


__all__ = [
    "ALLOWED_TRANSITIONS",
    "CANONICAL_LIFECYCLE_STATES",
    "DEFAULT_FIRMS_CATALOG_PATH",
    "DEFAULT_FX_RATES_PATH",
    "DEFAULT_SAMPLE_FIXTURE_PATH",
    "FLAT_REQUIRED_TRANSITIONS",
    "FLEET_LEDGER_SCHEMA_VERSION",
    "FORWARD_TRANSITIONS",
    "FUNDED_ENTRY_TRANSITIONS",
    "GENESIS_EVENT_SHA256",
    "HOLDOUT_CUTOFF_DATE",
    "HOLDOUT_ROWS_ANALYSED",
    "INCIDENT_TERMINAL_STATES",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRESET_MODE_EVAL_P1_SPRINT",
    "PRESET_MODE_EVAL_P2_SPRINT",
    "PRESET_MODE_FUNDED_1X",
    "PRESET_MODE_NONE",
    "STATE_METADATA",
    "VALID_CONCURRENCY_MODES",
    "VALID_EVAL_P1_PRESET_MODES",
    "VALID_EVAL_P2_PRESET_MODES",
    "VALID_PRESET_MODES",
    "VALID_TRAFFIC_LIGHTS",
    "AfterPayoutAllocationPolicy",
    "FleetAccount",
    "FleetLifecycleError",
    "FleetPolicy",
    "FleetState",
    "FleetTransitionError",
    "LedgerValidationError",
    "PropFleetOrchestrator",
    "TransitionEvent",
    "build_sample_fleet_orchestrator",
    "compute_event_sha256",
    "compute_inactivity_status",
    "emit_sample_fixture",
    "load_firms_catalog",
    "load_usd_vnd_rate",
    "main",
    "resolve_tracker_profile_spec",
    "validate_ledger_dict",
    "validate_ledger_file",
]


if __name__ == "__main__":
    raise SystemExit(main())
