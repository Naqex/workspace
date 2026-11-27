"""Naqex Quant Pod Local Interactive Web Control Room Server (`127.0.0.1:8787`, stdlib-only).

Thin backward-compatible façade delegating to `cockpit.modules.*`.
Zero external CDNs, strictly localhost-bound (`127.0.0.1`), 100% read-only on workspace state
(`ORDER_SEND_COUNT = 0`, Holdout 2025+ SEALED).

Live JSON API endpoints:
  - GET  /                     -> Flat-dark institutional Cockpit UI (`static/index.html`)
  - GET  /static/<asset>       -> Static CSS/JS (`styles.css`, `app.js`) with path-traversal guard
  - GET  /api/health           -> Lightweight readiness check
  - GET  /api/summary          -> Safety seal, registry, pod snapshot, FTMO specs, Red-Team stress curve
  - GET  /api/overview         -> Unified summary + live-telemetry + Black-Swan/Multi-Prop stress snapshot
  - GET  /api/allocations      -> Multi-sleeve equity/underwater curves (4-6+ sleeves), N×N corr matrix & metrics
  - GET  /api/live-telemetry   -> Live Crypto L2 shadow, Maker probe, MT5 demo/spreads, Real-Tick Matrix, Red-News
  - GET  /api/stress           -> Black-Swan VND/USD loss matrix (-30%/-50% CEX, Corr=0.85) & Multi-Prop budget audit
  - GET|POST /api/vnd-calculator -> PROFILE.md-calibrated VND/USD absolute risk, stress & crossover calculator
  - GET  /api/rebalancer       -> Dry-run Sleeve #3B IBKR Macro ETF weights & order tickets (`OrderSend = 0`)
  - GET  /api/blackfriday-sprint -> Cached 30s Black Friday 30/11 countdown, Mũi 1-3 metrics & Vault status
  - GET  /api/node1-summary    -> Cached 30s sanitized naqex-node1 health summary (live SSH 4s cap or fallback)
  - GET  /api/automation/status   -> Stateless read-only 24/7 automation & ops-cloud summary (`OrderSend = 0`)
  - GET  /api/automation/events   -> Stateless read-only automation event queue tail (`OrderSend = 0`)
  - GET  /api/automation/features -> Stateless read-only feature_map + product QA overlay (`OrderSend = 0`)
"""

from __future__ import annotations

import sys
import types
import urllib
import urllib.request  # noqa: F401
from pathlib import Path
from typing import Any

_AI_ENGINES_BOOT = Path(__file__).resolve().parents[1]
if str(_AI_ENGINES_BOOT) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_BOOT))

from cockpit.modules.automation import (  # noqa: E402, F401
    build_automation_events_payload,
    build_automation_features_payload,
    build_automation_status_payload,
    validate_sidecar_config,
)
from cockpit.modules.helpers import (  # noqa: E402, F401
    _coerce_opt_bool,
    _coerce_opt_float,
    _coerce_opt_int,
    _downsample_series,
    _extract_first_float,
    _extract_first_int,
    _format_countdown_vi,
    _load_upcoming_red_news,
    _parse_float_token,
    _parse_pod_snapshot_md,
    _pip_size_for_symbol,
    _read_jsonl_tail,
    _safe_read_json,
    _sanitize_heroku_status,
    _sanitize_ntp_offset,
    _sanitize_short_token,
)
from cockpit.modules.node1 import (  # noqa: E402, F401
    _probe_node1_via_node_ctl,
    _read_local_node1_fallback,
    build_node1_summary_payload,
)
from cockpit.modules.portfolio import (  # noqa: E402, F401
    _get_sleeve1_cached,
    build_allocations_payload,
    build_overview_payload,
    build_summary_payload,
)
from cockpit.modules.prop_metrix import build_prop_metrix_payload  # noqa: E402
from cockpit.modules.prop_risk import (  # noqa: E402, F401
    _build_prop_risk_attribution,
    _compute_positions_mae_mfe,
    _fetch_heroku_node1_cached,
)
from cockpit.modules.routes import create_server, main, make_handler  # noqa: E402
from cockpit.modules.sprint import (  # noqa: E402, F401
    _detect_realtick_model,
    _load_mui3_master_prop7e_scenarios,
    build_blackfriday_sprint_payload,
)
from cockpit.modules.sprint_friction import (  # noqa: E402, F401
    _load_live_calibration_progress,
    _load_mui1_mui2_friction_and_spreads,
)
from cockpit.modules.state import (  # noqa: E402, F401
    _HEROKU_CACHE_LOCK,
    _HEROKU_STATUS_CACHE,
    _IPV4_OR_URL_RE,
    _NODE1_CACHE,
    _NODE1_CACHE_LOCK,
    _NTP_OFFSET_RE,
    _SLEEVE1_CACHE,
    _SLEEVE1_LOCK,
    _SPRINT_CACHE,
    _SPRINT_CACHE_LOCK,
    _STRESS_CACHE_LOCK,
    _STRESS_MD_CACHE,
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
    register_facade_module,
)
from cockpit.modules.stress import (  # noqa: E402, F401
    _interpolate_red_team_curve,
    _parse_stress_and_multiprop_md,
    build_stress_payload,
    compute_vnd_risk_calculator,
)
from cockpit.modules.telemetry import (  # noqa: E402, F401
    apply_emergency_cover_action,
    build_live_telemetry_payload,
    handle_prop_terms_audit_request,
    read_emergency_cover_state,
)
from quant_factory.ibkr_macro_rebalancer import VALID_MODES, generate_rebalance_plan  # noqa: E402
from quant_factory.portfolio_allocator import (  # noqa: E402
    align_sleeves_business_days,
    compute_series_metrics,
    load_external_sleeve_json,
)
from quant_factory.prop_terms_auditor import FIRM_BASELINES, audit_prop_terms_text  # noqa: E402
from quant_factory.treasury_ledger import DEFAULT_USD_VND_RATE, compute_prop_own_crossover  # noqa: E402

