"""Lauren Tan (`@poteto`) 5-Pillar Metric Ratchet & Hard 3-Attempt Circuit Breaker.

Design invariants (100% enforced under `python -O`, ZERO bare `assert` statements):
  1. `ORDER_SEND_COUNT = 0`, `HOLDOUT_ROWS_ANALYSED = 0` (offline verification only).
  2. Monotonic Ratchet: tracks baseline metric floors (`tests_passed` never drops)
     and ceilings (`tests_failed`, `ruff_errors`, `ty_errors`, `arch_errors`,
     `arch_warnings` never rise; `opsec_leaks`, `holdout_rows_analysed`, and
     `order_send_count` MUST remain `0`). Regressions fail closed without
     weakening the stored baseline.
  3. Strict Circuit Breaker (`max_attempts = 3`):
     - Attempts 1..3 failing keep state `CLOSED` while decrementing retries.
     - Attempt #4 (4th consecutive failure, or pre-flight guard after 3 failures)
       trips HARD into `CIRCUIT_OPEN_ESCALATE_OWNER` — zero infinite retry loops!
     - Once open, autonomous `record_success()` raises `CircuitOpenError`;
       only an explicit owner `reset_circuit(target_id, owner_reason=...)` closes it.
  4. Atomic state persistence via temp + flush + fsync + `os.replace`, with
     OPSEC secret scrubbing on persisted reasons/details.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tooling.automation.event_queue import (  # noqa: E402
    DEFAULT_EVENT_QUEUE_PATH,
    EventQueue,
    _atomic_write_text,
    _queue_lock,
    scrub_mapping,
    scrub_text,
    utc_now_iso,
)

DEFAULT_RATCHET_STATE_PATH = REPO_ROOT / ".runtime" / "automation" / "ratchet_state.json"
RATCHET_STATE_SCHEMA = "naqex-poteto-ratchet-state-v1"

ORDER_SEND_COUNT = 0
HOLDOUT_ROWS_ANALYSED = 0
DEFAULT_MAX_ATTEMPTS = 3

STATE_CLOSED = "CLOSED"
CIRCUIT_OPEN_ESCALATE_OWNER = "CIRCUIT_OPEN_ESCALATE_OWNER"


class CircuitOpenError(RuntimeError):
    """Fail-closed exception raised when a target's circuit breaker is open."""

    def __init__(self, target_id: str, consecutive_failures: int, reason: str) -> None:
        self.target_id = target_id
        self.consecutive_failures = consecutive_failures
        self.state = CIRCUIT_OPEN_ESCALATE_OWNER
        super().__init__(
            f"{CIRCUIT_OPEN_ESCALATE_OWNER} [{target_id}]: "
            f"consecutive_failures={consecutive_failures}; last_reason={reason}"
        )


def _require_non_neg_int(name: str, val: Any) -> int:
    if isinstance(val, bool) or not isinstance(val, int) or val < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {val!r}")
    return val


def _require_finite_number(name: str, val: Any) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"{name} must be a finite number, got {val!r}")
    fv = float(val)
    if not math.isfinite(fv):
        raise ValueError(f"{name} must be finite (no NaN/Inf), got {val!r}")
    return fv


