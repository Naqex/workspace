"""Naqex Quant Factory: Modular 4-layer parallel research, Numba JIT prop lifecycle & reporting engine.

Uses PEP 562 lazy module/symbol resolution so importing `quant_factory` or any single submodule
never eagerly pulls heavy scientific dependencies (`numba`, `scipy`, `pyarrow`, `pass*`).
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_store import (
        CONFIGS_DIR,
        DERIVED_CACHE_DIR,
        REGISTRY_PATH,
        build_or_load_frozen_tapes,
        compute_tapes_binding,
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
    from .live_decay_monitor import calibrate_baseline, evaluate_live_decay
    from .ops_monitor import dispatch_alert, format_alert_message, inspect_heartbeat
    from .prop_engine import (
        apply_vol_targeting_causal,
        compute_cluster_a_invdd_weights,
        evaluate_firm_profile,
        make_block_bootstrap_indices,
        replay_portfolio_m1,
    )
    from .report_gen import format_markdown_table, write_verified_receipt
    from .robustness_gate import (
        RobustnessThresholds,
        buy_sell_symmetry_audit,
        evaluate_robustness_gate,
        random_entry_mc_on_bars,
        random_entry_mc_on_closes,
        top_outlier_trim_audit,
        worst_year_stability_audit,
    )
    from .tca_reconcile import compute_tca_report, load_exec_audit_csv

_PACKAGE_DIR = Path(__file__).resolve().parent

_SYMBOL_TO_MODULE: dict[str, str] = {
    # data_store
    "CONFIGS_DIR": "data_store",
    "DERIVED_CACHE_DIR": "data_store",
    "REGISTRY_PATH": "data_store",
    "build_or_load_frozen_tapes": "data_store",
    "compute_tapes_binding": "data_store",
    "load_firm_config": "data_store",
    "load_profile_config": "data_store",
    "load_red_news_calendar": "data_store",
    "load_registry": "data_store",
    # eval_pipeline
    "benjamini_hochberg": "eval_pipeline",
    "deflated_sharpe_ratio": "eval_pipeline",
    "run_parallel_sweep": "eval_pipeline",
    "sign_flip_p_numba": "eval_pipeline",
    "tail_correlation_report": "eval_pipeline",
    # prop_engine
    "apply_vol_targeting_causal": "prop_engine",
    "compute_cluster_a_invdd_weights": "prop_engine",
    "evaluate_firm_profile": "prop_engine",
    "make_block_bootstrap_indices": "prop_engine",
    "replay_portfolio_m1": "prop_engine",
    # report_gen
    "format_markdown_table": "report_gen",
    "write_verified_receipt": "report_gen",
    # robustness_gate
    "RobustnessThresholds": "robustness_gate",
    "buy_sell_symmetry_audit": "robustness_gate",
    "evaluate_robustness_gate": "robustness_gate",
    "random_entry_mc_on_bars": "robustness_gate",
    "random_entry_mc_on_closes": "robustness_gate",
    "top_outlier_trim_audit": "robustness_gate",
    "worst_year_stability_audit": "robustness_gate",
    # tca_reconcile
    "compute_tca_report": "tca_reconcile",
    "load_exec_audit_csv": "tca_reconcile",
    # live_decay_monitor
    "calibrate_baseline": "live_decay_monitor",
    "evaluate_live_decay": "live_decay_monitor",
    # ops_monitor
    "inspect_heartbeat": "ops_monitor",
    "format_alert_message": "ops_monitor",
    "dispatch_alert": "ops_monitor",
}

__all__ = [
    "CONFIGS_DIR",
    "DERIVED_CACHE_DIR",
    "REGISTRY_PATH",
    "build_or_load_frozen_tapes",
    "compute_tapes_binding",
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
    "RobustnessThresholds",
    "buy_sell_symmetry_audit",
    "evaluate_robustness_gate",
    "random_entry_mc_on_bars",
    "random_entry_mc_on_closes",
    "top_outlier_trim_audit",
    "worst_year_stability_audit",
    "compute_tca_report",
    "load_exec_audit_csv",
    "calibrate_baseline",
    "evaluate_live_decay",
    "inspect_heartbeat",
    "format_alert_message",
    "dispatch_alert",
]


def __getattr__(name: str) -> Any:
    mod_name = _SYMBOL_TO_MODULE.get(name)
    if mod_name is not None:
        mod = importlib.import_module(f".{mod_name}", __name__)
        val = getattr(mod, name)
        globals()[name] = val
        return val
    if not name.startswith("_") and (_PACKAGE_DIR / f"{name}.py").is_file():
        mod = importlib.import_module(f".{name}", __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    submods = [p.stem for p in _PACKAGE_DIR.glob("*.py") if p.stem != "__init__"]
    return sorted(set(globals()) | set(__all__) | set(submods))