__all__ = [
    "AI_ENGINES",
    "BLACKFRIDAY_DEADLINE_DT",
    "BLACKFRIDAY_DEADLINE_ICT",
    "BLACKFRIDAY_DEADLINE_ISO",
    "COCKPIT_DIR",
    "CORE_DEV_SPREAD_BASELINE_BPS",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_USD_VND_RATE",
    "EMERGENCY_CONFIRM_CODES",
    "FIRM_BASELINES",
    "MIME_TYPES",
    "NODE1_CACHE_TTL_SEC",
    "NODE1_SSH_TIMEOUT_SEC",
    "ORDER_SEND_COUNT",
    "PROP_METRIX_PROGRAMS",
    "PROP_PROGRAMS",
    "ROOT",
    "SPRINT_CACHE_TTL_SEC",
    "STATIC_DIR",
    "VALID_MODES",
    "VN_TZ",
    "align_sleeves_business_days",
    "apply_emergency_cover_action",
    "audit_prop_terms_text",
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
    "compute_prop_own_crossover",
    "compute_series_metrics",
    "compute_vnd_risk_calculator",
    "create_server",
    "generate_rebalance_plan",
    "handle_prop_terms_audit_request",
    "load_external_sleeve_json",
    "main",
    "make_handler",
    "read_emergency_cover_state",
    "urllib",
    "validate_sidecar_config",
]


class _SyncedFacadeModule(types.ModuleType):
    """Propagate façade attribute mutations/deletions to backing `cockpit.modules` & sibling façades."""

    _sync_prefix: str = "cockpit.modules"
    _facade_file: str = ""
    _deleted_targets: dict[str, set[str]]

    def _iter_sync_modules(self) -> list[types.ModuleType]:
        prefix = self._sync_prefix
        prefix_dot = f"{prefix}."
        facade_file = self._facade_file
        targets: list[types.ModuleType] = []
        for mod_name, mod in list(sys.modules.items()):
            if mod is None or mod is self:
                continue
            if mod_name == prefix or mod_name.startswith(prefix_dot):
                targets.append(mod)
                continue
            if facade_file:
                mod_file = getattr(mod, "__file__", None)
                if mod_file:
                    try:
                        if str(Path(mod_file).resolve()) == facade_file:
                            targets.append(mod)
                    except OSError:
                        pass
        return targets

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if (name.startswith("__") and name.endswith("__")) or name in (
            "_sync_prefix",
            "_facade_file",
            "_deleted_targets",
        ):
            return
        deleted = getattr(self, "_deleted_targets", {}).get(name)
        for mod in self._iter_sync_modules():
            if name in mod.__dict__ or (deleted is not None and mod.__name__ in deleted):
                types.ModuleType.__setattr__(mod, name, value)
                if deleted is not None:
                    deleted.discard(mod.__name__)

    def __delattr__(self, name: str) -> None:
        super().__delattr__(name)
        if (name.startswith("__") and name.endswith("__")) or name in (
            "_sync_prefix",
            "_facade_file",
            "_deleted_targets",
        ):
            return
        deleted_map: dict[str, set[str]] = getattr(self, "_deleted_targets", {})
        recorded = deleted_map.setdefault(name, set())
        for mod in self._iter_sync_modules():
            if name in mod.__dict__:
                recorded.add(mod.__name__)
                types.ModuleType.__delattr__(mod, name)


_this_mod: Any = sys.modules.get(__name__)
if _this_mod is not None:
    if not isinstance(_this_mod, _SyncedFacadeModule):
        _this_mod.__class__ = _SyncedFacadeModule
        types.ModuleType.__setattr__(_this_mod, "_sync_prefix", "cockpit.modules")
        types.ModuleType.__setattr__(_this_mod, "_facade_file", str(Path(__file__).resolve()))
        types.ModuleType.__setattr__(_this_mod, "_deleted_targets", {})
    register_facade_module(_this_mod)

if __name__ == "__main__":
    raise SystemExit(main())
