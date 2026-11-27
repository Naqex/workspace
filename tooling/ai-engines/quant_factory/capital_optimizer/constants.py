"""Shared constants, paths, enum codes, and variant phase presets for the capital optimizer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from quant_core.io_utils import repo_root_from

StageArrays = tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    np.ndarray, np.ndarray, np.ndarray, np.ndarray,
]

ROOT: Path = repo_root_from(__file__)
AI_ENGINES: Path = ROOT / "tooling" / "ai-engines"

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
HOLDOUT_MAX_YEAR: int = 2024

DEFAULT_SEED: int = 20261126
BLOCK_LEN: int = 5
TRADING_DAYS_PER_MONTH: int = 21
TRADING_DAYS_PER_YEAR: int = 252
CALENDAR_DAYS_PER_TRADING_DAY: float = 365.2425 / 252.0

CORE7_IDS: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
)

TIER_SIZES_USD: tuple[float, ...] = (
    5_000.0,
    10_000.0,
    20_000.0,
    25_000.0,
    50_000.0,
    60_000.0,
    100_000.0,
    200_000.0,
)

FRICTION_LEVELS: tuple[float, ...] = (0.66, 1.00, 1.25, 1.50, 1.75)
FRICTION_SWEEP_WITH_BREAKEVEN: tuple[float, ...] = (
    0.66,
    1.00,
    1.25,
    1.50,
    1.75,
    2.00,
    2.50,
    3.00,
    3.50,
    4.00,
)
DISCOUNT_RATES_ANNUAL: tuple[float, ...] = (0.04, 0.06, 0.08)
DEFAULT_DISCOUNT_RATE: float = 0.06

BANKROLL_GRID_VND_TR: tuple[float, ...] = (15.0, 25.0, 35.0, 50.0, 80.0)
TOPUP_GRID_VND_TR: tuple[float, ...] = (0.0, 3.0, 5.0)

DEFAULT_CATALOG_PATH: Path = ROOT / "tooling/ai-engines/configs/prop_pricing_catalog.json"
DEFAULT_STEP5_REPORT_PATH: Path = (
    ROOT / "private_vault/strategies/step5-c00-vs-c10-economic-20261126/step5_c00_vs_c10_economic_report.json"
)
DEFAULT_OUT_JSON: Path = (
    ROOT / "private_vault/strategies/step5-capital-optimizer-20261126/optimizer_results.json"
)
DEFAULT_OUT_JSON_V2: Path = (
    ROOT / "private_vault/strategies/step7-astra-r10-closures-20261126/optimizer_v2_results.json"
)
DEFAULT_OUT_MD: Path = (
    ROOT / "planning/research/MULTI-FIRM-CAPITAL-PROMO-OPTIMIZER-20261126.md"
)

PRIMARY_VARIANT_DEFAULT: str = "C10_NEWS_ON"
CONTROL_VARIANT_DEFAULT: str = "C00"
E8_EXCLUDED_FIRM_IDS: frozenset[str] = frozenset({"E8_MARKETS", "E8"})

# DD type enum codes for Numba kernels
DD_STATIC: int = 0
DD_EOD_TRAILING: int = 1
DD_INTRADAY_TRAILING: int = 2

# Per-contract daily DD anchor enum codes for Numba kernels
DAILY_DD_ANCHOR_INITIAL_BALANCE: int = 0  # daily_floor = s_bal - cap * daily_lim (e.g. FTMO)
DAILY_DD_ANCHOR_PREV_DAY_BALANCE: int = 1  # daily_floor = s_bal * (1.0 - daily_lim) (holds ONLY when flat at reset)

DD_ANCHOR_TAG_BALANCE_VERIFIED: str = "DD_ANCHOR_BALANCE_VERIFIED"
DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT: str = "DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET"
MAX_FUTURE_TIMESTAMP_SKEW_DAYS: float = 1.0

# Variant phase definitions (`C10_NEWS_ON` primary candidate vs `C00` v1.01 control vs `C10` News-OFF ablation)
VARIANT_PHASE_CONFIGS: dict[str, dict[str, Any]] = {
    "C00": {
        "label": "C00 (v1.01 Incumbent · News ON all phases · P1 4x/L50->2.01x · P2 2x/L50->1x · Funded 1x)",
        "p1_mult": 4.00,
        "p1_lock_trigger": 0.50,
        "p1_lock_mult": 2.01,
        "p2_mult": 2.00,
        "p2_lock_trigger": 0.50,
        "p2_lock_mult": 1.00,
        "funded_mult": 1.00,
        "amber_dd": 0.035,
        "amber_mult": 0.65,
        "red_dd": 0.060,
        "red_mult": 0.40,
        "p1_symcap_pct": 1.75,
        "p2_symcap_pct": 1.25,
        "funded_symcap_pct": 1.00,
        "p1_news_guard": True,
        "p2_news_guard": True,
        "funded_news_guard": True,
        "p1_ea_daily_stop": 0.035,
        "p1_ea_static_stop": 0.080,
        "p2_ea_daily_stop": 0.025,
        "p2_ea_static_stop": 0.075,
        "funded_ea_daily_stop": 0.025,
        "funded_ea_static_stop": 0.075,
    },
    "C10": {
        "label": (
            "C10 (News-OFF Sensitivity ONLY · News OFF P1/P2, ON Funded · "
            "P1 4x/L70->2.5x · P2 3.5x/L70->1.75x · Funded 1.25x)"
        ),
        "p1_mult": 4.00,
        "p1_lock_trigger": 0.70,
        "p1_lock_mult": 2.50,
        "p2_mult": 3.50,
        "p2_lock_trigger": 0.70,
        "p2_lock_mult": 1.75,
        "funded_mult": 1.25,
        "amber_dd": 0.035,
        "amber_mult": 0.65,
        "red_dd": 0.060,
        "red_mult": 0.40,
        "p1_symcap_pct": 1.75,
        "p2_symcap_pct": 1.75,
        "funded_symcap_pct": 1.25,
        "p1_news_guard": False,
        "p2_news_guard": False,
        "funded_news_guard": True,
        "p1_ea_daily_stop": 0.035,
        "p1_ea_static_stop": 0.080,
        "p2_ea_daily_stop": 0.030,
        "p2_ea_static_stop": 0.075,
        "funded_ea_daily_stop": 0.025,
        "funded_ea_static_stop": 0.075,
    },
    "C10_NEWS_ON": {
        "label": (
            "C10_NEWS_ON (Primary Candidate · Red-News ON all phases · "
            "P1 4x/L70->2.5x · P2 3.5x/L70->1.75x · Funded 1.25x)"
        ),
        "p1_mult": 4.00,
        "p1_lock_trigger": 0.70,
        "p1_lock_mult": 2.50,
        "p2_mult": 3.50,
        "p2_lock_trigger": 0.70,
        "p2_lock_mult": 1.75,
        "funded_mult": 1.25,
        "amber_dd": 0.035,
        "amber_mult": 0.65,
        "red_dd": 0.060,
        "red_mult": 0.40,
        "p1_symcap_pct": 1.75,
        "p2_symcap_pct": 1.75,
        "funded_symcap_pct": 1.25,
        "p1_news_guard": True,
        "p2_news_guard": True,
        "funded_news_guard": True,
        "p1_ea_daily_stop": 0.035,
        "p1_ea_static_stop": 0.080,
        "p2_ea_daily_stop": 0.030,
        "p2_ea_static_stop": 0.075,
        "funded_ea_daily_stop": 0.025,
        "funded_ea_static_stop": 0.075,
    },
}
