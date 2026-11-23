"""Naqex Quant Factory: Modular 4-layer parallel research, Numba JIT prop lifecycle & reporting engine."""

from .data_store import (
    CONFIGS_DIR,
    DERIVED_CACHE_DIR,
    REGISTRY_PATH,
    build_or_load_frozen_tapes,
    load_firm_config,
    load_profile_config,
    load_red_news_calendar,
    load_registry,
)
from .eval_pipeline import (
    benjamini_hochberg,
    deflated_sharpe_ratio,
    run_parallel_sweep,
    sign_flip_p_numba,
    tail_correlation_report,
)
from .prop_engine import (
    apply_vol_targeting_causal,
    compute_cluster_a_invdd_weights,
    evaluate_firm_profile,
    make_block_bootstrap_indices,
    replay_portfolio_m1,
)
from .live_decay_monitor import calibrate_baseline, evaluate_live_decay
from .ops_monitor import dispatch_alert, format_alert_message, inspect_heartbeat
from .report_gen import format_markdown_table, write_verified_receipt
from .tca_reconcile import compute_tca_report, load_exec_audit_csv

__all__ = [
    "CONFIGS_DIR",
    "DERIVED_CACHE_DIR",
    "REGISTRY_PATH",
    "build_or_load_frozen_tapes",
    "load_firm_config",
    "load_profile_config",
    "load_red_news_calendar",
    "load_registry",
    "benjamini_hochberg",
    "deflated_sharpe_ratio",
    "run_parallel_sweep",
    "sign_flip_p_numba",
    "tail_correlation_report",
    "apply_vol_targeting_causal",
    "compute_cluster_a_invdd_weights",
    "evaluate_firm_profile",
    "make_block_bootstrap_indices",
    "replay_portfolio_m1",
    "format_markdown_table",
    "write_verified_receipt",
    "compute_tca_report",
    "load_exec_audit_csv",
    "calibrate_baseline",
    "evaluate_live_decay",
    "inspect_heartbeat",
    "format_alert_message",
    "dispatch_alert",
]