def _validate_extra_metrics(name: str, mapping: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(mapping, Mapping):
        raise ValueError(f"{name} must be a mapping, got {type(mapping).__name__}")
    out: dict[str, float] = {}
    for k, v in mapping.items():
        if not isinstance(k, str) or not k.strip():
            raise ValueError(f"{name} contains invalid metric key: {k!r}")
        out[k.strip()] = _require_finite_number(f"{name}.{k}", v)
    return out


@dataclass(frozen=True)
class MetricSnapshot:
    """Observed verification metrics evaluated against a monotonic ratchet baseline."""

    tests_passed: int
    tests_failed: int = 0
    ruff_errors: int = 0
    ty_errors: int = 0
    arch_errors: int = 0
    arch_warnings: int = 0
    opsec_leaks: int = 0
    holdout_rows_analysed: int = 0
    order_send_count: int = 0
    extra_floors: dict[str, float] = field(default_factory=dict)
    extra_ceilings: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_neg_int("tests_passed", self.tests_passed)
        _require_non_neg_int("tests_failed", self.tests_failed)
        _require_non_neg_int("ruff_errors", self.ruff_errors)
        _require_non_neg_int("ty_errors", self.ty_errors)
        _require_non_neg_int("arch_errors", self.arch_errors)
        _require_non_neg_int("arch_warnings", self.arch_warnings)
        _require_non_neg_int("opsec_leaks", self.opsec_leaks)
        _require_non_neg_int("holdout_rows_analysed", self.holdout_rows_analysed)
        _require_non_neg_int("order_send_count", self.order_send_count)
        _validate_extra_metrics("extra_floors", self.extra_floors)
        _validate_extra_metrics("extra_ceilings", self.extra_ceilings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MetricSnapshot:
        if not isinstance(data, Mapping):
            raise ValueError("MetricSnapshot data must be a mapping")
        return cls(
            tests_passed=data.get("tests_passed", 0),  # type: ignore[arg-type]
            tests_failed=data.get("tests_failed", 0),  # type: ignore[arg-type]
            ruff_errors=data.get("ruff_errors", 0),  # type: ignore[arg-type]
            ty_errors=data.get("ty_errors", 0),  # type: ignore[arg-type]
            arch_errors=data.get("arch_errors", 0),  # type: ignore[arg-type]
            arch_warnings=data.get("arch_warnings", 0),  # type: ignore[arg-type]
            opsec_leaks=data.get("opsec_leaks", 0),  # type: ignore[arg-type]
            holdout_rows_analysed=data.get("holdout_rows_analysed", 0),  # type: ignore[arg-type]
            order_send_count=data.get("order_send_count", 0),  # type: ignore[arg-type]
            extra_floors=dict(data.get("extra_floors", {})),
            extra_ceilings=dict(data.get("extra_ceilings", {})),
        )


@dataclass(frozen=True)
class RatchetBaseline:
    """Monotonic metric floor/ceiling ledger that only tightens on green runs."""

    min_tests_passed: int = 0
    max_tests_failed: int = 0
    max_ruff_errors: int = 0
    max_ty_errors: int = 0
    max_arch_errors: int = 0
    max_arch_warnings: int = 0
    extra_floors: dict[str, float] = field(default_factory=dict)
    extra_ceilings: dict[str, float] = field(default_factory=dict)
    updated_utc: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        _require_non_neg_int("min_tests_passed", self.min_tests_passed)
        _require_non_neg_int("max_tests_failed", self.max_tests_failed)
        _require_non_neg_int("max_ruff_errors", self.max_ruff_errors)
        _require_non_neg_int("max_ty_errors", self.max_ty_errors)
        _require_non_neg_int("max_arch_errors", self.max_arch_errors)
        _require_non_neg_int("max_arch_warnings", self.max_arch_warnings)
        _validate_extra_metrics("extra_floors", self.extra_floors)
        _validate_extra_metrics("extra_ceilings", self.extra_ceilings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, snapshot: MetricSnapshot, *, ts_utc: str | None = None) -> RatchetBaseline:
        return cls(
            min_tests_passed=snapshot.tests_passed,
            max_tests_failed=snapshot.tests_failed,
            max_ruff_errors=snapshot.ruff_errors,
            max_ty_errors=snapshot.ty_errors,
            max_arch_errors=snapshot.arch_errors,
            max_arch_warnings=snapshot.arch_warnings,
            extra_floors=dict(snapshot.extra_floors),
            extra_ceilings=dict(snapshot.extra_ceilings),
            updated_utc=ts_utc or utc_now_iso(),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RatchetBaseline:
        if not isinstance(data, Mapping):
            raise ValueError("RatchetBaseline data must be a mapping")
        return cls(
            min_tests_passed=data.get("min_tests_passed", 0),  # type: ignore[arg-type]
            max_tests_failed=data.get("max_tests_failed", 0),  # type: ignore[arg-type]
            max_ruff_errors=data.get("max_ruff_errors", 0),  # type: ignore[arg-type]
            max_ty_errors=data.get("max_ty_errors", 0),  # type: ignore[arg-type]
            max_arch_errors=data.get("max_arch_errors", 0),  # type: ignore[arg-type]
            max_arch_warnings=data.get("max_arch_warnings", 0),  # type: ignore[arg-type]
            extra_floors=dict(data.get("extra_floors", {})),
            extra_ceilings=dict(data.get("extra_ceilings", {})),
            updated_utc=str(data.get("updated_utc") or utc_now_iso()),
        )


@dataclass(frozen=True)
class RatchetVerdict:
    """Result of comparing an observed `MetricSnapshot` against `RatchetBaseline`."""

    passed: bool
    regressions: tuple[dict[str, Any], ...]
    improvements: tuple[dict[str, Any], ...]
    next_baseline: RatchetBaseline
    order_send_count: int = ORDER_SEND_COUNT
    holdout_rows_analysed: int = HOLDOUT_ROWS_ANALYSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "regressions": list(self.regressions),
            "improvements": list(self.improvements),
            "next_baseline": self.next_baseline.to_dict(),
            "order_send_count": self.order_send_count,
            "holdout_rows_analysed": self.holdout_rows_analysed,
        }


def evaluate_ratchet(
    baseline: RatchetBaseline,
    observed: MetricSnapshot,
    *,
    ts_utc: str | None = None,
) -> RatchetVerdict:
    """Evaluate `observed` against `baseline`; tighten monotonically only when passing."""
    if not isinstance(baseline, RatchetBaseline):
        raise ValueError(f"baseline must be RatchetBaseline, got {type(baseline).__name__}")
    if not isinstance(observed, MetricSnapshot):
        raise ValueError(f"observed must be MetricSnapshot, got {type(observed).__name__}")

    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []

    # Hard zero invariants that can NEVER be relaxed.
    for invariant_name, val in (
        ("opsec_leaks", observed.opsec_leaks),
        ("holdout_rows_analysed", observed.holdout_rows_analysed),
        ("order_send_count", observed.order_send_count),
    ):
        if val != 0:
            regressions.append(
                {
                    "metric": invariant_name,
                    "direction": "hard_zero",
                    "baseline": 0,
                    "observed": val,
                    "delta": val,
                }
            )

    # Higher-is-better floor: tests_passed
    if observed.tests_passed < baseline.min_tests_passed:
        regressions.append(
            {
                "metric": "tests_passed",
                "direction": "min_floor",
                "baseline": baseline.min_tests_passed,
                "observed": observed.tests_passed,
                "delta": observed.tests_passed - baseline.min_tests_passed,
            }
        )
    elif observed.tests_passed > baseline.min_tests_passed:
        improvements.append(
            {
                "metric": "tests_passed",
                "direction": "min_floor",
                "baseline": baseline.min_tests_passed,
                "observed": observed.tests_passed,
                "delta": observed.tests_passed - baseline.min_tests_passed,
            }
        )

    # Lower-is-better ceilings
    ceiling_pairs = (
        ("tests_failed", baseline.max_tests_failed, observed.tests_failed),
        ("ruff_errors", baseline.max_ruff_errors, observed.ruff_errors),
        ("ty_errors", baseline.max_ty_errors, observed.ty_errors),
        ("arch_errors", baseline.max_arch_errors, observed.arch_errors),
        ("arch_warnings", baseline.max_arch_warnings, observed.arch_warnings),
    )
    for metric_name, max_allowed, cur_val in ceiling_pairs:
        if cur_val > max_allowed:
            regressions.append(
                {
                    "metric": metric_name,
                    "direction": "max_ceiling",
                    "baseline": max_allowed,
                    "observed": cur_val,
                    "delta": cur_val - max_allowed,
                }
            )
        elif cur_val < max_allowed:
            improvements.append(
                {
                    "metric": metric_name,
                    "direction": "max_ceiling",
                    "baseline": max_allowed,
                    "observed": cur_val,
                    "delta": cur_val - max_allowed,
                }
            )

    # Extra floors (higher is better)
    next_extra_floors = dict(baseline.extra_floors)
    for key, floor_val in baseline.extra_floors.items():
        if key not in observed.extra_floors:
            regressions.append(
                {
                    "metric": f"extra_floors.{key}",
                    "direction": "min_floor",
                    "baseline": floor_val,
                    "observed": None,
                    "delta": None,
                }
            )
            continue
        cur_f = observed.extra_floors[key]
        if cur_f < floor_val:
            regressions.append(
                {
                    "metric": f"extra_floors.{key}",
                    "direction": "min_floor",
                    "baseline": floor_val,
                    "observed": cur_f,
                    "delta": cur_f - floor_val,
                }
            )
        elif cur_f > floor_val:
            improvements.append(
                {
                    "metric": f"extra_floors.{key}",
                    "direction": "min_floor",
                    "baseline": floor_val,
                    "observed": cur_f,
                    "delta": cur_f - floor_val,
                }
            )
            next_extra_floors[key] = cur_f
    for key, cur_f in observed.extra_floors.items():
        if key not in next_extra_floors:
            next_extra_floors[key] = cur_f

    # Extra ceilings (lower is better)
    next_extra_ceilings = dict(baseline.extra_ceilings)
    for key, ceil_val in baseline.extra_ceilings.items():
        if key not in observed.extra_ceilings:
            regressions.append(
                {
                    "metric": f"extra_ceilings.{key}",
                    "direction": "max_ceiling",
                    "baseline": ceil_val,
                    "observed": None,
                    "delta": None,
                }
            )
            continue
        cur_c = observed.extra_ceilings[key]
        if cur_c > ceil_val:
            regressions.append(
                {
                    "metric": f"extra_ceilings.{key}",
                    "direction": "max_ceiling",
                    "baseline": ceil_val,
                    "observed": cur_c,
                    "delta": cur_c - ceil_val,
                }
            )
        elif cur_c < ceil_val:
            improvements.append(
                {
                    "metric": f"extra_ceilings.{key}",
                    "direction": "max_ceiling",
                    "baseline": ceil_val,
                    "observed": cur_c,
                    "delta": cur_c - ceil_val,
                }
            )
            next_extra_ceilings[key] = cur_c
    for key, cur_c in observed.extra_ceilings.items():
        if key not in next_extra_ceilings:
            next_extra_ceilings[key] = cur_c

    passed = len(regressions) == 0
    if passed:
        next_baseline = RatchetBaseline(
            min_tests_passed=max(baseline.min_tests_passed, observed.tests_passed),
            max_tests_failed=min(baseline.max_tests_failed, observed.tests_failed),
            max_ruff_errors=min(baseline.max_ruff_errors, observed.ruff_errors),
            max_ty_errors=min(baseline.max_ty_errors, observed.ty_errors),
            max_arch_errors=min(baseline.max_arch_errors, observed.arch_errors),
            max_arch_warnings=min(baseline.max_arch_warnings, observed.arch_warnings),
            extra_floors=next_extra_floors,
            extra_ceilings=next_extra_ceilings,
            updated_utc=ts_utc or utc_now_iso(),
        )
    else:
        # Never weaken baseline on failure.
        next_baseline = baseline

    return RatchetVerdict(
        passed=passed,
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        next_baseline=next_baseline,
        order_send_count=ORDER_SEND_COUNT,
        holdout_rows_analysed=HOLDOUT_ROWS_ANALYSED,
    )


@dataclass
class CircuitTargetState:
    """Per-target state tracked by the hard 3-attempt Circuit Breaker."""

    target_id: str
    state: str = STATE_CLOSED
    consecutive_failures: int = 0
    total_failures: int = 0
    total_successes: int = 0
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    last_failure_reason: str = ""
    last_failure_utc: str = ""
    opened_utc: str = ""
    last_reset_reason: str = ""
    last_reset_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CircuitTargetState:
        return cls(
            target_id=str(data.get("target_id", "")),
            state=str(data.get("state", STATE_CLOSED)),
            consecutive_failures=int(data.get("consecutive_failures", 0)),
            total_failures=int(data.get("total_failures", 0)),
            total_successes=int(data.get("total_successes", 0)),
            max_attempts=int(data.get("max_attempts", DEFAULT_MAX_ATTEMPTS)),
            last_failure_reason=str(data.get("last_failure_reason", "")),
            last_failure_utc=str(data.get("last_failure_utc", "")),
            opened_utc=str(data.get("opened_utc", "")),
            last_reset_reason=str(data.get("last_reset_reason", "")),
            last_reset_utc=str(data.get("last_reset_utc", "")),
        )


@dataclass(frozen=True)
class CircuitDecision:
    """Decision returned by the Circuit Breaker on failure or pre-flight check."""

    target_id: str
    state: str
    attempt_number: int
    max_attempts: int
    consecutive_failures: int
    retries_remaining: int
    allowed: bool
    tripped: bool
    escalate_owner: bool
    reason: str
    order_send_count: int = ORDER_SEND_COUNT

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CircuitBreaker:
    """Strict 3-attempt Circuit Breaker tripping HARD on attempt #4.

    Rules:
      - `max_attempts` defaults to `3` (must be an int >= 1).
      - Consecutive failures 1..`max_attempts` stay `CLOSED` (`tripped = False`).
      - Consecutive failure `#4` (`consecutive_failures > max_attempts`) trips HARD
        into `CIRCUIT_OPEN_ESCALATE_OWNER` (`tripped = True`, `escalate_owner = True`,
        `allowed = False`) and stays open until explicit owner `reset_circuit(...)`.
      - Pre-flight `guard_attempt(target_id)` ALSO trips HARD when called for
        attempt #4 (`consecutive_failures >= max_attempts`), preventing infinite
        retry loops before a 4th broken attempt even runs.
    """

    def __init__(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        targets: Mapping[str, CircuitTargetState] | None = None,
        event_queue: EventQueue | None = None,
    ) -> None:
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError(f"max_attempts must be an integer >= 1, got {max_attempts!r}")
        self.max_attempts = max_attempts
        self._targets: dict[str, CircuitTargetState] = {}
        if targets is not None:
            for tid, st in targets.items():
                self._targets[str(tid)] = st
        self._event_queue = event_queue

    def _validate_target_id(self, target_id: str) -> str:
        if not isinstance(target_id, str) or not target_id.strip():
            raise ValueError("target_id must be a non-empty string")
        return scrub_text(target_id.strip())

    def get_state(self, target_id: str) -> CircuitTargetState:
        tid = self._validate_target_id(target_id)
        st = self._targets.get(tid)
        if st is None:
            st = CircuitTargetState(target_id=tid, max_attempts=self.max_attempts)
            self._targets[tid] = st
        return st

    def is_open(self, target_id: str) -> bool:
        return self.get_state(target_id).state == CIRCUIT_OPEN_ESCALATE_OWNER

    def check_attempt(self, target_id: str, *, raise_on_open: bool = False) -> CircuitDecision:
        """Pre-flight check before starting the next repair attempt.

        Allows attempts 1..`max_attempts`; trips HARD on attempt #4 (`max_attempts + 1`).
        """
        tid = self._validate_target_id(target_id)
        st = self.get_state(tid)
        next_attempt = st.consecutive_failures + 1

        if st.state == CIRCUIT_OPEN_ESCALATE_OWNER or next_attempt > self.max_attempts:
            if st.state != CIRCUIT_OPEN_ESCALATE_OWNER:
                st.state = CIRCUIT_OPEN_ESCALATE_OWNER
                st.opened_utc = utc_now_iso()
                self._emit_trip_event(st, attempt_number=next_attempt)
            decision = CircuitDecision(
                target_id=tid,
                state=CIRCUIT_OPEN_ESCALATE_OWNER,
                attempt_number=next_attempt,
                max_attempts=self.max_attempts,
                consecutive_failures=st.consecutive_failures,
                retries_remaining=0,
                allowed=False,
                tripped=True,
                escalate_owner=True,
                reason=st.last_failure_reason or "max_attempts_exceeded",
            )
            if raise_on_open:
                raise CircuitOpenError(tid, st.consecutive_failures, decision.reason)
            return decision

        return CircuitDecision(
            target_id=tid,
            state=STATE_CLOSED,
            attempt_number=next_attempt,
            max_attempts=self.max_attempts,
            consecutive_failures=st.consecutive_failures,
            retries_remaining=max(0, self.max_attempts - st.consecutive_failures),
            allowed=True,
            tripped=False,
            escalate_owner=False,
            reason="attempt_allowed",
        )

    def guard_attempt(self, target_id: str) -> CircuitDecision:
        """Fail-closed pre-flight guard: raises `CircuitOpenError` on attempt #4 or open circuit."""
        return self.check_attempt(target_id, raise_on_open=True)

    def record_failure(
        self,
        target_id: str,
        reason: str,
        *,
        ts_utc: str | None = None,
        details: Mapping[str, Any] | None = None,
        raise_on_trip: bool = False,
    ) -> CircuitDecision:
        """Record a failed verification/repair attempt.

        Failures 1..3 keep the breaker `CLOSED`.
        Failure #4 (`consecutive_failures > max_attempts`) trips HARD into
        `CIRCUIT_OPEN_ESCALATE_OWNER` without infinite retries!
        """
        tid = self._validate_target_id(target_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string")
        safe_reason = scrub_text(reason.strip())
        now_iso = ts_utc or utc_now_iso()

        st = self.get_state(tid)
        st.consecutive_failures += 1
        st.total_failures += 1
        st.last_failure_reason = safe_reason
        st.last_failure_utc = now_iso

        tripped = st.state == CIRCUIT_OPEN_ESCALATE_OWNER or st.consecutive_failures > self.max_attempts
        if tripped:
            if st.state != CIRCUIT_OPEN_ESCALATE_OWNER:
                st.state = CIRCUIT_OPEN_ESCALATE_OWNER
                st.opened_utc = now_iso
            self._emit_trip_event(st, attempt_number=st.consecutive_failures, details=details)
            decision = CircuitDecision(
                target_id=tid,
                state=CIRCUIT_OPEN_ESCALATE_OWNER,
                attempt_number=st.consecutive_failures,
                max_attempts=self.max_attempts,
                consecutive_failures=st.consecutive_failures,
                retries_remaining=0,
                allowed=False,
                tripped=True,
                escalate_owner=True,
                reason=safe_reason,
            )
            if raise_on_trip:
                raise CircuitOpenError(tid, st.consecutive_failures, safe_reason)
            return decision

        retries_left = max(0, self.max_attempts - st.consecutive_failures)
        if self._event_queue is not None:
            self._event_queue.append(
                event_type="circuit.failure_recorded",
                source="ratchet_engine",
                severity="warning",
                status="retry_allowed" if retries_left > 0 else "attempts_exhausted",
                summary=f"Target {tid} failed attempt {st.consecutive_failures}/{self.max_attempts}: {safe_reason}",
                details=scrub_mapping(
                    {
                        "target_id": tid,
                        "consecutive_failures": st.consecutive_failures,
                        "max_attempts": self.max_attempts,
                        "retries_remaining": retries_left,
                        "details": dict(details) if details is not None else {},
                    }
                ),
            )
        return CircuitDecision(
            target_id=tid,
            state=STATE_CLOSED,
            attempt_number=st.consecutive_failures,
            max_attempts=self.max_attempts,
            consecutive_failures=st.consecutive_failures,
            retries_remaining=retries_left,
            allowed=retries_left > 0,
            tripped=False,
            escalate_owner=False,
            reason=safe_reason,
        )

    def record_success(self, target_id: str) -> CircuitTargetState:
        """Reset consecutive failure counter on green run; fail-closed if circuit is already OPEN."""
        tid = self._validate_target_id(target_id)
        st = self.get_state(tid)
        if st.state == CIRCUIT_OPEN_ESCALATE_OWNER:
            raise CircuitOpenError(
                tid,
                st.consecutive_failures,
                "Circuit is OPEN; autonomous success cannot clear escalation without explicit owner reset",
            )
        st.consecutive_failures = 0
        st.total_successes += 1
        return st

    def reset_circuit(self, target_id: str, *, owner_reason: str, ts_utc: str | None = None) -> CircuitTargetState:
        """Explicit owner-authorized reset of an open circuit breaker."""
        tid = self._validate_target_id(target_id)
        if not isinstance(owner_reason, str) or not owner_reason.strip():
            raise ValueError("owner_reason must be a non-empty string for explicit circuit reset")
        safe_reason = scrub_text(owner_reason.strip())
        now_iso = ts_utc or utc_now_iso()
        st = self.get_state(tid)
        st.state = STATE_CLOSED
        st.consecutive_failures = 0
        st.opened_utc = ""
        st.last_reset_reason = safe_reason
        st.last_reset_utc = now_iso
        if self._event_queue is not None:
            self._event_queue.append(
                event_type="circuit.owner_reset",
                source="ratchet_engine",
                severity="info",
                status="closed",
                summary=f"Owner reset circuit for {tid}: {safe_reason}",
                details={"target_id": tid, "owner_reason": safe_reason},
            )
        return st

    def _emit_trip_event(
        self,
        st: CircuitTargetState,
        *,
        attempt_number: int,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if self._event_queue is None:
            return
        self._event_queue.append(
            event_type="circuit.tripped",
            source="ratchet_engine",
            severity="critical",
            status=CIRCUIT_OPEN_ESCALATE_OWNER,
            summary=(
                f"{CIRCUIT_OPEN_ESCALATE_OWNER} [{st.target_id}] on attempt #{attempt_number}: {st.last_failure_reason}"
            ),
            details=scrub_mapping(
                {
                    "target_id": st.target_id,
                    "state": CIRCUIT_OPEN_ESCALATE_OWNER,
                    "attempt_number": attempt_number,
                    "max_attempts": self.max_attempts,
                    "consecutive_failures": st.consecutive_failures,
                    "details": dict(details) if details is not None else {},
                }
            ),
        )

    def snapshot_states(self) -> dict[str, dict[str, Any]]:
        return {tid: st.to_dict() for tid, st in sorted(self._targets.items())}


class RatchetEngine:
    """Stateful coordinator combining Monotonic Ratchet, Hard Circuit Breaker, and atomic JSON persistence."""

    def __init__(
        self,
        *,
        state_path: Path | str = DEFAULT_RATCHET_STATE_PATH,
        event_queue_path: Path | str | None = DEFAULT_EVENT_QUEUE_PATH,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError(f"max_attempts must be an integer >= 1, got {max_attempts!r}")
        self.state_path = Path(state_path)
        self.max_attempts = max_attempts
        self.event_queue = EventQueue(event_queue_path) if event_queue_path is not None else None
        self.baselines: dict[str, RatchetBaseline] = {}
        self.breaker = CircuitBreaker(max_attempts=max_attempts, event_queue=self.event_queue)
        self._load_if_exists()

    def _load_if_exists(self) -> None:
        if not self.state_path.is_file():
            return
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Corrupted ratchet state file (expected JSON object): {self.state_path}")
        raw_baselines = raw.get("baselines", {})
        if isinstance(raw_baselines, dict):
            for k, v in raw_baselines.items():
                self.baselines[str(k)] = RatchetBaseline.from_dict(v)
        raw_circuits = raw.get("circuits", {})
        targets: dict[str, CircuitTargetState] = {}
        if isinstance(raw_circuits, dict):
            for k, v in raw_circuits.items():
                targets[str(k)] = CircuitTargetState.from_dict(v)
        self.breaker = CircuitBreaker(
            max_attempts=self.max_attempts,
            targets=targets,
            event_queue=self.event_queue,
        )

    def save(self) -> Path:
        payload = {
            "schema_version": RATCHET_STATE_SCHEMA,
            "updated_utc": utc_now_iso(),
            "max_attempts": self.max_attempts,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
            "baselines": {k: v.to_dict() for k, v in sorted(self.baselines.items())},
            "circuits": self.breaker.snapshot_states(),
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        with _queue_lock(self.state_path):
            return _atomic_write_text(self.state_path, text)

    def verify_and_ratchet(
        self,
        scope: str,
        observed: MetricSnapshot,
        *,
        persist: bool = True,
        raise_on_open: bool = False,
    ) -> dict[str, Any]:
        """Evaluate ratchet for `scope`, update circuit breaker, and persist atomically."""
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("scope must be a non-empty string")
        clean_scope = scrub_text(scope.strip())

        pre_check = self.breaker.check_attempt(clean_scope, raise_on_open=raise_on_open)
        if not pre_check.allowed:
            if persist:
                self.save()
            return {
                "scope": clean_scope,
                "passed": False,
                "verdict": None,
                "circuit": pre_check.to_dict(),
                "order_send_count": ORDER_SEND_COUNT,
                "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
            }

        baseline = self.baselines.get(clean_scope)
        if baseline is None:
            baseline = RatchetBaseline(
                min_tests_passed=0,
                max_tests_failed=0,
                max_ruff_errors=0,
                max_ty_errors=0,
                max_arch_errors=0,
                max_arch_warnings=0,
            )

        verdict = evaluate_ratchet(baseline, observed)
        if verdict.passed:
            self.baselines[clean_scope] = verdict.next_baseline
            self.breaker.record_success(clean_scope)
            circuit_dict = self.breaker.check_attempt(clean_scope).to_dict()
            if self.event_queue is not None:
                self.event_queue.append(
                    event_type="ratchet.pass",
                    source="ratchet_engine",
                    severity="info",
                    status="pass",
                    summary=f"Ratchet PASS for {clean_scope} (tests_passed={observed.tests_passed})",
                    details={
                        "scope": clean_scope,
                        "improvements": list(verdict.improvements),
                        "baseline": verdict.next_baseline.to_dict(),
                    },
                )
        else:
            reg_summary = ", ".join(f"{r['metric']}({r['baseline']}->{r['observed']})" for r in verdict.regressions[:5])
            decision = self.breaker.record_failure(
                clean_scope,
                f"ratchet_regression: {reg_summary}",
                details={"regressions": list(verdict.regressions)},
            )
            circuit_dict = decision.to_dict()
            if self.event_queue is not None:
                self.event_queue.append(
                    event_type="ratchet.regression",
                    source="ratchet_engine",
                    severity="error" if not decision.tripped else "critical",
                    status=decision.state,
                    summary=f"Ratchet FAIL for {clean_scope}: {reg_summary}",
                    details={"scope": clean_scope, "regressions": list(verdict.regressions)},
                )

        if persist:
            self.save()

        return {
            "scope": clean_scope,
            "passed": verdict.passed,
            "verdict": verdict.to_dict(),
            "circuit": circuit_dict,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Naqex Poteto Ratchet & Circuit Breaker state.")
    parser.add_argument("--state", type=Path, default=DEFAULT_RATCHET_STATE_PATH, help="Ratchet state JSON path")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON summary")
    args = parser.parse_args(argv)

    engine = RatchetEngine(state_path=args.state, event_queue_path=None)
    summary = {
        "schema_version": RATCHET_STATE_SCHEMA,
        "state_exists": args.state.is_file(),
        "max_attempts": engine.max_attempts,
        "baseline_count": len(engine.baselines),
        "circuit_count": len(engine.breaker.snapshot_states()),
        "open_circuits": [
            tid for tid, st in engine.breaker.snapshot_states().items() if st["state"] == CIRCUIT_OPEN_ESCALATE_OWNER
        ],
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
    }
    if args.as_json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(
            f"RatchetEngine: baselines={summary['baseline_count']}, "
            f"circuits={summary['circuit_count']}, open={len(summary['open_circuits'])}, OrderSend=0"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
