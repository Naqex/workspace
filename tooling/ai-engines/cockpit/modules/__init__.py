"""Modular backend package for the Naqex Quant Pod Local Web Control Room."""

from __future__ import annotations

from cockpit.modules.automation import (
    build_automation_events_payload,
    build_automation_features_payload,
    build_automation_status_payload,
    validate_sidecar_config,
)
from cockpit.modules.node1 import build_node1_summary_payload
from cockpit.modules.portfolio import build_allocations_payload, build_overview_payload, build_summary_payload
from cockpit.modules.prop_metrix import build_prop_metrix_payload
from cockpit.modules.routes import create_server, main, make_handler
from cockpit.modules.sprint import build_blackfriday_sprint_payload
from cockpit.modules.state import (
    AI_ENGINES,
    BLACKFRIDAY_DEADLINE_DT,
    BLACKFRIDAY_DEADLINE_ICT,
    BLACKFRIDAY_DEADLINE_ISO,
    COCKPIT_DIR,
    CORE_DEV_SPREAD_BASELINE_BPS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    EMERGENCY_CONFIRM_CODES,
    MIME_TYPES,
    NODE1_CACHE_TTL_SEC,
    NODE1_SSH_TIMEOUT_SEC,
    ORDER_SEND_COUNT,
    PROP_METRIX_PROGRAMS,
    PROP_PROGRAMS,
    ROOT,
    SPRINT_CACHE_TTL_SEC,
    STATIC_DIR,
    VN_TZ,
    clear_sprint_and_node1_caches,
)
from cockpit.modules.stress import build_stress_payload, compute_vnd_risk_calculator
from cockpit.modules.telemetry import (
    apply_emergency_cover_action,
    build_live_telemetry_payload,
    handle_prop_terms_audit_request,
    read_emergency_cover_state,
)

__all__ = [
    "AI_ENGINES",
    "BLACKFRIDAY_DEADLINE_DT",
    "BLACKFRIDAY_DEADLINE_ICT",
    "BLACKFRIDAY_DEADLINE_ISO",
    "COCKPIT_DIR",
    "CORE_DEV_SPREAD_BASELINE_BPS",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "EMERGENCY_CONFIRM_CODES",
    "MIME_TYPES",
    "NODE1_CACHE_TTL_SEC",
    "NODE1_SSH_TIMEOUT_SEC",
    "ORDER_SEND_COUNT",
    "PROP_METRIX_PROGRAMS",
    "PROP_PROGRAMS",
    "ROOT",
    "SPRINT_CACHE_TTL_SEC",
    "STATIC_DIR",
    "VN_TZ",
    "apply_emergency_cover_action",
    "build_allocations_payload",
    "build_automation_events_payload",
    "build_automation_features_payload",
    "build_automation_status_payload",
    "build_blackfriday_sprint_payload",
    "build_live_telemetry_payload",
    "build_node1_summary_payload",
    "build_overview_payload",
    "build_prop_metrix_payload",
    "build_stress_payload",
    "build_summary_payload",
    "clear_sprint_and_node1_caches",
    "compute_vnd_risk_calculator",
    "create_server",
    "handle_prop_terms_audit_request",
    "main",
    "make_handler",
    "read_emergency_cover_state",
    "validate_sidecar_config",
]
