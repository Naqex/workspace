"""Naqex Front-3 offline automation primitives (`OrderSend = 0`, `python -O` safe).

Exports the atomic secret-scrubbed event queue and Lauren Tan (`@poteto`)
5-pillar metric ratchet & hard 3-attempt circuit breaker.
"""

from __future__ import annotations

from tooling.automation.event_queue import (
    DEFAULT_EVENT_QUEUE_PATH,
    EVENT_SCHEMA_VERSION,
    ORDER_SEND_COUNT,
    AutomationEvent,
    EventQueue,
    EventQueueError,
    append_event,
    prune_events,
    read_events,
    scrub_mapping,
    scrub_text,
)
from tooling.automation.ratchet_engine import (
    CIRCUIT_OPEN_ESCALATE_OWNER,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_RATCHET_STATE_PATH,
    HOLDOUT_ROWS_ANALYSED,
    STATE_CLOSED,
    CircuitBreaker,
    CircuitDecision,
    CircuitOpenError,
    CircuitTargetState,
    MetricSnapshot,
    RatchetBaseline,
    RatchetEngine,
    RatchetVerdict,
    evaluate_ratchet,
)

__all__ = [
    "AutomationEvent",
    "CIRCUIT_OPEN_ESCALATE_OWNER",
    "CircuitBreaker",
    "CircuitDecision",
    "CircuitOpenError",
    "CircuitTargetState",
    "DEFAULT_EVENT_QUEUE_PATH",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_RATCHET_STATE_PATH",
    "EVENT_SCHEMA_VERSION",
    "EventQueue",
    "EventQueueError",
    "HOLDOUT_ROWS_ANALYSED",
    "MetricSnapshot",
    "ORDER_SEND_COUNT",
    "RatchetBaseline",
    "RatchetEngine",
    "RatchetVerdict",
    "STATE_CLOSED",
    "append_event",
    "evaluate_ratchet",
    "prune_events",
    "read_events",
    "scrub_mapping",
    "scrub_text",
]
