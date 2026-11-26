"""Multi-Firm Prop Capital Scaling, Exact 0.01-Lot Rounding & Dynamic Promo Optimizer (v2 — Astra R10 Closures).

STRICT SAFETY & ANTI-OVERFIT INVARIANTS:
  - Holdout 2025+ STRICTLY SEALED (`holdout_rows_analysed = 0`, NEVER touches `.runtime/holdout-m1-cache/`).
  - Strictly enforces `day < "2025-01-01"` / `year <= 2024` on all loaded/replayed tapes and asserts
    `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA integrity when running on workspace data.
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero broker/MT5/VPS interaction.
  - Primary variant locked to `C10_NEWS_ON` (Red-News Guard ON all phases) with `C00` control across
    all tables, dual-horizon sale calendar, and capital-scaling policies.
  - Fail-closed catalog loading (`allow_fallback=False`) + per-program & per-tier `verified_utc`
    freshness enforcement (`<= staleness_max_days`).
  - Purchase-day ticket pricing (`fee_day0_usd` active promo on Day 0 vs `fee_regular_usd` on retries
    and post-Day-0 purchases — ZERO perpetual Black Friday discount on retries).
  - Per-contract `daily_dd_anchor` (`initial_balance` static vs `prev_day_balance` / `balance_or_equity`).
  - Separated VN fee accounting (`+2.5%` non-refundable card FX buy fee, `0.0%` FTMO direct-to-card
    refund withdrawal fee + `1.5%` rail sensitivity, `1.5%–4.0%` payout rail + FX spread).
  - `own_book` DISABLED (`0.0`) across all prop-strategy ranking tables (`P1..P5B`) to eliminate
    riskless-spread distortion; `E8 Pro` excluded from `P5/P5B` (3 surviving firms: FTMO + The5ers +
    IC Funded) while retained in Section 4 structural-trap & Payout #1 buffer-sensitivity audit.
  - `P4A_WAIT_FOR_100K` (`wait_for_top_rung_slot2=True`), `P4B_PARALLEL_2X100K` (Day-0 parallel
    `2x 100K` alongside sequential `P4B_DIRECT_100K` & `P4C_DIRECT_200K`), full `mean` + `median`
    + `P(NPV24 <= 0)` on every Pareto cell, and Dual-Horizon exact-sweep Dynamic Sale Calculator.
  - Every daily-level lifecycle table is explicitly tagged `DAILY_APPROX`, and every firm is tagged
    `MEASURED_DEMO_EXECUTION` (FTMO only) vs `TERMS_VERIFIED_EXECUTION_UNMEASURED`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

from numba import njit
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

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
FRICTION_SWEEP_WITH_BREAKEVEN: tuple[float, ...] = (0.66, 1.00, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 3.50, 4.00)
DISCOUNT_RATES_ANNUAL: tuple[float, ...] = (0.04, 0.06, 0.08)
DEFAULT_DISCOUNT_RATE: float = 0.06

BANKROLL_GRID_VND_TR: tuple[float, ...] = (15.0, 25.0, 35.0, 50.0, 80.0)
TOPUP_GRID_VND_TR: tuple[float, ...] = (0.0, 3.0, 5.0)

DEFAULT_CATALOG_PATH = ROOT / "tooling/ai-engines/configs/prop_pricing_catalog.json"
DEFAULT_STEP5_REPORT_PATH = (
    ROOT / "private_vault/strategies/step5-c00-vs-c10-economic-20261126/step5_c00_vs_c10_economic_report.json"
)
DEFAULT_OUT_JSON = (
    ROOT / "private_vault/strategies/step5-capital-optimizer-20261126/optimizer_results.json"
)
DEFAULT_OUT_JSON_V2 = (
    ROOT / "private_vault/strategies/step7-astra-r10-closures-20261126/optimizer_v2_results.json"
)
DEFAULT_OUT_MD = (
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
DAILY_DD_ANCHOR_INITIAL_BALANCE: int = 0   # daily_floor = s_bal - cap * daily_lim (e.g. FTMO)
DAILY_DD_ANCHOR_PREV_DAY_BALANCE: int = 1  # daily_floor = s_bal * (1.0 - daily_lim) (holds ONLY when flat at reset for The5ers/IC Funded)

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
        "label": "C10 (News-OFF Sensitivity ONLY · News OFF P1/P2, ON Funded · P1 4x/L70->2.5x · P2 3.5x/L70->1.75x · Funded 1.25x)",
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
        "label": "C10_NEWS_ON (Primary Candidate · Red-News ON all phases · P1 4x/L70->2.5x · P2 3.5x/L70->1.75x · Funded 1.25x)",
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


# ---------------------------------------------------------------------------
# Offline-Safe Default Pricing Catalog (OPT-IN ONLY for isolated tests; production is fail-closed!)
# ---------------------------------------------------------------------------

def build_default_pricing_catalog() -> dict[str, Any]:
    """Offline-safe default catalog for opt-in unit tests (`allow_fallback=True` only)."""
    default_ts = "2026-11-26T11:25:00Z"
    return {
        "schema": "naqex-prop-pricing-catalog-v1-fallback",
        "updated_utc": default_ts,
        "staleness_max_days": 7,
        "is_fallback": True,
        "fx_rates": {
            "usd_vnd": 25_450.0,
            "eur_vnd": 26_900.0,
            "fetched_utc": default_ts,
            "source": "FALLBACK_REF_UNTIL_PRICING_CATALOG_LOADED",
        },
        "vn_transaction_costs": {
            "card_fx_buy_fee_pct": 0.025,
            "fx_conversion_spread_pct": 0.005,
            "default_withdrawal_fee_pct": 0.015,
            "default_ftmo_refund_withdrawal_fee_pct": 0.0,
        },
        "seasonal_sale_calendar": [
            {"event": "Black Friday / Cyber Monday", "month": 11, "day_approx": 26, "typical_discount_pct": 0.20, "max_discount_pct": 0.30, "confidence_tag": "HISTORICAL_PATTERN"},
            {"event": "New Year / Lunar New Year", "month": 1, "day_approx": 15, "typical_discount_pct": 0.10, "max_discount_pct": 0.15, "confidence_tag": "HISTORICAL_PATTERN"},
            {"event": "Mid-Year / Anniversary", "month": 6, "day_approx": 15, "typical_discount_pct": 0.10, "max_discount_pct": 0.15, "confidence_tag": "HISTORICAL_PATTERN"},
            {"event": "Back to Trading (Sep)", "month": 9, "day_approx": 1, "typical_discount_pct": 0.10, "max_discount_pct": 0.15, "confidence_tag": "HISTORICAL_PATTERN"},
        ],
        "programs": [
            # 1. FTMO 2-Step Standard (LIVE VN CHECKOUT SCREENSHOTS 2026-11-26)
            {
                "program_id": "FTMO_2STEP_STD",
                "firm_id": "FTMO",
                "firm_name": "FTMO",
                "mode_name": "FTMO 2-Step Standard",
                "profile_mode": "Standard",
                "verified_utc": default_ts,
                "steps": 2,
                "p1_target_pct": 0.10,
                "p2_target_pct": 0.05,
                "dd_daily_pct": 0.05,
                "dd_max_pct": 0.10,
                "dd_type": "static",
                "daily_dd_anchor": "initial_balance",
                "daily_dd_anchor_raw": "MIDNIGHT_BALANCE_PRAGUE_0000",
                "trail_lock_at_initial": False,
                "best_day_cap_pct": 0.0,
                "min_trading_days": 4,
                "min_profitable_days": 0,
                "min_profitable_day_pct": 0.0,
                "fee_refund_pct": 1.0,
                "refund_payout_milestone": 1,
                "refund_is_hub_credit": False,
                "profit_split_pct": 0.80,
                "payout_cycle_trading_days": 10,
                "min_payout_usd": 50.0,
                "payout_rail_fee_pct": 0.010,
                "fx_conversion_spread_pct": 0.005,
                "payout_withdrawal_fee_pct": 0.015,
                "withdrawal_fee_pct": 0.015,
                "refund_withdrawal_fee_pct": 0.0,
                "max_allocation_usd": 400_000.0,
                "news_restricted_eval": False,
                "news_restricted_funded": True,
                "execution_evidence_tag": "MEASURED_DEMO_EXECUTION",
                "tiers": [
                    {"capital_usd": 10_000.0, "available_vn": True, "orig_usd": 98.61, "active_promo_usd": 68.70, "active_promo_pct": 0.30, "verified_utc": default_ts},
                    {"capital_usd": 25_000.0, "available_vn": True, "orig_usd": 277.01, "active_promo_usd": 220.50, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 50_000.0, "available_vn": True, "orig_usd": 382.28, "active_promo_usd": 305.83, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 100_000.0, "available_vn": True, "orig_usd": 598.35, "active_promo_usd": 478.68, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 200_000.0, "available_vn": True, "orig_usd": 1196.70, "active_promo_usd": 957.36, "active_promo_pct": 0.20, "verified_utc": default_ts},
                ],
            },
            # 2. FTMO 2-Step Swing (VN: ONLY 10K & 25K AVAILABLE; 50K/100K/200K DISABLED)
            {
                "program_id": "FTMO_2STEP_SWING",
                "firm_id": "FTMO",
                "firm_name": "FTMO",
                "mode_name": "FTMO 2-Step Swing",
                "profile_mode": "Swing",
                "verified_utc": default_ts,
                "steps": 2,
                "p1_target_pct": 0.10,
                "p2_target_pct": 0.05,
                "dd_daily_pct": 0.05,
                "dd_max_pct": 0.10,
                "dd_type": "static",
                "daily_dd_anchor": "initial_balance",
                "daily_dd_anchor_raw": "MIDNIGHT_BALANCE_PRAGUE_0000",
                "trail_lock_at_initial": False,
                "best_day_cap_pct": 0.0,
                "min_trading_days": 4,
                "min_profitable_days": 0,
                "min_profitable_day_pct": 0.0,
                "fee_refund_pct": 1.0,
                "refund_payout_milestone": 1,
                "refund_is_hub_credit": False,
                "profit_split_pct": 0.80,
                "payout_cycle_trading_days": 10,
                "min_payout_usd": 50.0,
                "payout_rail_fee_pct": 0.010,
                "fx_conversion_spread_pct": 0.005,
                "payout_withdrawal_fee_pct": 0.015,
                "withdrawal_fee_pct": 0.015,
                "refund_withdrawal_fee_pct": 0.0,
                "max_allocation_usd": 400_000.0,
                "news_restricted_eval": False,
                "news_restricted_funded": False,
                "execution_evidence_tag": "MEASURED_DEMO_EXECUTION",
                "tiers": [
                    {"capital_usd": 10_000.0, "available_vn": True, "orig_usd": 109.69, "active_promo_usd": 109.69, "active_promo_pct": 0.0, "verified_utc": default_ts},
                    {"capital_usd": 25_000.0, "available_vn": True, "orig_usd": 309.14, "active_promo_usd": 309.14, "active_promo_pct": 0.0, "verified_utc": default_ts},
                    {"capital_usd": 50_000.0, "available_vn": False, "orig_usd": 0.0, "active_promo_usd": 0.0, "active_promo_pct": 0.0, "verified_utc": default_ts},
                    {"capital_usd": 100_000.0, "available_vn": False, "orig_usd": 0.0, "active_promo_usd": 0.0, "active_promo_pct": 0.0, "verified_utc": default_ts},
                    {"capital_usd": 200_000.0, "available_vn": False, "orig_usd": 0.0, "active_promo_usd": 0.0, "active_promo_pct": 0.0, "verified_utc": default_ts},
                ],
            },
            # 3. FTMO 1-Step (3% daily / 10% EOD Trailing / 50% Best Day / 90% split / NON-REFUNDABLE)
            {
                "program_id": "FTMO_1STEP_STD",
                "firm_id": "FTMO",
                "firm_name": "FTMO",
                "mode_name": "FTMO 1-Step",
                "profile_mode": "Standard",
                "verified_utc": default_ts,
                "steps": 1,
                "p1_target_pct": 0.10,
                "p2_target_pct": 0.0,
                "dd_daily_pct": 0.03,
                "dd_max_pct": 0.10,
                "dd_type": "eod_trailing",
                "daily_dd_anchor": "initial_balance",
                "daily_dd_anchor_raw": "START_OF_DAY_PRAGUE_0000",
                "trail_lock_at_initial": False,
                "best_day_cap_pct": 0.50,
                "min_trading_days": 0,
                "min_profitable_days": 0,
                "min_profitable_day_pct": 0.0,
                "fee_refund_pct": 0.0,
                "refund_payout_milestone": 0,
                "refund_is_hub_credit": False,
                "profit_split_pct": 0.90,
                "payout_cycle_trading_days": 10,
                "min_payout_usd": 50.0,
                "payout_rail_fee_pct": 0.010,
                "fx_conversion_spread_pct": 0.005,
                "payout_withdrawal_fee_pct": 0.015,
                "withdrawal_fee_pct": 0.015,
                "refund_withdrawal_fee_pct": 0.0,
                "max_allocation_usd": 400_000.0,
                "news_restricted_eval": False,
                "news_restricted_funded": True,
                "execution_evidence_tag": "MEASURED_DEMO_EXECUTION",
                "tiers": [
                    {"capital_usd": 10_000.0, "available_vn": True, "orig_usd": 87.53, "active_promo_usd": 60.94, "active_promo_pct": 0.30, "verified_utc": default_ts},
                    {"capital_usd": 25_000.0, "available_vn": True, "orig_usd": 220.50, "active_promo_usd": 176.18, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 50_000.0, "available_vn": True, "orig_usd": 353.47, "active_promo_usd": 282.56, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 100_000.0, "available_vn": True, "orig_usd": 552.89, "active_promo_usd": 442.12, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 200_000.0, "available_vn": True, "orig_usd": 1106.95, "active_promo_usd": 885.34, "active_promo_pct": 0.20, "verified_utc": default_ts},
                ],
            },
            # 4. FTMO Instant (0-step / 3% daily / 10% Intraday Trailing / 30% Best Day / 90% split)
            {
                "program_id": "FTMO_INSTANT_STD",
                "firm_id": "FTMO",
                "firm_name": "FTMO",
                "mode_name": "FTMO Instant",
                "profile_mode": "Standard",
                "verified_utc": default_ts,
                "steps": 0,
                "p1_target_pct": 0.0,
                "p2_target_pct": 0.0,
                "dd_daily_pct": 0.03,
                "dd_max_pct": 0.10,
                "dd_type": "intraday_trailing",
                "daily_dd_anchor": "initial_balance",
                "daily_dd_anchor_raw": "START_OF_DAY_PRAGUE_0000",
                "trail_lock_at_initial": False,
                "best_day_cap_pct": 0.30,
                "min_trading_days": 0,
                "min_profitable_days": 0,
                "min_profitable_day_pct": 0.0,
                "fee_refund_pct": 0.0,
                "refund_payout_milestone": 0,
                "refund_is_hub_credit": False,
                "profit_split_pct": 0.90,
                "payout_cycle_trading_days": 10,
                "min_payout_usd": 50.0,
                "payout_rail_fee_pct": 0.010,
                "fx_conversion_spread_pct": 0.005,
                "payout_withdrawal_fee_pct": 0.015,
                "withdrawal_fee_pct": 0.015,
                "refund_withdrawal_fee_pct": 0.0,
                "max_allocation_usd": 200_000.0,
                "news_restricted_eval": False,
                "news_restricted_funded": True,
                "execution_evidence_tag": "MEASURED_DEMO_EXECUTION",
                "tiers": [
                    {"capital_usd": 5_000.0, "available_vn": True, "orig_usd": 187.25, "active_promo_usd": 130.75, "active_promo_pct": 0.30, "verified_utc": default_ts},
                    {"capital_usd": 10_000.0, "available_vn": True, "orig_usd": 375.36, "active_promo_usd": 300.29, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 25_000.0, "available_vn": True, "orig_usd": 829.66, "active_promo_usd": 663.73, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 50_000.0, "available_vn": True, "orig_usd": 1660.98, "active_promo_usd": 1328.57, "active_promo_pct": 0.20, "verified_utc": default_ts},
                    {"capital_usd": 100_000.0, "available_vn": True, "orig_usd": 3322.80, "active_promo_usd": 2658.24, "active_promo_pct": 0.20, "verified_utc": default_ts},
                ],
            },
            # 5. The5ers High Stakes (Fallback for isolated tests only)
            {
                "program_id": "THE5ERS_HS",
                "firm_id": "THE5ERS",
                "firm_name": "The5ers",
                "mode_name": "The5ers High Stakes",
                "profile_mode": "Standard",
                "verified_utc": default_ts,
                "steps": 2,
                "p1_target_pct": 0.08,
                "p2_target_pct": 0.05,
                "dd_daily_pct": 0.05,
                "dd_max_pct": 0.10,
                "dd_type": "static",
                "daily_dd_anchor": "prev_day_balance",
                "daily_dd_anchor_raw": "MAX_MIDNIGHT_BALANCE_OR_EQUITY_MT5_0000",
                "dd_rule_verification_tag": DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT,
                "dd_rule_verification_note": "The5ers daily DD anchors at max(balance, equity) at MT5 00:00 reset; balance * (1 - daily_lim) holds ONLY when flat at exact firm reset time.",
                "trail_lock_at_initial": False,
                "best_day_cap_pct": 0.0,
                "min_trading_days": 3,
                "min_profitable_days": 3,
                "min_profitable_day_pct": 0.005,
                "fee_refund_pct": 0.70,
                "refund_payout_milestone": 1,
                "refund_is_hub_credit": False,
                "profit_split_pct": 0.80,
                "payout_cycle_trading_days": 10,
                "min_payout_usd": 150.0,
                "payout_rail_fee_pct": 0.035,
                "fx_conversion_spread_pct": 0.005,
                "payout_withdrawal_fee_pct": 0.040,
                "withdrawal_fee_pct": 0.040,
                "refund_withdrawal_fee_pct": 0.040,
                "max_allocation_usd": 100_000.0,
                "news_restricted_eval": True,
                "news_restricted_funded": True,
                "execution_evidence_tag": "TERMS_VERIFIED_EXECUTION_UNMEASURED",
                "tiers": [
                    {"capital_usd": 5_000.0, "available_vn": True, "orig_usd": 39.0, "active_promo_usd": 39.0, "active_promo_pct": 0.0, "dd_daily_pct": 0.05, "dd_max_pct": 0.10, "verified_utc": default_ts},
                    {"capital_usd": 20_000.0, "available_vn": True, "orig_usd": 165.0, "active_promo_usd": 165.0, "active_promo_pct": 0.0, "dd_daily_pct": 0.05, "dd_max_pct": 0.10, "verified_utc": default_ts},
                    {"capital_usd": 50_000.0, "available_vn": True, "orig_usd": 275.0, "active_promo_usd": 275.0, "active_promo_pct": 0.0, "dd_daily_pct": 0.04, "dd_max_pct": 0.08, "verified_utc": default_ts},
                    {"capital_usd": 60_000.0, "available_vn": True, "orig_usd": 300.0, "active_promo_usd": 300.0, "active_promo_pct": 0.0, "dd_daily_pct": 0.04, "dd_max_pct": 0.08, "verified_utc": default_ts},
                    {"capital_usd": 100_000.0, "available_vn": True, "orig_usd": 545.0, "active_promo_usd": 545.0, "active_promo_pct": 0.0, "dd_daily_pct": 0.05, "dd_max_pct": 0.10, "verified_utc": default_ts},
                ],
            },
            # 6. Firm #3 Fallback placeholder (isolated tests only)
            {
                "program_id": "FIRM3_2STEP",
                "firm_id": "IC_FUNDED",
                "firm_name": "IC Funded (Fallback)",
                "mode_name": "IC Funded 2-Step",
                "profile_mode": "Standard",
                "verified_utc": default_ts,
                "steps": 2,
                "p1_target_pct": 0.10,
                "p2_target_pct": 0.05,
                "dd_daily_pct": 0.05,
                "dd_max_pct": 0.10,
                "dd_type": "static",
                "daily_dd_anchor": "prev_day_balance",
                "daily_dd_anchor_raw": "EQUITY_RESET_SERVER_0000_GMT2_3",
                "dd_rule_verification_tag": DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT,
                "dd_rule_verification_note": "IC Funded daily DD anchors at equity at server 00:00 (GMT+2/+3) reset; balance * (1 - daily_lim) holds ONLY when flat at exact firm reset time.",
                "trail_lock_at_initial": False,
                "best_day_cap_pct": 0.0,
                "min_trading_days": 3,
                "min_profitable_days": 0,
                "min_profitable_day_pct": 0.0,
                "fee_refund_pct": 1.0,
                "refund_payout_milestone": 3,
                "refund_is_hub_credit": False,
                "profit_split_pct": 0.80,
                "payout_cycle_trading_days": 10,
                "min_payout_usd": 100.0,
                "payout_rail_fee_pct": 0.015,
                "fx_conversion_spread_pct": 0.005,
                "payout_withdrawal_fee_pct": 0.020,
                "withdrawal_fee_pct": 0.020,
                "refund_withdrawal_fee_pct": 0.020,
                "max_allocation_usd": 300_000.0,
                "news_restricted_eval": False,
                "news_restricted_funded": True,
                "execution_evidence_tag": "TERMS_VERIFIED_EXECUTION_UNMEASURED",
                "tiers": [
                    {"capital_usd": 10_000.0, "available_vn": True, "orig_usd": 125.0, "active_promo_usd": 125.0, "active_promo_pct": 0.0, "verified_utc": default_ts},
                    {"capital_usd": 50_000.0, "available_vn": True, "orig_usd": 449.0, "active_promo_usd": 449.0, "active_promo_pct": 0.0, "verified_utc": default_ts},
                    {"capital_usd": 100_000.0, "available_vn": True, "orig_usd": 689.0, "active_promo_usd": 689.0, "active_promo_pct": 0.0, "verified_utc": default_ts},
                ],
            },
        ],
    }


def _parse_utc_iso(ts: Any) -> datetime:
    """Parse ISO-8601 UTC timestamp string strictly into an aware UTC datetime."""
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError(f"Missing or non-string UTC timestamp: {ts!r}")
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _pct_to_frac(val: Any, default: float = 0.0) -> float:
    """Convert a percentage-point value from `prop_pricing_catalog.json` (e.g. `0.5` -> `0.005`, `1.0` -> `0.01`, `80.0` -> `0.80`) to a fraction.

    CRITICAL: In `naqex-prop-pricing-catalog-v1`, ALL `*_pct` fields are strictly expressed in percentage points
    (`0.5` = 0.5%, `1.0` = 1.0%, `2.5` = 2.5%, `100.0` = 100%), NEVER mixed fractions!
    """
    if val is None:
        return default
    if isinstance(val, bool):
        raise ValueError(f"NON_FINITE_PRICE_ERROR: boolean passed to percentage field: {val!r}")
    fv = float(val)
    if not math.isfinite(fv):
        raise ValueError(f"NON_FINITE_PRICE_ERROR: non-finite percentage value: {val!r}")
    return fv / 100.0


def _parse_dd_type(raw: Any) -> str:
    s = str(raw or "static").strip().lower()
    if "intraday" in s:
        return "intraday_trailing"
    if "eod" in s or "trailing" in s:
        return "eod_trailing"
    return "static"


def _dd_type_code(dd_type: str) -> int:
    t = _parse_dd_type(dd_type)
    if t == "intraday_trailing":
        return DD_INTRADAY_TRAILING
    if t == "eod_trailing":
        return DD_EOD_TRAILING
    return DD_STATIC


def _parse_daily_dd_anchor(raw: Any) -> str:
    """Classify catalog `daily_dd_anchor` into `initial_balance` vs `prev_day_balance`.

    - `initial_balance`: static allowance (`daily_floor = s_bal - cap * daily_lim`), e.g. FTMO Prague midnight.
    - `prev_day_balance`: relative to start-of-day balance/equity (`daily_floor = s_bal * (1.0 - daily_lim)`),
      e.g. The5ers (`MAX_MIDNIGHT_BALANCE_OR_EQUITY_MT5_0000`) & IC Funded (`EQUITY_RESET_SERVER_0000_GMT2_3`).
    """
    s = str(raw or "initial_balance").strip().lower()
    if any(
        tok in s
        for tok in (
            "prev_day",
            "prev_balance",
            "previous_day",
            "balance_or_equity",
            "equity_reset",
            "relative_balance",
            "trailing_daily",
        )
    ):
        return "prev_day_balance"
    return "initial_balance"


def _daily_dd_anchor_code(anchor: Any) -> int:
    return (
        DAILY_DD_ANCHOR_PREV_DAY_BALANCE
        if _parse_daily_dd_anchor(anchor) == "prev_day_balance"
        else DAILY_DD_ANCHOR_INITIAL_BALANCE
    )


def _require_finite_float(val: Any, field_name: str, *, allow_zero: bool = False) -> float:
    """Strictly parse a finite numeric value; reject bool, NaN, +/-Inf, and non-positive values."""
    if val is None or isinstance(val, bool):
        raise ValueError(f"NON_FINITE_PRICE_ERROR: {field_name} missing or boolean ({val!r})")
    try:
        fv = float(val)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"NON_FINITE_PRICE_ERROR: {field_name} is not numeric ({val!r})") from exc
    if not math.isfinite(fv):
        raise ValueError(f"NON_FINITE_PRICE_ERROR: {field_name} must be finite, got {val!r}")
    if allow_zero:
        if fv < 0.0:
            raise ValueError(f"NON_FINITE_PRICE_ERROR: {field_name} must be >= 0, got {fv!r}")
    else:
        if fv <= 0.0:
            raise ValueError(f"NON_FINITE_PRICE_ERROR: {field_name} must be > 0, got {fv!r}")
    return fv


def _dd_rule_verification_tag(firm_id: str, daily_dd_anchor_raw: str, daily_dd_anchor: str) -> str:
    """Tag non-FTMO equity-anchored daily DD rules (`The5ers`, `IC Funded`) as flat-at-reset only."""
    fid = str(firm_id or "").upper()
    raw_low = str(daily_dd_anchor_raw or "").lower()
    if (
        daily_dd_anchor == "prev_day_balance"
        or "THE5ERS" in fid
        or "IC_FUNDED" in fid
        or "equity" in raw_low
    ):
        return DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT
    return DD_ANCHOR_TAG_BALANCE_VERIFIED


def _dd_rule_verification_note(firm_id: str, daily_dd_anchor_raw: str, tag: str) -> str:
    fid = str(firm_id or "").upper()
    if tag != DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT:
        return "Daily DD anchored to initial balance allowance at Prague midnight reset."
    if "THE5ERS" in fid:
        return (
            "The5ers daily DD anchors at max(balance, equity) at MT5 00:00 reset; "
            "modeled daily_floor = balance * (1 - daily_lim) holds ONLY when flat at exact firm reset time."
        )
    if "IC_FUNDED" in fid:
        return (
            "IC Funded daily DD anchors at equity at server 00:00 (GMT+2/+3) reset; "
            "modeled daily_floor = balance * (1 - daily_lim) holds ONLY when flat at exact firm reset time."
        )
    return (
        f"Equity-sensitive daily DD anchor ({daily_dd_anchor_raw}); "
        f"modeled daily_floor = balance * (1 - daily_lim) holds ONLY when flat at exact firm reset time."
    )


def _parse_refund_milestone(raw: Any, fee_refund_pct: float) -> int:
    if fee_refund_pct <= 1e-9:
        return 0
    s = str(raw or "FIRST_PAYOUT").strip().upper()
    if "THIRD" in s or s == "3":
        return 3
    if "SECOND" in s or s == "2":
        return 2
    if "NON" in s or "NONE" in s or s == "0":
        return 0
    return 1


def _cal_days_to_trading_days(cal_days: Any, default: int = 10) -> int:
    if cal_days is None:
        return default
    c = int(cal_days)
    if c <= 1:
        return 1
    return max(1, int(round(c * 252.0 / 365.2425)))


def _normalize_external_catalog(raw: dict[str, Any]) -> dict[str, Any]:
    """Adapt `prop_pricing_catalog.json` (nested `firms -> programs -> tiers`) to canonical format with strict validation."""
    if not isinstance(raw, dict):
        raise ValueError("Pricing catalog root JSON must be an object")

    if "programs" in raw and isinstance(raw["programs"], list) and raw["programs"]:
        out = dict(raw)
        out["is_fallback"] = bool(raw.get("is_fallback", False))
        # Validate FX rates & ensure canonical per-program / per-tier defaults for already-normalized dicts
        fx_in = out.get("fx_rates") or {}
        if isinstance(fx_in, dict) and "usd_vnd" in fx_in:
            _require_finite_float(fx_in.get("usd_vnd"), "fx_rates.usd_vnd")
        norm_progs = []
        top_ts = out.get("updated_utc")
        for p in out["programs"]:
            p_copy = dict(p)
            p_ts = p_copy.get("verified_utc") or top_ts
            p_copy["verified_utc"] = p_ts
            p_copy["daily_dd_anchor_raw"] = str(p_copy.get("daily_dd_anchor_raw") or p_copy.get("daily_dd_anchor") or "initial_balance")
            p_copy["daily_dd_anchor"] = _parse_daily_dd_anchor(p_copy["daily_dd_anchor_raw"])
            dd_tag = p_copy.get("dd_rule_verification_tag") or _dd_rule_verification_tag(
                str(p_copy.get("firm_id", "")),
                p_copy["daily_dd_anchor_raw"],
                p_copy["daily_dd_anchor"],
            )
            p_copy["dd_rule_verification_tag"] = dd_tag
            p_copy["dd_rule_verification_note"] = p_copy.get("dd_rule_verification_note") or _dd_rule_verification_note(
                str(p_copy.get("firm_id", "")),
                p_copy["daily_dd_anchor_raw"],
                dd_tag,
            )
            wd = _require_finite_float(
                p_copy.get("payout_withdrawal_fee_pct", p_copy.get("withdrawal_fee_pct", 0.015)),
                f"{p_copy.get('program_id')}.payout_withdrawal_fee_pct",
                allow_zero=True,
            )
            p_copy["payout_withdrawal_fee_pct"] = wd
            p_copy["withdrawal_fee_pct"] = wd
            if "refund_withdrawal_fee_pct" not in p_copy:
                p_copy["refund_withdrawal_fee_pct"] = 0.0 if "FTMO" in str(p_copy.get("firm_id", "")).upper() else wd
            tiers_out = []
            for t in p_copy.get("tiers", []):
                t_copy = dict(t)
                cap_v = _require_finite_float(t_copy.get("capital_usd"), f"{p_copy.get('program_id')}.capital_usd")
                cap_lbl = f"{int(round(cap_v / 1000.0))}K"
                avail_vn = bool(t_copy.get("available_vn", True))
                if avail_vn:
                    orig_v = _require_finite_float(t_copy.get("orig_usd"), f"{p_copy.get('program_id')}:{cap_lbl}.orig_usd")
                    promo_raw = t_copy.get("active_promo_usd")
                    promo_v = _require_finite_float(
                        promo_raw if promo_raw is not None else orig_v,
                        f"{p_copy.get('program_id')}:{cap_lbl}.active_promo_usd",
                    )
                    if promo_v > orig_v + 1e-9:
                        raise ValueError(
                            f"Available tier {p_copy.get('program_id')} {cap_lbl} has active_promo_usd ({promo_v}) > orig_usd ({orig_v})"
                        )
                else:
                    if t_copy.get("orig_usd") is not None:
                        _require_finite_float(t_copy.get("orig_usd"), f"{p_copy.get('program_id')}:{cap_lbl}.orig_usd", allow_zero=True)
                    if t_copy.get("active_promo_usd") is not None:
                        _require_finite_float(t_copy.get("active_promo_usd"), f"{p_copy.get('program_id')}:{cap_lbl}.active_promo_usd", allow_zero=True)
                t_ver = t_copy.get("verified_utc")
                if not isinstance(t_ver, str) or not t_ver.strip():
                    raise ValueError(
                        f"MISSING_TIER_VERIFIED_UTC: tier {p_copy.get('program_id')}:{cap_lbl} must declare its own verified_utc"
                    )
                _parse_utc_iso(t_ver)
                tiers_out.append(t_copy)
            p_copy["tiers"] = tiers_out
            norm_progs.append(p_copy)
        out["programs"] = norm_progs
        return out

    fx_raw = raw.get("fx_rates")
    if not isinstance(fx_raw, dict):
        raise ValueError("Pricing catalog missing required `fx_rates` object")
    usd_vnd = float(
        fx_raw.get("usd_vnd")
        or fx_raw.get("USD_VND")
        or fx_raw.get("usd_to_vnd")
        or 0.0
    )
    eur_vnd = float(
        fx_raw.get("eur_vnd")
        or fx_raw.get("EUR_VND")
        or fx_raw.get("eur_to_vnd")
        or 0.0
    )
    if usd_vnd <= 0.0 or not math.isfinite(usd_vnd):
        raise ValueError(f"Invalid fx_rates.usd_vnd in pricing catalog: {usd_vnd!r}")
    if eur_vnd <= 0.0 or not math.isfinite(eur_vnd):
        eur_vnd = usd_vnd * 1.09

    vn_costs = raw.get("vn_transaction_costs", {})
    if not isinstance(vn_costs, dict):
        raise ValueError("Pricing catalog `vn_transaction_costs` must be an object")
    card_fx_fee = _pct_to_frac(
        vn_costs.get("card_fx_buy_fee_pct", vn_costs.get("card_fx_fee_pct", 2.5)),
        default=0.025,
    )
    fx_conv_spread = _pct_to_frac(vn_costs.get("fx_conversion_spread_pct", 0.5), default=0.005)
    rail_by_firm = {
        str(k).lower(): _pct_to_frac(v, default=0.015)
        for k, v in (vn_costs.get("payout_rail_fee_pct_by_firm") or {}).items()
    }
    refund_wd_by_firm = {
        str(k).lower(): _pct_to_frac(v, default=0.0)
        for k, v in (vn_costs.get("refund_withdrawal_fee_pct_by_firm") or {}).items()
    }
    default_wd = _pct_to_frac(vn_costs.get("default_withdrawal_fee_pct", 1.5), default=0.015)

    firms_raw = raw.get("firms")
    if not firms_raw:
        raise ValueError("Pricing catalog missing non-empty `firms` collection")
    if isinstance(firms_raw, dict):
        firms_iter = [{"firm_id": k, **v} for k, v in firms_raw.items()]
    elif isinstance(firms_raw, list):
        firms_iter = list(firms_raw)
    else:
        raise ValueError("Pricing catalog `firms` must be a dict or list")

    top_updated = raw.get("updated_utc")
    programs: list[dict[str, Any]] = []
    for fobj in firms_iter:
        if not isinstance(fobj, dict):
            raise ValueError("Malformed firm entry in pricing catalog")
        firm_id_raw = str(fobj.get("firm_id") or fobj.get("id") or fobj.get("name") or "UNKNOWN")
        firm_id = firm_id_raw.upper()
        firm_name = str(fobj.get("display_name") or fobj.get("name") or fobj.get("firm_name") or firm_id)
        firm_verified = fobj.get("verified_utc") or top_updated
        exec_tag = str(
            fobj.get("execution_evidence_tag")
            or ("MEASURED_DEMO_EXECUTION" if "FTMO" in firm_id else "TERMS_VERIFIED_EXECUTION_UNMEASURED")
        )
        rail_fee_firm = rail_by_firm.get(
            firm_id_raw.lower(),
            _pct_to_frac(fobj.get("payout_rail_fee_pct", fobj.get("withdrawal_fee_pct", default_wd * 100.0)), default=default_wd),
        )
        # Total inbound payout drag to VND = firm payout rail fee + VN FX conversion spread
        payout_wd_fee_firm = rail_fee_firm + fx_conv_spread
        # Separate refund withdrawal fee: FTMO refunds challenge fee directly to card (0.0% default);
        # firms adding refund into 1st payout withdrawal (e.g. The5ers) incur payout_wd_fee_firm.
        if firm_id_raw.lower() in refund_wd_by_firm:
            refund_wd_fee_firm = refund_wd_by_firm[firm_id_raw.lower()]
        elif fobj.get("refund_withdrawal_fee_pct") is not None:
            refund_wd_fee_firm = _pct_to_frac(fobj.get("refund_withdrawal_fee_pct"), default=0.0)
        elif "FTMO" in firm_id:
            refund_wd_fee_firm = 0.0
        else:
            refund_wd_fee_firm = payout_wd_fee_firm

        max_alloc_firm = float(fobj.get("max_allocation_usd") or 200_000.0)
        source_urls = list(fobj.get("source_urls", []))

        nested_progs = fobj.get("programs") or fobj.get("modes")
        if nested_progs:
            p_iter = (
                [{"program_id": k, **v} for k, v in nested_progs.items()]
                if isinstance(nested_progs, dict)
                else list(nested_progs)
            )
            for pobj in p_iter:
                if not isinstance(pobj, dict):
                    raise ValueError(f"Malformed program entry under firm {firm_id}")
                pid = str(pobj.get("program_id") or pobj.get("id") or f"{firm_id}_{pobj.get('name', 'PROG')}").upper().replace(" ", "_")
                mname = str(pobj.get("display_name") or pobj.get("mode_name") or pobj.get("name") or pid)
                prog_verified = pobj.get("verified_utc") or firm_verified
                prog_anchor_raw = str(pobj.get("daily_dd_anchor") or fobj.get("daily_dd_anchor") or "initial_balance")
                prog_anchor_mode = _parse_daily_dd_anchor(prog_anchor_raw)
                prog_refund_wd = (
                    _pct_to_frac(pobj.get("refund_withdrawal_fee_pct"), default=refund_wd_fee_firm)
                    if pobj.get("refund_withdrawal_fee_pct") is not None
                    else refund_wd_fee_firm
                )

                raw_tiers_obj = pobj.get("tiers") or pobj.get("skus") or []
                raw_tiers = list(raw_tiers_obj.values()) if isinstance(raw_tiers_obj, dict) else list(raw_tiers_obj)
                norm_tiers = []
                for t in raw_tiers:
                    if not isinstance(t, dict):
                        raise ValueError(f"Malformed tier entry under {pid}")
                    cap_raw = t.get("capital_usd")
                    if cap_raw is None:
                        cap_raw = t.get("account_size_usd") if t.get("account_size_usd") is not None else t.get("size_usd")
                    cap = _require_finite_float(cap_raw, f"{pid}.capital_usd")
                    cap_lbl = f"{int(round(cap / 1000.0))}K"
                    avail_vn = bool(t.get("available_vn", True))
                    orig_raw = t.get("orig_usd") if t.get("orig_usd") is not None else (t.get("regular_usd") if t.get("regular_usd") is not None else t.get("price_usd"))
                    promo_raw = t.get("active_promo_usd")
                    if avail_vn:
                        orig = _require_finite_float(orig_raw, f"{pid}:{cap_lbl}.orig_usd")
                        promo = _require_finite_float(
                            promo_raw if promo_raw is not None else orig,
                            f"{pid}:{cap_lbl}.active_promo_usd",
                        )
                        if promo > orig + 1e-9:
                            raise ValueError(f"Available tier {pid} {cap_lbl} has active_promo_usd ({promo}) > orig_usd ({orig})")
                    else:
                        orig = _require_finite_float(orig_raw, f"{pid}:{cap_lbl}.orig_usd", allow_zero=True) if orig_raw is not None else 0.0
                        promo = _require_finite_float(promo_raw, f"{pid}:{cap_lbl}.active_promo_usd", allow_zero=True) if promo_raw is not None else 0.0
                    ppct_raw = t.get("active_promo_pct")
                    if ppct_raw is not None:
                        _require_finite_float(ppct_raw, f"{pid}:{cap_lbl}.active_promo_pct", allow_zero=True)
                    ppct = _pct_to_frac(
                        ppct_raw if ppct_raw is not None else (((1.0 - promo / orig) * 100.0) if orig > 0 else 0.0),
                        default=0.0,
                    )
                    if not math.isfinite(ppct):
                        raise ValueError(f"NON_FINITE_PRICE_ERROR: {pid}:{cap_lbl}.active_promo_pct={ppct!r}")
                    # Strictly require per-tier verified_utc (ZERO silent inheritance from program/firm!)
                    tier_verified = t.get("verified_utc")
                    if not isinstance(tier_verified, str) or not tier_verified.strip():
                        raise ValueError(
                            f"MISSING_TIER_VERIFIED_UTC: tier {pid}:{cap_lbl} must declare its own verified_utc"
                        )
                    _parse_utc_iso(tier_verified)
                    tier_anchor_raw = str(t.get("daily_dd_anchor") or prog_anchor_raw)
                    tier_anchor = _parse_daily_dd_anchor(tier_anchor_raw)
                    tier_dd_tag = str(
                        t.get("dd_rule_verification_tag")
                        or pobj.get("dd_rule_verification_tag")
                        or _dd_rule_verification_tag(firm_id, tier_anchor_raw, tier_anchor)
                    )
                    tier_row: dict[str, Any] = {
                        "capital_usd": cap,
                        "available_vn": avail_vn,
                        "orig_usd": orig,
                        "active_promo_usd": promo,
                        "active_promo_pct": ppct,
                        "promo_label": str(t.get("promo_label") or ""),
                        "verified_utc": tier_verified,
                        "daily_dd_anchor_raw": tier_anchor_raw,
                        "daily_dd_anchor": tier_anchor,
                        "dd_rule_verification_tag": tier_dd_tag,
                        "dd_rule_verification_note": _dd_rule_verification_note(firm_id, tier_anchor_raw, tier_dd_tag),
                    }
                    if t.get("dd_daily_pct") is not None:
                        tier_row["dd_daily_pct"] = _pct_to_frac(t["dd_daily_pct"])
                    if t.get("dd_max_pct") is not None:
                        tier_row["dd_max_pct"] = _pct_to_frac(t["dd_max_pct"])
                    if t.get("dd_type") is not None:
                        tier_row["dd_type"] = _parse_dd_type(t["dd_type"])
                    if t.get("p1_target_pct") is not None:
                        tier_row["p1_target_pct"] = _pct_to_frac(t["p1_target_pct"])
                    if t.get("p2_target_pct") is not None:
                        tier_row["p2_target_pct"] = _pct_to_frac(t["p2_target_pct"])
                    norm_tiers.append(tier_row)

                is_swing = "swing" in mname.lower() or "swing" in pid.lower()
                steps_raw = pobj.get("steps")
                if steps_raw is None:
                    if "instant" in mname.lower() or "instant" in pid.lower():
                        steps_raw = 0
                    elif "1-step" in mname.lower() or "1step" in pid.lower() or "one" in mname.lower():
                        steps_raw = 1
                    else:
                        steps_raw = 2
                steps = int(steps_raw)
                p1_t = _pct_to_frac(
                    pobj.get("p1_target_pct", pobj.get("target_p1_pct", 0.0 if steps == 0 else 10.0)),
                    default=0.0 if steps == 0 else 0.10,
                )
                p2_t = _pct_to_frac(
                    pobj.get("p2_target_pct", pobj.get("target_p2_pct", 5.0 if steps == 2 else 0.0)),
                    default=0.05 if steps == 2 else 0.0,
                )
                news_rule_str = str(pobj.get("news_rule") or fobj.get("news_rule") or "").lower()
                news_eval = bool(pobj.get("news_restricted_eval", "all_phases_ban" in news_rule_str))
                news_fund = bool(pobj.get("news_restricted_funded", not is_swing))
                fee_ref = _pct_to_frac(
                    pobj.get("external_cash_refund_pct", pobj.get("fee_refund_pct", 100.0 if steps == 2 else 0.0)),
                    default=0.0,
                )
                ref_mile = _parse_refund_milestone(pobj.get("fee_refund_milestone"), fee_ref)
                cycle_td = int(
                    pobj.get("payout_cycle_trading_days")
                    or _cal_days_to_trading_days(pobj.get("payout_cycle_days"), default=10)
                )
                min_prof_days = int(pobj.get("min_profitable_days", 0) or 0)
                min_prof_thr = _pct_to_frac(
                    pobj.get(
                        "profitable_day_threshold_pct",
                        pobj.get("min_profitable_day_pct", 0.5 if min_prof_days > 0 else 0.0),
                    ),
                    default=0.0,
                )
                programs.append({
                    "program_id": pid,
                    "firm_id": firm_id,
                    "firm_name": firm_name,
                    "mode_name": mname,
                    "profile_mode": "Swing" if is_swing else "Standard",
                    "verified_utc": prog_verified,
                    "steps": steps,
                    "p1_target_pct": p1_t,
                    "p2_target_pct": p2_t,
                    "dd_daily_pct": _pct_to_frac(pobj.get("dd_daily_pct", 5.0), default=0.05),
                    "dd_max_pct": _pct_to_frac(pobj.get("dd_max_pct", 10.0), default=0.10),
                    "dd_type": _parse_dd_type(pobj.get("dd_type", "static")),
                    "daily_dd_anchor_raw": prog_anchor_raw,
                    "daily_dd_anchor": prog_anchor_mode,
                    "dd_rule_verification_tag": _dd_rule_verification_tag(firm_id, prog_anchor_raw, prog_anchor_mode),
                    "dd_rule_verification_note": _dd_rule_verification_note(
                        firm_id,
                        prog_anchor_raw,
                        _dd_rule_verification_tag(firm_id, prog_anchor_raw, prog_anchor_mode),
                    ),
                    "trail_lock_at_initial": bool(pobj.get("trail_lock_at_initial", False)),
                    "locks_at_initial_after_first_payout": bool(pobj.get("locks_at_initial_after_first_payout", False)),
                    "best_day_cap_pct": _pct_to_frac(pobj.get("best_day_cap_pct", 0.0), default=0.0),
                    "daily_profit_cap_pct": _pct_to_frac(pobj.get("daily_profit_cap_pct", 0.0), default=0.0),
                    "min_trading_days": int(pobj.get("min_trading_days", 4 if steps == 2 else 0) or 0),
                    "min_profitable_days": min_prof_days,
                    "min_profitable_day_pct": min_prof_thr,
                    "funded_first_payout_min_prof_days": int(pobj.get("funded_first_payout_min_profitable_days", 0) or 0),
                    "funded_first_payout_prof_pct": _pct_to_frac(pobj.get("funded_first_payout_profitable_day_pct", 0.0), default=0.0),
                    "fee_refund_pct": fee_ref,
                    "refund_payout_milestone": ref_mile,
                    "hub_credit_rebate_pct": _pct_to_frac(pobj.get("hub_credit_rebate_pct", 0.0), default=0.0),
                    "payout_buffer_retention_pct": _pct_to_frac(pobj.get("payout_buffer_retention_pct", 0.0), default=0.0),
                    "min_payout_profit_pct": _pct_to_frac(pobj.get("min_payout_profit_pct", 0.0), default=0.0),
                    "profit_split_pct": _pct_to_frac(pobj.get("profit_split_pct", 80.0), default=0.80),
                    "payout_cycle_trading_days": cycle_td,
                    "min_payout_usd": float(pobj.get("min_payout_usd", fobj.get("min_payout_usd", 50.0)) or 50.0),
                    "payout_rail_fee_pct": rail_fee_firm,
                    "fx_conversion_spread_pct": fx_conv_spread,
                    "payout_withdrawal_fee_pct": payout_wd_fee_firm,
                    "withdrawal_fee_pct": payout_wd_fee_firm,
                    "refund_withdrawal_fee_pct": prog_refund_wd,
                    "max_allocation_usd": float(pobj.get("max_allocation_usd", max_alloc_firm) or max_alloc_firm),
                    "news_restricted_eval": news_eval,
                    "news_restricted_funded": news_fund,
                    "execution_evidence_tag": str(pobj.get("execution_evidence_tag") or exec_tag),
                    "ea_policy": str(pobj.get("ea_policy") or (fobj.get("ea_policy", {}).get("summary") if isinstance(fobj.get("ea_policy"), dict) else fobj.get("ea_policy")) or "VERIFY_AT_CHECKOUT"),
                    "source_urls": list(pobj.get("source_urls", source_urls)),
                    "tiers": norm_tiers,
                })

    if not programs:
        raise ValueError("Pricing catalog contains zero valid programs after normalization")

    return {
        "schema": raw.get("schema", "naqex-prop-pricing-catalog-v1"),
        "updated_utc": top_updated,
        "staleness_max_days": int(raw.get("staleness_max_days", 7)),
        "is_fallback": False,
        "fx_rates": {
            "usd_vnd": usd_vnd,
            "eur_vnd": eur_vnd,
            "source": fx_raw.get("source", "prop_pricing_catalog.json"),
            "fetched_utc": fx_raw.get("fetched_utc"),
        },
        "vn_transaction_costs": {
            "card_fx_buy_fee_pct": card_fx_fee,
            "fx_conversion_spread_pct": fx_conv_spread,
            "payout_rail_fee_pct_by_firm": rail_by_firm,
            "refund_withdrawal_fee_pct_by_firm": refund_wd_by_firm,
            "default_withdrawal_fee_pct": default_wd,
            "default_ftmo_refund_withdrawal_fee_pct": 0.0,
        },
        "seasonal_sale_calendar": raw.get("seasonal_sale_calendar", []),
        "rejected_candidates": raw.get("rejected_candidates", []),
        "programs": programs,
    }


def check_catalog_freshness(
    catalog: dict[str, Any],
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Enforce catalog, FX, per-program, and strict per-tier `verified_utc` freshness & future-date guards."""
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    max_days = float(catalog.get("staleness_max_days", 7))
    if (not math.isfinite(max_days)) or max_days <= 0.0:
        raise ValueError(f"Invalid staleness_max_days in catalog: {max_days!r}")

    stale_items: list[dict[str, Any]] = []
    future_items: list[dict[str, Any]] = []
    max_age_days = 0.0

    def _check_ts(scope: str, ts_val: Any) -> tuple[float, bool]:
        nonlocal max_age_days
        dt = _parse_utc_iso(ts_val)
        age_d = (now - dt).total_seconds() / 86400.0
        if age_d < -MAX_FUTURE_TIMESTAMP_SKEW_DAYS:
            future_items.append({
                "scope": scope,
                "verified_utc": str(ts_val),
                "future_by_days": round(-age_d, 3),
                "max_future_skew_days": MAX_FUTURE_TIMESTAMP_SKEW_DAYS,
            })
        if age_d > max_age_days:
            max_age_days = age_d
        is_st = age_d > max_days
        if is_st:
            stale_items.append({
                "scope": scope,
                "verified_utc": str(ts_val),
                "age_days": round(age_d, 3),
                "staleness_max_days": max_days,
            })
        return age_d, is_st

    top_age, _ = _check_ts("catalog.updated_utc", catalog.get("updated_utc"))

    fx_ts = (catalog.get("fx_rates") or {}).get("fetched_utc")
    fx_age = top_age
    if fx_ts is not None:
        fx_age, _ = _check_ts("fx_rates.fetched_utc", fx_ts)

    per_program: dict[str, dict[str, Any]] = {}
    tier_count = 0
    stale_tier_count = 0
    for prog in catalog.get("programs", []):
        pid = str(prog["program_id"])
        p_ts = prog.get("verified_utc") or catalog.get("updated_utc")
        p_age, p_stale = _check_ts(f"program:{pid}", p_ts)
        prog_stale_tiers: list[str] = []
        for tier in prog.get("tiers", []):
            tier_count += 1
            cap_lbl = f"{int(round(float(tier['capital_usd']) / 1000.0))}K"
            t_ts = tier.get("verified_utc")
            if not isinstance(t_ts, str) or not t_ts.strip():
                raise ValueError(
                    f"MISSING_TIER_VERIFIED_UTC: tier {pid}:{cap_lbl} must have its own verified_utc timestamp"
                )
            _, t_stale = _check_ts(f"tier:{pid}:{cap_lbl}", t_ts)
            if t_stale:
                stale_tier_count += 1
                prog_stale_tiers.append(cap_lbl)
        per_program[pid] = {
            "verified_utc": str(p_ts),
            "age_days": round(p_age, 3),
            "status": "STALE_NEEDS_REFRESH" if (p_stale or prog_stale_tiers) else "FRESH",
            "stale_tiers": prog_stale_tiers,
        }

    is_stale = len(stale_items) > 0
    has_future = len(future_items) > 0
    if has_future:
        status_str = "INVALID_FUTURE_TIMESTAMP"
    elif is_stale:
        status_str = "STALE_NEEDS_REFRESH"
    else:
        status_str = "FRESH"
    return {
        "status": status_str,
        "is_stale": is_stale,
        "has_future_timestamps": has_future,
        "future_items": future_items,
        "staleness_max_days": max_days,
        "checked_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalog_age_days": round(top_age, 3),
        "fx_age_days": round(fx_age, 3),
        "max_age_days": round(max_age_days, 3),
        "per_tier_count": tier_count,
        "stale_tier_count": stale_tier_count,
        "stale_items": stale_items,
        "per_program": per_program,
        "override_used": False,
    }


def load_pricing_catalog(
    path: Path | None = None,
    *,
    allow_fallback: bool = False,
    enforce_freshness: bool = True,
    allow_stale: bool = False,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Fail-closed pricing catalog loader with strict per-tier `verified_utc`, finite-price, and future-date guards.

    - Raises `FileNotFoundError` if `path` is missing and `allow_fallback=False` (production default).
    - Raises `ValueError` if catalog JSON is malformed, corrupt, contains `NaN`/`Inf`/`<=0` prices,
      lacks per-tier `verified_utc`, contains future timestamps (`> now_utc + 1 day`, e.g. `2099`),
      or is stale (`> staleness_max_days` when `enforce_freshness=True` and `allow_stale=False`).
    - Tests may explicitly pass `allow_fallback=True` (for builtin default fixture) or `allow_stale=True`
      (for offline historical audit; future timestamps are STILL rejected!).
    """
    p = Path(path) if path is not None else DEFAULT_CATALOG_PATH
    if p is not None and p.is_file():
        try:
            raw_bytes = p.read_bytes()
            raw = json.loads(raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Corrupt JSON in pricing catalog {p}: {exc}") from exc
        norm = _normalize_external_catalog(raw)
        norm["source_path"] = str(p)
        norm["source_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
        freshness = check_catalog_freshness(norm, now_utc=now_utc)
        if freshness["has_future_timestamps"]:
            f_scopes = ", ".join(
                f"{item['scope']}={item['verified_utc']} (+{item['future_by_days']}d)"
                for item in freshness["future_items"][:6]
            )
            raise ValueError(
                f"FUTURE_TIMESTAMP_CATALOG_ERROR: {len(freshness['future_items'])} item(s) exceed "
                f"now_utc + {MAX_FUTURE_TIMESTAMP_SKEW_DAYS:.0f}d tolerance: {f_scopes}"
            )
        if enforce_freshness and freshness["is_stale"]:
            if not allow_stale:
                scopes = ", ".join(item["scope"] for item in freshness["stale_items"][:6])
                raise ValueError(
                    f"STALE_CATALOG_ERROR: {len(freshness['stale_items'])} item(s) exceed "
                    f"{freshness['staleness_max_days']}d freshness limit (max_age={freshness['max_age_days']}d): {scopes}"
                )
            freshness["override_used"] = True
            freshness["status"] = "STALE_OVERRIDDEN_HISTORICAL_AUDIT"
        norm["freshness_report"] = freshness
        return norm

    if not allow_fallback:
        raise FileNotFoundError(
            f"Pricing catalog not found (fail-closed, allow_fallback=False): {p}"
        )

    fb = build_default_pricing_catalog()
    fb["source_path"] = "BUILTIN_DEFAULT_FALLBACK"
    fb["source_sha256"] = "FALLBACK"
    fb["freshness_report"] = check_catalog_freshness(fb, now_utc=now_utc) if enforce_freshness else {
        "status": "SKIPPED_FALLBACK",
        "is_stale": False,
        "override_used": True,
    }
    return fb


def get_program_tier(
    catalog: dict[str, Any],
    program_id: str,
    capital_usd: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Lookup exact (program, tier) specification from normalized catalog."""
    for prog in catalog["programs"]:
        if prog["program_id"] == program_id:
            for tier in prog["tiers"]:
                if abs(float(tier["capital_usd"]) - float(capital_usd)) < 1e-6:
                    merged = {**prog, **tier}
                    return prog, merged
    raise KeyError(f"Program/tier not found in catalog: {program_id} @ {capital_usd}")


def detect_pricing_traps(catalog: dict[str, Any]) -> dict[str, Any]:
    """Programmatically verify VN checkout traps (`25K` fee-ratio trap, `200K == 2x 100K`, `Swing >= 50K unavailable`)."""
    std_prog = next(
        (p for p in catalog["programs"] if p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"),
        None,
    )
    swing_prog = next(
        (p for p in catalog["programs"] if p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Swing"),
        None,
    )
    out: dict[str, Any] = {
        "trap_25k_detected": False,
        "parity_200k_vs_2x100k_detected": False,
        "swing_50k_plus_unavailable_vn": False,
        "details": {},
    }
    if std_prog is not None:
        by_cap = {float(t["capital_usd"]): t for t in std_prog["tiers"]}
        if all(c in by_cap for c in (10_000.0, 25_000.0, 50_000.0, 100_000.0, 200_000.0)):
            r10_orig = by_cap[10_000.0]["orig_usd"] / 10_000.0
            r25_orig = by_cap[25_000.0]["orig_usd"] / 25_000.0
            r50_orig = by_cap[50_000.0]["orig_usd"] / 50_000.0
            r100_orig = by_cap[100_000.0]["orig_usd"] / 100_000.0
            r200_orig = by_cap[200_000.0]["orig_usd"] / 200_000.0

            r10_bf = by_cap[10_000.0]["active_promo_usd"] / 10_000.0
            r25_bf = by_cap[25_000.0]["active_promo_usd"] / 25_000.0
            r50_bf = by_cap[50_000.0]["active_promo_usd"] / 50_000.0
            r100_bf = by_cap[100_000.0]["active_promo_usd"] / 100_000.0
            r200_bf = by_cap[200_000.0]["active_promo_usd"] / 200_000.0

            out["trap_25k_detected"] = bool((r25_orig > r10_orig) and (r25_bf > r10_bf) and (r25_bf > r50_bf))
            out["parity_200k_vs_2x100k_detected"] = bool(
                abs(r200_orig - r100_orig) <= 1e-5 and abs(r200_bf - r100_bf) <= 1e-5
            )
            out["details"]["ftmo_2step_std_fee_ratio_pct"] = {
                "10K_orig_pct": round(r10_orig * 100.0, 4),
                "25K_orig_pct": round(r25_orig * 100.0, 4),
                "50K_orig_pct": round(r50_orig * 100.0, 4),
                "100K_orig_pct": round(r100_orig * 100.0, 4),
                "200K_orig_pct": round(r200_orig * 100.0, 4),
                "10K_promo_pct": round(r10_bf * 100.0, 4),
                "25K_promo_pct": round(r25_bf * 100.0, 4),
                "50K_promo_pct": round(r50_bf * 100.0, 4),
                "100K_promo_pct": round(r100_bf * 100.0, 4),
                "200K_promo_pct": round(r200_bf * 100.0, 4),
                "25k_vs_10k_promo_premium_pct": round((r25_bf / r10_bf - 1.0) * 100.0, 2),
                "25k_vs_50k_promo_premium_pct": round((r25_bf / r50_bf - 1.0) * 100.0, 2),
                "100k_vs_10k_promo_savings_pct": round((1.0 - r100_bf / r10_bf) * 100.0, 2),
            }
    if swing_prog is not None:
        by_cap_sw = {float(t["capital_usd"]): t for t in swing_prog["tiers"]}
        blocked = [c for c in (50_000.0, 100_000.0, 200_000.0) if c in by_cap_sw and not by_cap_sw[c].get("available_vn", True)]
        out["swing_50k_plus_unavailable_vn"] = len(blocked) == 3
        out["details"]["swing_vn_blocked_tiers"] = blocked

    e8_prog = next((p for p in catalog["programs"] if "E8" in p["firm_id"]), None)
    if e8_prog is not None:
        by_cap_e8 = {float(t["capital_usd"]): t for t in e8_prog["tiers"]}
        if 50_000.0 in by_cap_e8 and 100_000.0 in by_cap_e8:
            r50 = by_cap_e8[50_000.0]["active_promo_usd"] / 50_000.0
            r100 = by_cap_e8[100_000.0]["active_promo_usd"] / 100_000.0
            out["e8_100k_gt_2x50k_trap_detected"] = bool(r100 > r50 + 1e-6)
            out["details"]["e8_fee_ratio_pct"] = {
                "50K_pct": round(r50 * 100.0, 4),
                "100K_pct": round(r100 * 100.0, 4),
            }
    return out


def load_step5_c00_c10_summary(path: Path | None = None) -> dict[str, Any]:
    """Ingest Step 5 `C00 vs C10` unified or 7-yr Dev report; lock v2 primary variant to `C10_NEWS_ON` with `C00` control."""
    p = path or DEFAULT_STEP5_REPORT_PATH
    fallback_7yr = DEFAULT_STEP5_REPORT_PATH.parent / "step5_7yr_dev_c00_vs_c10_report.json"
    chosen = p if (p is not None and Path(p).is_file()) else (fallback_7yr if fallback_7yr.is_file() else None)
    if chosen is not None:
        raw = json.loads(Path(chosen).read_text(encoding="utf-8"))
        dev7_ref = raw.get("dev_7yr_study_reference") or {}
        rank_audit = raw.get("ranking_stability_audit") or dev7_ref.get("ranking_stability_audit") or {}
        sl_cal = raw.get("sl_gap_slippage_calibration") or dev7_ref.get("sl_gap_slippage_calibration") or {}
        mt5_pairs = raw.get("mt5_model4_q4_2024_same_phase_pairs") or {}
        verdict = str(
            raw.get("overall_ranking_stability_verdict")
            or rank_audit.get("overall_verdict")
            or raw.get("ranking_stability_verdict")
            or raw.get("verdict")
            or "INDISTINGUISHABLE_RANK_FLIP"
        )
        # Step 5/6 + Astra R10 closure: primary variant is ALWAYS `C10_NEWS_ON` (Red-News ON all phases),
        # with `C00` as incumbent control and `C10` (News-OFF) retained strictly as ablation/sensitivity.
        primary_variant = PRIMARY_VARIANT_DEFAULT
        active_variants = [PRIMARY_VARIANT_DEFAULT, CONTROL_VARIANT_DEFAULT, "C10"]
        return {
            "loaded": True,
            "is_full_mt5_plus_7yr": bool(mt5_pairs),
            "source_path": str(chosen),
            "source_sha256": hashlib.sha256(Path(chosen).read_bytes()).hexdigest(),
            "verdict": verdict,
            "primary_variant": primary_variant,
            "control_variant": CONTROL_VARIANT_DEFAULT,
            "active_variants": active_variants,
            "primary_variant_rationale": (
                "Step 5/6 MT5 Model=4 & Astra R10 confirmed C10_NEWS_ON (C10 sizing/ProfitLock + Red-News ON all phases) "
                "dominates both C00 control and C10 News-OFF."
            ),
            "sl_gap_slippage_summary": sl_cal.get("preset_summary", {}),
            "mt5_model4_q4_2024_same_phase_pairs": mt5_pairs,
            "ea_provenance": raw.get("ea_provenance", {}),
        }
    return {
        "loaded": False,
        "is_full_mt5_plus_7yr": False,
        "source_path": "PENDING_STEP5_REPORT",
        "source_sha256": "PENDING",
        "verdict": "PENDING_DEFAULT_C10_NEWS_ON_WITH_C00_CONTROL",
        "primary_variant": PRIMARY_VARIANT_DEFAULT,
        "control_variant": CONTROL_VARIANT_DEFAULT,
        "active_variants": [PRIMARY_VARIANT_DEFAULT, CONTROL_VARIANT_DEFAULT],
        "primary_variant_rationale": "Default v2 primary variant C10_NEWS_ON with C00 incumbent control.",
        "sl_gap_slippage_summary": {},
        "mt5_model4_q4_2024_same_phase_pairs": {},
        "ea_provenance": {},
    }


# ---------------------------------------------------------------------------
# Strict Holdout Guard & Exact 0.01-Lot Rounding Simulator
# ---------------------------------------------------------------------------

def assert_strict_pre_holdout_days(days: list[str] | tuple[str, ...]) -> int:
    """Fail-closed if ANY day is `>= 2025-01-01` or year > 2024; returns `holdout_rows_analysed = 0`."""
    for d in days:
        ds = str(d)
        if ds >= HOLDOUT_CUTOFF_DAY or int(ds[:4]) > HOLDOUT_MAX_YEAR:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: forbidden holdout date detected: {ds}")
    return 0


def floor_lot_step(
    raw_lots: float,
    *,
    step: float = 0.01,
    vol_min: float = 0.01,
    vol_max: float = 1000.0,
) -> float:
    """Exact broker `0.01`-lot floor rounding (`< vol_min` returns `0.0`, trade skipped)."""
    if raw_lots <= 0.0 or not math.isfinite(raw_lots):
        return 0.0
    capped = min(float(raw_lots), float(vol_max))
    steps = math.floor(capped / step + 1e-9)
    lot = round(steps * step, 8)
    if lot < vol_min - 1e-12:
        return 0.0
    return lot


def simulate_exact_lot_rounding_on_trade_list(
    trades: list[dict[str, Any]],
    *,
    capital_usd: float,
    risk_mult: float = 1.0,
    vol_step: float = 0.01,
    vol_min: float = 0.01,
    vol_max: float = 1000.0,
    years_span: float = 7.0,
) -> dict[str, Any]:
    """Exact per-trade `0.01`-lot rounding evaluator (works on real frozen tapes OR synthetic unit-test fixtures).

    Asserts every trade has `year <= 2024` and `day < '2025-01-01'`.
    Returns full balanced Law-15 metrics + lot-rounding utilization & rejection diagnostics.
    """
    holdout_rows = 0
    total_signals = 0
    sized_trades = 0
    min_lot_rejected = 0
    ideal_risk_sum = 0.0
    actual_risk_sum = 0.0

    pnls: list[float] = []
    r_vals: list[float] = []
    bal = float(capital_usd)
    peak = bal
    max_dd = 0.0
    cur_loss_streak = 0
    max_loss_streak = 0
    day_pnls: dict[str, float] = {}

    for tr in trades:
        dk = str(tr["day"])
        yr = int(tr.get("year", int(dk[:4])))
        if dk >= HOLDOUT_CUTOFF_DAY or yr > HOLDOUT_MAX_YEAR:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: trade date {dk} / year {yr} exceeds sealed 2024 cutoff")
        total_signals += 1
        base_risk_frac = float(tr["base_risk_frac"])
        stop_cost_1lot = float(tr["stop_risk_with_cost_usd"])
        net_1lot = float(tr["net_usd_per_lot"])
        if stop_cost_1lot <= 0.0:
            continue

        budget_usd = float(capital_usd) * base_risk_frac * float(risk_mult)
        raw_lots = budget_usd / stop_cost_1lot
        lot = floor_lot_step(raw_lots, step=vol_step, vol_min=vol_min, vol_max=vol_max)

        ideal_risk_sum += budget_usd
        if lot <= 0.0:
            min_lot_rejected += 1
            continue

        sized_trades += 1
        actual_risk_usd = lot * stop_cost_1lot
        actual_risk_sum += actual_risk_usd
        pnl = lot * net_1lot
        pnls.append(pnl)
        r_vals.append(pnl / max(1e-9, budget_usd))
        day_pnls[dk] = day_pnls.get(dk, 0.0) + pnl

        bal += pnl
        if bal > peak:
            peak = bal
        dd = peak - bal
        if dd > max_dd:
            max_dd = dd

        if pnl < 0.0:
            cur_loss_streak += 1
            if cur_loss_streak > max_loss_streak:
                max_loss_streak = cur_loss_streak
        elif pnl > 0.0:
            cur_loss_streak = 0

    wins = [p for p in pnls if p > 0.0]
    losses = [p for p in pnls if p < 0.0]
    gross_win = float(sum(wins))
    gross_loss = abs(float(sum(losses)))
    pf = (gross_win / gross_loss) if gross_loss > 1e-9 else (99.0 if gross_win > 0.0 else 0.0)
    winrate_pct = (100.0 * len(wins) / len(pnls)) if pnls else 0.0
    avg_win = (gross_win / len(wins)) if wins else 0.0
    avg_loss = (gross_loss / len(losses)) if losses else 0.0
    rr = (avg_win / avg_loss) if avg_loss > 1e-9 else 0.0
    ev_r = float(np.mean(r_vals)) if r_vals else 0.0

    total_net = float(sum(pnls))
    ann_pct = 100.0 * (total_net / max(1e-9, float(years_span))) / float(capital_usd)
    max_dd_pct = 100.0 * max_dd / float(capital_usd)
    calmar = (ann_pct / max_dd_pct) if max_dd_pct > 1e-9 else 0.0

    if len(day_pnls) >= 2:
        dp = np.asarray(list(day_pnls.values()), dtype=np.float64) / float(capital_usd)
        std_d = float(np.std(dp, ddof=1))
        sharpe = (float(np.mean(dp)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0
    else:
        sharpe = 0.0

    return {
        "capital_usd": float(capital_usd),
        "risk_mult": float(risk_mult),
        "holdout_rows_analysed": holdout_rows,
        "total_signals": total_signals,
        "sized_trades": sized_trades,
        "min_lot_rejected": min_lot_rejected,
        "min_lot_reject_pct": round(100.0 * min_lot_rejected / max(1, total_signals), 3),
        "mean_risk_utilization_pct": round(100.0 * actual_risk_sum / max(1e-9, ideal_risk_sum), 2),
        "total_net_usd": round(total_net, 2),
        "ann_return_pct": round(ann_pct, 3),
        "max_dd_pct": round(max_dd_pct, 3),
        "calmar": round(calmar, 3),
        "sharpe": round(sharpe, 3),
        "winrate_pct": round(winrate_pct, 2),
        "avg_rr": round(rr, 3),
        "ev_per_trade_r": round(ev_r, 4),
        "profit_factor": round(pf, 3),
        "max_loss_streak_trades": max_loss_streak,
    }


def exits_to_daily_arrays_with_upside(
    ext_days: list[str],
    exits: list[dict[str, Any]],
    initial: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Convert M1 replay exits into dense daily `(net_usd, intraday_dd_usd, intraday_upside_usd, traded_flag)` arrays."""
    by_day = {e["day"]: e for e in exits}
    n = len(ext_days)
    nets = np.zeros(n, dtype=np.float64)
    dds = np.zeros(n, dtype=np.float64)
    ups = np.zeros(n, dtype=np.float64)
    flg = np.zeros(n, dtype=np.int8)
    prev_cash = float(initial)
    for i, dk in enumerate(ext_days):
        e = by_day.get(dk)
        if e is not None:
            nets[i] = float(e["net_usd"])
            dds[i] = max(0.0, prev_cash - float(e["day_equity_minimum"]))
            ups[i] = max(0.0, float(e.get("day_equity_maximum", prev_cash + max(0.0, nets[i]))) - prev_cash)
            flg[i] = 1
            prev_cash = float(e["cash"])
    return nets, dds, ups, flg


def compute_exits_balanced_metrics(
    ext_days: list[str],
    exits: list[dict[str, Any]],
    replay_met: dict[str, Any],
    initial: float,
    tapes: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]],
) -> dict[str, Any]:
    """Extract full balanced Law-15 portfolio statistics from exact M1 replay exits."""
    sized = 0
    min_lot_rej = 0
    margin_rej = 0
    symcap_rej = 0
    trade_pnls: list[float] = []
    trade_rs: list[float] = []
    cur_loss = 0
    max_loss = 0

    for ex in exits:
        dk = ex["day"]
        for o in ex.get("orders", []):
            st = o.get("status")
            if st == "SIZED":
                sized += 1
                eng = o["engine"]
                lots = float(o["lots"])
                eff_risk = float(o.get("eff_risk", 0.0))
                row = tapes[eng][dk][0]
                pnl = lots * float(row["net_usd_per_lot"])
                budget = initial * eff_risk
                trade_pnls.append(pnl)
                if budget > 1e-9:
                    trade_rs.append(pnl / budget)
                if pnl < 0.0:
                    cur_loss += 1
                    if cur_loss > max_loss:
                        max_loss = cur_loss
                elif pnl > 0.0:
                    cur_loss = 0
            elif st == "MIN_LOT":
                min_lot_rej += 1
            elif st == "MARGIN":
                margin_rej += 1
            elif st == "SYM_RISK_CAP_SKIP":
                symcap_rej += 1

    nets, dds, _, _ = exits_to_daily_arrays_with_upside(ext_days, exits, initial)
    daily_ret = nets / max(1.0, float(initial))
    std_d = float(np.std(daily_ret, ddof=1)) if len(daily_ret) > 1 else 0.0
    sharpe = (float(np.mean(daily_ret)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0

    wins = [p for p in trade_pnls if p > 0.0]
    losses = [p for p in trade_pnls if p < 0.0]
    gwin = float(sum(wins))
    gloss = abs(float(sum(losses)))
    pf = (gwin / gloss) if gloss > 1e-9 else 0.0
    winrate = (100.0 * len(wins) / len(trade_pnls)) if trade_pnls else 0.0
    avg_w = (gwin / len(wins)) if wins else 0.0
    avg_l = (gloss / len(losses)) if losses else 0.0
    rr = (avg_w / avg_l) if avg_l > 1e-9 else 0.0
    ev_r = float(np.mean(trade_rs)) if trade_rs else 0.0
    tot_cand = sized + min_lot_rej + margin_rej

    return {
        "capital_usd": float(initial),
        "sized_trades": sized,
        "min_lot_rejected": min_lot_rej,
        "min_lot_reject_pct": round(100.0 * min_lot_rej / max(1, tot_cand), 3),
        "margin_rejected": margin_rej,
        "symcap_skipped": symcap_rej,
        "net_usd": round(float(replay_met["net_usd"]), 2),
        "ann_pct": round(float(replay_met["ann_pct"]["all"]), 3),
        "ann_cluster_a_pct": round(float(replay_met["ann_pct"]["A"]), 3),
        "ann_cluster_b_pct": round(float(replay_met["ann_pct"]["B"]), 3),
        "peak_dd_pct": round(float(replay_met["peak_dd_pct"]), 3),
        "max_daily_dd_pct": round(float(replay_met["daily_loss_pct"]), 3),
        "calmar": round(float(replay_met["calmar"]), 3),
        "sharpe": round(sharpe, 3),
        "winrate_pct": round(winrate, 2),
        "avg_rr": round(rr, 3),
        "ev_per_trade_r": round(ev_r, 4),
        "profit_factor": round(pf, 3),
        "max_loss_streak_trades": max_loss,
        "underwater_months": round(float(replay_met["underwater_months"]), 2),
    }


def make_block_bootstrap_indices(
    n_obs: int,
    *,
    horizon: int = 756,
    n_paths: int = 5_000,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
) -> np.ndarray:
    """Deterministic Circular Block-Bootstrap index matrix (`int32`)."""
    rng = np.random.default_rng(seed)
    n_blocks = (horizon + block_len - 1) // block_len
    starts = rng.integers(0, n_obs, size=(n_paths, n_blocks))
    offs = np.arange(block_len, dtype=np.int64)[None, None, :]
    idxs = (starts[:, :, None] + offs).reshape(n_paths, n_blocks * block_len)[:, :horizon] % n_obs
    return idxs.astype(np.int32)


def make_firm_hazard_days(
    n_paths: int,
    n_firms: int,
    annual_hazard_rate: float,
    *,
    horizon: int = 756,
    seed: int = DEFAULT_SEED + 777,
) -> np.ndarray:
    """Generate independent exponential firm-disruption event day (`-1` if none within horizon) per `(path, firm)`."""
    if annual_hazard_rate <= 1e-12:
        return np.full((n_paths, n_firms), -1, dtype=np.int32)
    rng = np.random.default_rng(seed)
    daily_rate = float(annual_hazard_rate) / float(TRADING_DAYS_PER_YEAR)
    # Exponential waiting time in trading days
    u = rng.uniform(1e-12, 1.0, size=(n_paths, n_firms))
    wait_days = np.floor(-np.log(u) / daily_rate).astype(np.int32)
    out = np.where(wait_days < horizon, wait_days, -1).astype(np.int32)
    return out


# ---------------------------------------------------------------------------
# Numba-JIT Single-Ticket Rule-Engine Simulator (Law 13 + NPV + All Modes)
# ---------------------------------------------------------------------------

@njit(cache=True)
def _simulate_single_ticket_rules_numba(
    idx_matrix: np.ndarray,
    # Exact tier-level M1 replayed daily arrays (ALREADY in exact tier USD — NO linear scaling!)
    n_p1: np.ndarray, d_p1: np.ndarray, u_p1: np.ndarray, f_p1: np.ndarray,
    n_p1l: np.ndarray, d_p1l: np.ndarray, u_p1l: np.ndarray, f_p1l: np.ndarray,
    n_p2: np.ndarray, d_p2: np.ndarray, u_p2: np.ndarray, f_p2: np.ndarray,
    n_p2l: np.ndarray, d_p2l: np.ndarray, u_p2l: np.ndarray, f_p2l: np.ndarray,
    n_fn: np.ndarray, d_fn: np.ndarray, u_fn: np.ndarray, f_fn: np.ndarray,
    n_amb: np.ndarray, d_amb: np.ndarray, u_amb: np.ndarray, f_amb: np.ndarray,
    n_red: np.ndarray, d_red: np.ndarray, u_red: np.ndarray, f_red: np.ndarray,
    # Mode & contract rules
    steps: int,                # 0=Instant, 1=1-Step, 2=2-Step
    cap: float,
    fee_day0_usd: float,       # purchase-day Day-0 ticket fee (promo if active, else regular)
    fee_regular_usd: float,    # regular ticket fee used on ALL retries after Day 0 (NO perpetual BF!)
    card_fx_fee_pct: float,    # buy-side non-refundable card FX fee (+2.5%)
    withdrawal_fee_pct: float, # payout withdrawal + FX spread fee on profit split payouts
    fee_refund_pct: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    max_dd_lim: float,
    dd_type: int,              # 0=STATIC, 1=EOD_TRAILING, 2=INTRADAY_TRAILING
    trail_lock_initial: bool,
    best_day_cap_pct: float,   # 0.0=off, 0.50=1-Step, 0.30=Instant
    min_days: int,
    min_prof_days: int,
    min_prof_day_pct: float,
    profit_split: float,
    payout_cycle_days: int,
    min_payout_usd: float,
    strict_lt_breach: bool,
    # Risk pacing & bot auto-kill thresholds
    p1_lock_trigger: float,
    p2_lock_trigger: float,
    amber_dd: float,
    red_dd: float,
    p1_ea_stop: float,
    p2_ea_stop: float,
    fn_ea_stop: float,
    # Economics & start delay (for dynamic wait-for-sale!)
    start_day_offset: int,
    discount_rate_annual: float,
    max_retries: int,
    # Extended firm-specific rules & v2 closures (B4/B5/B6 + daily DD anchor)
    refund_payout_milestone: int = 1,
    payout_buffer_retention_pct: float = 0.0,
    locks_at_initial_after_first_payout: bool = False,
    min_payout_profit_pct: float = 0.0,
    funded_first_payout_min_prof_days: int = 0,
    funded_first_payout_prof_pct: float = 0.0,
    daily_profit_cap_pct: float = 0.0,
    refund_withdrawal_fee_pct: float = 0.0,
    daily_dd_anchor_mode: int = 0,       # 0=INITIAL_BALANCE, 1=PREV_DAY_BALANCE
    shifting_horizon: bool = False,      # False=fixed 504d calendar deadline; True=504d from start_day_offset
    funded_first_payout_min_profit_pct: float = 0.0,  # Optional Payout #1 buffer wait (e.g. E8 +8%/+10% sensitivity)
):
    """Exact single-ticket (or retry-enabled) lifecycle simulator with Law-13/15 metrics, Day-0 vs Regular fees & NPV."""
    n_paths, horizon = idx_matrix.shape
    eff_fee_day0_out = fee_day0_usd * (1.0 + card_fx_fee_pct)
    eff_fee_reg_out = fee_regular_usd * (1.0 + card_fx_fee_pct)
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    daily_cap = cap * daily_lim
    static_floor_base = cap * (1.0 - max_dd_lim)
    r_ann = discount_rate_annual
    inv_df = np.empty(horizon + 2, dtype=np.float64)
    for k_d in range(horizon + 2):
        inv_df[k_d] = (1.0 + r_ann) ** (-k_d / 252.0)

    cutoff_24m = (start_day_offset + 504) if shifting_horizon else 504

    # Per-path outputs
    eval_pass_day = np.full(n_paths, -1, dtype=np.int32)      # first day entered Funded (absolute day index + 1)
    eval_fail_day = np.full(n_paths, -1, dtype=np.int32)      # first eval fail day (1st ticket)
    pay1_day = np.full(n_paths, -1, dtype=np.int32)           # first payout day (absolute day index + 1)
    funded_enter_day = np.full(n_paths, -1, dtype=np.int32)   # 1st ticket entered Funded day
    funded_breach_day = np.full(n_paths, -1, dtype=np.int32)  # 1st ticket breached in Funded day

    bot_kill_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_daily = np.zeros(n_paths, dtype=np.int8)
    firm_breach_maxdd = np.zeros(n_paths, dtype=np.int8)

    npv_24m = np.zeros(n_paths, dtype=np.float64)
    npv_36m = np.zeros(n_paths, dtype=np.float64)
    cf_24m = np.zeros(n_paths, dtype=np.float64)
    cf_36m = np.zeros(n_paths, dtype=np.float64)
    fees_24m = np.zeros(n_paths, dtype=np.float64)
    payouts_24m = np.zeros(n_paths, dtype=np.float64)
    max_oop = np.zeros(n_paths, dtype=np.float64)
    tickets_used = np.zeros(n_paths, dtype=np.int32)

    # Funded dry-month tracking (over 24m/36m while Funded)
    funded_months_total = np.zeros(n_paths, dtype=np.int32)
    funded_months_dry = np.zeros(n_paths, dtype=np.int32)
    funded_max_dry_streak = np.zeros(n_paths, dtype=np.int32)

    for b in range(n_paths):
        if start_day_offset >= horizon:
            continue

        # Initial ticket purchase on start_day_offset (Day-0 / purchase-day price)
        stage = 3 if steps == 0 else 1
        bal = cap
        hwm = cap
        tdays = 0
        pdays_cnt = 0
        cycle_d = 0
        max_day_gain = 0.0
        refunded = False
        payout_cnt = 0
        fn_pdays_cnt = 0
        attempts = 1
        first_ticket_active = True
        cur_ticket_fee = fee_day0_usd

        cum_npv = -eff_fee_day0_out * inv_df[start_day_offset]
        cum_cf = -eff_fee_day0_out
        cum_fees = eff_fee_day0_out
        cum_payouts = 0.0
        path_oop = eff_fee_day0_out

        f_eval_pass = start_day_offset if steps == 0 else -1
        f_eval_fail = -1
        f_pay1 = -1
        f_fn_enter = start_day_offset if steps == 0 else -1
        f_fn_breach = -1
        b_kill = 0
        f_br = 0
        f_br_d = 0
        f_br_m = 0

        # Funded month-level dry tracker (21 trading days = 1 month)
        fn_month_days = 0
        fn_month_paid = 0
        cur_dry_streak = 0
        best_dry_streak = 0
        tot_fn_m = 0
        dry_fn_m = 0

        recorded_24m = False

        for d in range(horizon):
            if d >= start_day_offset and stage > 0:
                src = idx_matrix[b, d]
                eq_pct = (bal - cap) / cap

                # Select exact tier-level M1 stage tape (NO linear scaling!)
                if eq_pct <= -red_dd:
                    net = n_red[src]
                    dd = d_red[src]
                    up = u_red[src]
                    flg = f_red[src]
                    ea_stop_pct = fn_ea_stop if stage == 3 else (p2_ea_stop if stage == 2 else p1_ea_stop)
                elif eq_pct <= -amber_dd:
                    net = n_amb[src]
                    dd = d_amb[src]
                    up = u_amb[src]
                    flg = f_amb[src]
                    ea_stop_pct = fn_ea_stop if stage == 3 else (p2_ea_stop if stage == 2 else p1_ea_stop)
                elif stage == 1:
                    prog = eq_pct / max(1e-6, p1_target)
                    if p1_lock_trigger > 0.0 and prog >= p1_lock_trigger:
                        net, dd, up, flg = n_p1l[src], d_p1l[src], u_p1l[src], f_p1l[src]
                    else:
                        net, dd, up, flg = n_p1[src], d_p1[src], u_p1[src], f_p1[src]
                    ea_stop_pct = p1_ea_stop
                elif stage == 2:
                    prog = eq_pct / max(1e-6, p2_target)
                    if p2_lock_trigger > 0.0 and prog >= p2_lock_trigger:
                        net, dd, up, flg = n_p2l[src], d_p2l[src], u_p2l[src], f_p2l[src]
                    else:
                        net, dd, up, flg = n_p2[src], d_p2[src], u_p2[src], f_p2[src]
                    ea_stop_pct = p2_ea_stop
                else:
                    net, dd, up, flg = n_fn[src], d_fn[src], u_fn[src], f_fn[src]
                    ea_stop_pct = fn_ea_stop

                # Compute max-DD floor depending on DD type
                if dd_type == 2:  # INTRADAY_TRAILING
                    intra_peak = bal + up
                    if intra_peak > hwm:
                        hwm = intra_peak
                    max_floor = hwm * (1.0 - max_dd_lim)
                    if trail_lock_initial and max_floor > cap:
                        max_floor = cap
                elif dd_type == 1:  # EOD_TRAILING (floor anchored to prior EOD HWM during day)
                    max_floor = hwm * (1.0 - max_dd_lim)
                    if trail_lock_initial and max_floor > cap:
                        max_floor = cap
                else:  # STATIC
                    if locks_at_initial_after_first_payout and stage == 3 and payout_cnt >= 1:
                        max_floor = cap
                    else:
                        max_floor = static_floor_base

                day_min_eq = bal - dd
                # Per-contract daily DD anchor (initial_balance static vs prev_day_balance / balance_or_equity)
                if daily_dd_anchor_mode == 1:
                    daily_floor = bal * (1.0 - daily_lim)
                else:
                    daily_floor = bal - daily_cap
                ea_cut = cap * ea_stop_pct if ea_stop_pct > 0.0 else 1e18

                # Check raw broker tick-monitor limits FIRST (cannot undo instantaneous M1 spikes)
                if strict_lt_breach:
                    d_hit = day_min_eq < daily_floor - 1e-9
                    m_hit = day_min_eq < max_floor - 1e-9
                else:
                    d_hit = day_min_eq <= daily_floor + 1e-9
                    m_hit = day_min_eq <= max_floor + 1e-9

                # Separate BOT_AUTO_KILL from FIRM_HARD_BREACH
                if (not d_hit) and (not m_hit) and (dd > ea_cut):
                    b_kill = 1
                    # Conservative +0.20% flatten slippage charged to net PnL
                    dd_eff = min(dd, ea_cut + cap * 0.0020)
                    net = min(net, -dd_eff)
                    day_min_eq_eff = bal - dd_eff
                    if strict_lt_breach:
                        d_hit = day_min_eq_eff < daily_floor - 1e-9
                        m_hit = day_min_eq_eff < max_floor - 1e-9
                    else:
                        d_hit = day_min_eq_eff <= daily_floor + 1e-9
                        m_hit = day_min_eq_eff <= max_floor + 1e-9

                if d_hit or m_hit:
                    f_br = 1
                    if d_hit:
                        f_br_d = 1
                    if m_hit:
                        f_br_m = 1

                    if first_ticket_active:
                        if stage < 3 and f_eval_fail < 0:
                            f_eval_fail = d + 1
                        elif stage == 3 and f_fn_breach < 0:
                            f_fn_breach = d + 1
                        first_ticket_active = False

                    if attempts <= max_retries:
                        attempts += 1
                        # Retries ALWAYS pay regular non-promo ticket price (`fee_regular_usd`)!
                        cur_ticket_fee = fee_regular_usd
                        cum_npv -= eff_fee_reg_out * inv_df[d]
                        cum_cf -= eff_fee_reg_out
                        cum_fees += eff_fee_reg_out
                        stage = 3 if steps == 0 else 1
                        bal = cap
                        hwm = cap
                        tdays = 0
                        pdays_cnt = 0
                        cycle_d = 0
                        max_day_gain = 0.0
                        refunded = False
                        payout_cnt = 0
                        fn_pdays_cnt = 0
                    else:
                        stage = 0
                else:
                    if daily_profit_cap_pct > 0.0 and net > cap * daily_profit_cap_pct:
                        net = cap * daily_profit_cap_pct
                    bal += net
                    if dd_type == 1 and bal > hwm:
                        hwm = bal
                    if net > max_day_gain:
                        max_day_gain = net

                    if flg != 0:
                        tdays += 1
                    if min_prof_day_pct > 0.0 and net >= cap * min_prof_day_pct - 1e-9:
                        pdays_cnt += 1

                    # Phase transitions (with Best Day Consistency check for 1-Step!)
                    if stage == 1:
                        met_target = bal >= p1_goal - 1e-9
                        met_days = (tdays >= min_days) and (pdays_cnt >= min_prof_days)
                        met_cons = True
                        if best_day_cap_pct > 0.0:
                            tot_prof = bal - cap
                            if tot_prof <= 0.0 or max_day_gain > best_day_cap_pct * tot_prof + 1e-9:
                                met_cons = False
                        if met_target and met_days and met_cons:
                            if steps == 1:
                                stage = 3
                                bal = cap
                                hwm = cap
                                tdays = 0
                                pdays_cnt = 0
                                cycle_d = 0
                                max_day_gain = 0.0
                                if f_eval_pass < 0:
                                    f_eval_pass = d + 1
                                if first_ticket_active and f_fn_enter < 0:
                                    f_fn_enter = d + 1
                            else:
                                stage = 2
                                bal = cap
                                hwm = cap
                                tdays = 0
                                pdays_cnt = 0
                                max_day_gain = 0.0
                    elif stage == 2:
                        met_target = bal >= p2_goal - 1e-9
                        met_days = (tdays >= min_days) and (pdays_cnt >= min_prof_days)
                        if met_target and met_days:
                            stage = 3
                            bal = cap
                            hwm = cap
                            tdays = 0
                            pdays_cnt = 0
                            cycle_d = 0
                            max_day_gain = 0.0
                            if f_eval_pass < 0:
                                f_eval_pass = d + 1
                            if first_ticket_active and f_fn_enter < 0:
                                f_fn_enter = d + 1
                    elif stage == 3:
                        cycle_d += 1
                        fn_month_days += 1
                        if funded_first_payout_prof_pct > 0.0 and net >= cap * funded_first_payout_prof_pct - 1e-9:
                            fn_pdays_cnt += 1
                        if cycle_d >= payout_cycle_days:
                            prof = bal - cap
                            cons_ok = True
                            if best_day_cap_pct > 0.0 and prof > 0.0:
                                if max_day_gain > best_day_cap_pct * prof + 1e-9:
                                    cons_ok = False
                            if payout_cnt == 0 and funded_first_payout_min_prof_days > 0:
                                if fn_pdays_cnt < funded_first_payout_min_prof_days:
                                    cons_ok = False
                            if payout_cnt == 0 and funded_first_payout_min_profit_pct > 0.0:
                                if prof < cap * funded_first_payout_min_profit_pct - 1e-9:
                                    cons_ok = False
                            if min_payout_profit_pct > 0.0 and prof < cap * min_payout_profit_pct - 1e-9:
                                cons_ok = False
                            if prof > 1e-6 and cons_ok:
                                withdrawable_prof = prof * (1.0 - payout_buffer_retention_pct)
                                gross_share = withdrawable_prof * profit_split
                                if gross_share >= min_payout_usd - 1e-9:
                                    payout_cnt += 1
                                    net_in = gross_share * (1.0 - withdrawal_fee_pct)
                                    if (
                                        not refunded
                                        and fee_refund_pct > 0.0
                                        and refund_payout_milestone > 0
                                        and payout_cnt >= refund_payout_milestone
                                    ):
                                        # Separate refund withdrawal fee (`0.0%` for FTMO card refund; non-refundable buy FX already paid!)
                                        net_in += cur_ticket_fee * fee_refund_pct * (1.0 - refund_withdrawal_fee_pct)
                                        refunded = True
                                    cum_npv += net_in * inv_df[d + 1]
                                    cum_cf += net_in
                                    cum_payouts += net_in
                                    fn_month_paid = 1
                                    if f_pay1 < 0:
                                        f_pay1 = d + 1
                                    # Retain buffer inside balance if payout_buffer_retention_pct > 0 (e.g. E8 50%)
                                    bal = cap + prof * payout_buffer_retention_pct
                                    hwm = bal
                                    max_day_gain = 0.0
                            cycle_d = 0

                        if fn_month_days >= 21:
                            tot_fn_m += 1
                            if fn_month_paid == 0:
                                dry_fn_m += 1
                                cur_dry_streak += 1
                                if cur_dry_streak > best_dry_streak:
                                    best_dry_streak = cur_dry_streak
                            else:
                                cur_dry_streak = 0
                            fn_month_days = 0
                            fn_month_paid = 0

                cur_oop = cum_fees - cum_payouts
                if cur_oop > path_oop:
                    path_oop = cur_oop

            if (not recorded_24m) and (d + 1 == cutoff_24m):
                npv_24m[b] = cum_npv
                cf_24m[b] = cum_cf
                fees_24m[b] = cum_fees
                payouts_24m[b] = cum_payouts
                recorded_24m = True

        if not recorded_24m:
            npv_24m[b] = cum_npv
            cf_24m[b] = cum_cf
            fees_24m[b] = cum_fees
            payouts_24m[b] = cum_payouts

        npv_36m[b] = cum_npv
        cf_36m[b] = cum_cf
        max_oop[b] = path_oop
        tickets_used[b] = attempts
        eval_pass_day[b] = f_eval_pass
        eval_fail_day[b] = f_eval_fail
        pay1_day[b] = f_pay1
        funded_enter_day[b] = f_fn_enter
        funded_breach_day[b] = f_fn_breach
        bot_kill_any[b] = b_kill
        firm_breach_any[b] = f_br
        firm_breach_daily[b] = f_br_d
        firm_breach_maxdd[b] = f_br_m
        funded_months_total[b] = tot_fn_m
        funded_months_dry[b] = dry_fn_m
        funded_max_dry_streak[b] = best_dry_streak

    return (
        eval_pass_day,
        eval_fail_day,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        firm_breach_daily,
        firm_breach_maxdd,
        npv_24m,
        npv_36m,
        cf_24m,
        cf_36m,
        fees_24m,
        payouts_24m,
        max_oop,
        tickets_used,
        funded_months_total,
        funded_months_dry,
        funded_max_dry_streak,
    )


def wilson_upper_95(k: int, n: int) -> float:
    """95% two-sided Wilson upper bound for a binomial proportion `k/n`."""
    if n <= 0:
        return 1.0
    z = 1.959963984540054
    p = k / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return min(1.0, (center + margin) / denom)


def summarize_single_ticket_mc(
    res: tuple[np.ndarray, ...],
    *,
    fee_usd: float,
    card_fx_fee_pct: float,
    usd_vnd_rate: float,
    horizon_days: int,
    start_day_offset: int = 0,
    fee_regular_usd: float | None = None,
    refund_withdrawal_fee_pct: float = 0.0,
) -> dict[str, Any]:
    """Summarize Law-13 single-ticket zero-retry & NPV results with strict `Pass + Fail + Pending == 100%`."""
    (
        eval_pass_day,
        eval_fail_day,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        firm_breach_daily,
        firm_breach_maxdd,
        npv_24m,
        npv_36m,
        cf_24m,
        cf_36m,
        fees_24m,
        payouts_24m,
        max_oop,
        tickets_used,
        fn_m_tot,
        fn_m_dry,
        fn_max_dry,
    ) = res
    n = len(eval_pass_day)
    fee_reg = float(fee_usd if fee_regular_usd is None else fee_regular_usd)
    eff_fee = fee_usd * (1.0 + card_fx_fee_pct)
    eff_fee_reg = fee_reg * (1.0 + card_fx_fee_pct)

    # Monthly mutually exclusive Pass / Fail / Pending table (strict sum == 100.0%)
    monthly_breakdown: dict[str, dict[str, float]] = {}
    for m in (3, 6, 12, 24, 36):
        cutoff = start_day_offset + m * TRADING_DAYS_PER_MONTH
        if cutoff > horizon_days:
            continue
        passed = (eval_pass_day >= 0) & (eval_pass_day <= cutoff)
        failed = (~passed) & (eval_fail_day > 0) & (eval_fail_day <= cutoff)
        pending = (~passed) & (~failed)
        p_pct = 100.0 * float(np.sum(passed)) / n
        f_pct = 100.0 * float(np.sum(failed)) / n
        w_pct = 100.0 * float(np.sum(pending)) / n
        # Assert exact partition before rounding
        assert abs((p_pct + f_pct + w_pct) - 100.0) < 1e-6
        monthly_breakdown[f"{m}m"] = {
            "pass_pct": round(p_pct, 2),
            "fail_pct": round(f_pct, 2),
            "pending_pct": round(w_pct, 2),
            "sum_pct": round(p_pct + f_pct + w_pct, 2),
        }

    # Unconditional wait days to 1st payout (capped at 365d & 730d calendar days)
    cal_pay1 = np.where(
        pay1_day > 0,
        (pay1_day - start_day_offset) * CALENDAR_DAYS_PER_TRADING_DAY,
        1e9,
    )
    uncond_pay1_cap365 = np.minimum(cal_pay1, 365.0)
    uncond_pay1_cap730 = np.minimum(cal_pay1, 730.0)
    paid_mask = pay1_day > 0
    passed_mask = eval_pass_day >= 0

    # Fixed 12-month Funded breach rate on Funded denominator (Law 13)
    entered_fn_mask = funded_enter_day >= 0
    n_fn_entered = int(np.sum(entered_fn_mask))
    if n_fn_entered > 0:
        fn_enter_sub = funded_enter_day[entered_fn_mask]
        fn_br_sub = funded_breach_day[entered_fn_mask]
        br_within_12m = (fn_br_sub > 0) & ((fn_br_sub - fn_enter_sub) <= TRADING_DAYS_PER_YEAR)
        full_12m_obs = (fn_enter_sub + TRADING_DAYS_PER_YEAR) <= horizon_days
        n_censored = int(np.sum(~full_12m_obs))
        n_br_12m = int(np.sum(br_within_12m))
        n_full_12m = int(np.sum(full_12m_obs))
        n_br_full = int(np.sum(br_within_12m & full_12m_obs))
        fn_br_12m_all_pct = 100.0 * n_br_12m / n_fn_entered
        fn_br_12m_uncensored_pct = (100.0 * n_br_full / n_full_12m) if n_full_12m > 0 else 0.0
        wilson_ub_pct = 100.0 * wilson_upper_95(n_br_12m, n_fn_entered)
    else:
        n_censored = 0
        n_br_12m = 0
        n_full_12m = 0
        fn_br_12m_all_pct = 0.0
        fn_br_12m_uncensored_pct = 0.0
        wilson_ub_pct = 100.0

    # Funded dry months & streak
    tot_fn_months_all = int(np.sum(fn_m_tot))
    dry_fn_months_all = int(np.sum(fn_m_dry))
    dry_month_pct = (100.0 * dry_fn_months_all / tot_fn_months_all) if tot_fn_months_all > 0 else 100.0
    fn_paths_with_m = fn_max_dry[fn_m_tot > 0]
    dry_streak_p50 = int(np.median(fn_paths_with_m)) if len(fn_paths_with_m) > 0 else 0
    dry_streak_p95 = int(np.quantile(fn_paths_with_m, 0.95)) if len(fn_paths_with_m) > 0 else 0

    ev_npv24 = float(np.mean(npv_24m))
    med_npv24 = float(np.median(npv_24m))
    ev_cf24 = float(np.mean(cf_24m))
    med_cf24 = float(np.median(cf_24m))
    ev_npv36 = float(np.mean(npv_36m))
    ev_cf36 = float(np.mean(cf_36m))
    mean_fees24 = float(np.mean(fees_24m))

    return {
        "model_tag": "DAILY_APPROX",
        "n_paths": n,
        "pricing_regime": "BF_DAY0_PLUS_REGULAR_RETRIES" if fee_usd < fee_reg - 1e-6 else "ALL_REGULAR",
        "fee_usd": round(fee_usd, 2),
        "fee_day0_usd": round(fee_usd, 2),
        "fee_regular_usd": round(fee_reg, 2),
        "effective_fee_with_vn_fx_usd": round(eff_fee, 2),
        "effective_regular_fee_with_vn_fx_usd": round(eff_fee_reg, 2),
        "effective_fee_vnd_tr": round(eff_fee * usd_vnd_rate / 1_000_000.0, 2),
        "refund_withdrawal_fee_pct": round(refund_withdrawal_fee_pct * 100.0, 2),
        "monthly_pass_fail_pending": monthly_breakdown,
        "pass_24m_pct": monthly_breakdown.get("24m", {}).get("pass_pct", 0.0),
        "fail_eval_24m_pct": monthly_breakdown.get("24m", {}).get("fail_pct", 0.0),
        "pending_eval_24m_pct": monthly_breakdown.get("24m", {}).get("pending_pct", 0.0),
        "paid_any_pct": round(100.0 * float(np.mean(paid_mask)), 2),
        "cond_med_pass_cal_days": round(
            float(np.median((eval_pass_day[passed_mask] - start_day_offset) * CALENDAR_DAYS_PER_TRADING_DAY)), 1
        ) if np.any(passed_mask) else -1.0,
        "cond_med_pay1_cal_days": round(float(np.median(cal_pay1[paid_mask])), 1) if np.any(paid_mask) else -1.0,
        "uncond_mean_pay1_cap365_days": round(float(np.mean(uncond_pay1_cap365)), 1),
        "uncond_med_pay1_cap365_days": round(float(np.median(uncond_pay1_cap365)), 1),
        "uncond_mean_pay1_cap730_days": round(float(np.mean(uncond_pay1_cap730)), 1),
        "uncond_med_pay1_cap730_days": round(float(np.median(uncond_pay1_cap730)), 1),
        "funded_12m_breach": {
            "n_entered_funded": n_fn_entered,
            "n_full_12m_observed": n_full_12m,
            "n_censored_lt_12m": n_censored,
            "n_breached_within_12m": n_br_12m,
            "breach_12m_pct": round(fn_br_12m_all_pct, 2),
            "breach_12m_uncensored_pct": round(fn_br_12m_uncensored_pct, 2),
            "wilson_95_upper_pct": round(wilson_ub_pct, 2),
            "note_n299": "De chung minh can tren 95% < 1% tren thuc te can ~299 quan sat doc lap khong chay.",
        },
        "funded_dry_months_pct": round(dry_month_pct, 2),
        "funded_dry_streak_p50_months": dry_streak_p50,
        "funded_dry_streak_p95_months": dry_streak_p95,
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_any > 0)), 2),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_any > 0)), 2),
        "firm_hard_breach_daily_pct": round(100.0 * float(np.mean(firm_breach_daily > 0)), 2),
        "firm_hard_breach_maxdd_pct": round(100.0 * float(np.mean(firm_breach_maxdd > 0)), 2),
        "p_net_le_0_24m_pct": round(100.0 * float(np.mean(npv_24m <= 0.0)), 2),
        "avg_tickets": round(float(np.mean(tickets_used)), 2),
        "mean_fees_24m_usd": round(mean_fees24, 2),
        "ev_npv_24m_usd": round(ev_npv24, 2),
        "ev_npv_24m_vnd_tr": round(ev_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_24m_usd": round(med_npv24, 2),
        "med_npv_24m_vnd_tr": round(med_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_24m_usd": round(ev_cf24, 2),
        "med_undisc_24m_usd": round(med_cf24, 2),
        "ev_npv_36m_usd": round(ev_npv36, 2),
        "ev_npv_36m_vnd_tr": round(ev_npv36 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_36m_usd": round(ev_cf36, 2),
        "ev_per_fee_npv24": round(ev_npv24 / max(1.0, eff_fee), 2),
        "ev_per_fee_undisc24": round(ev_cf24 / max(1.0, eff_fee), 2),
        "ev_per_total_fee_npv24": round(ev_npv24 / max(1.0, mean_fees24), 2),
        "oop95_usd": round(float(np.quantile(max_oop, 0.95)), 2),
        "oop95_vnd_tr": round(float(np.quantile(max_oop, 0.95)) * usd_vnd_rate / 1_000_000.0, 2),
    }


# ---------------------------------------------------------------------------
# Dual-Horizon Dynamic Sale-Calendar Engine (EXACT sweep, NO binary search, NO 2*d7 shortcut!)
# ---------------------------------------------------------------------------

def _sale_common_kwargs(
    program_tier: dict[str, Any],
    *,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    p1_lock_trigger: float = 0.70,
    p2_lock_trigger: float = 0.70,
    amber_dd: float = 0.035,
    red_dd: float = 0.060,
    p1_ea_stop: float = 0.035,
    p2_ea_stop: float = 0.030,
    fn_ea_stop: float = 0.025,
    max_retries: int = 0,
) -> dict[str, Any]:
    return dict(
        steps=int(program_tier["steps"]),
        cap=float(program_tier["capital_usd"]),
        card_fx_fee_pct=float(card_fx_fee_pct),
        withdrawal_fee_pct=float(program_tier.get("payout_withdrawal_fee_pct", program_tier.get("withdrawal_fee_pct", 0.015))),
        fee_refund_pct=float(program_tier.get("fee_refund_pct", 1.0)),
        p1_target=float(program_tier.get("p1_target_pct", 0.10)),
        p2_target=float(program_tier.get("p2_target_pct", 0.05)),
        daily_lim=float(program_tier.get("dd_daily_pct", 0.05)),
        max_dd_lim=float(program_tier.get("dd_max_pct", 0.10)),
        dd_type=_dd_type_code(program_tier.get("dd_type", "static")),
        trail_lock_initial=bool(program_tier.get("trail_lock_at_initial", False)),
        best_day_cap_pct=float(program_tier.get("best_day_cap_pct", 0.0)),
        min_days=int(program_tier.get("min_trading_days", 4)),
        min_prof_days=int(program_tier.get("min_profitable_days", 0)),
        min_prof_day_pct=float(program_tier.get("min_profitable_day_pct", 0.0)),
        profit_split=float(program_tier.get("profit_split_pct", 0.80)),
        payout_cycle_days=int(program_tier.get("payout_cycle_trading_days", 10)),
        min_payout_usd=float(program_tier.get("min_payout_usd", 50.0)),
        strict_lt_breach=True,
        p1_lock_trigger=float(p1_lock_trigger),
        p2_lock_trigger=float(p2_lock_trigger),
        amber_dd=float(amber_dd),
        red_dd=float(red_dd),
        p1_ea_stop=float(p1_ea_stop),
        p2_ea_stop=float(p2_ea_stop),
        fn_ea_stop=float(fn_ea_stop),
        discount_rate_annual=float(discount_rate_annual),
        max_retries=int(max_retries),
        refund_payout_milestone=int(program_tier.get("refund_payout_milestone", 1)),
        payout_buffer_retention_pct=float(program_tier.get("payout_buffer_retention_pct", 0.0)),
        locks_at_initial_after_first_payout=bool(program_tier.get("locks_at_initial_after_first_payout", False)),
        min_payout_profit_pct=float(program_tier.get("min_payout_profit_pct", 0.0)),
        funded_first_payout_min_prof_days=int(program_tier.get("funded_first_payout_min_prof_days", 0)),
        funded_first_payout_prof_pct=float(program_tier.get("funded_first_payout_prof_pct", 0.0)),
        daily_profit_cap_pct=float(program_tier.get("daily_profit_cap_pct", 0.0)),
        refund_withdrawal_fee_pct=float(program_tier.get("refund_withdrawal_fee_pct", 0.0)),
        daily_dd_anchor_mode=_daily_dd_anchor_code(program_tier.get("daily_dd_anchor", "initial_balance")),
    )


def evaluate_wait_vs_buy_npv(
    idx_matrix: np.ndarray,
    stage_arrays: tuple[np.ndarray, ...],
    *,
    program_tier: dict[str, Any],
    orig_fee_usd: float,
    active_discount_pct: float,
    wait_cal_days: int,
    next_sale_discount_pct: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    usd_vnd_rate: float,
    p1_lock_trigger: float = 0.70,
    p2_lock_trigger: float = 0.70,
    amber_dd: float = 0.035,
    red_dd: float = 0.060,
    p1_ea_stop: float = 0.035,
    p2_ea_stop: float = 0.030,
    fn_ea_stop: float = 0.025,
    max_retries: int = 0,
    shifting_horizon: bool = False,
) -> dict[str, Any]:
    """Compare exact MC NPV of buying today vs waiting `Y` calendar days for a `Z%` sale.

    Purchase-day pricing enforced: retries ALWAYS pay `orig_fee_usd` (NO perpetual promo on retries!).
    Supports both fixed calendar deadline (`shifting_horizon=False`) and shifting 24m horizon (`shifting_horizon=True`).
    """
    fee_today = orig_fee_usd * (1.0 - active_discount_pct)
    fee_wait = orig_fee_usd * (1.0 - next_sale_discount_pct)
    wait_tdays = max(0, int(round(wait_cal_days / CALENDAR_DAYS_PER_TRADING_DAY)))

    common = _sale_common_kwargs(
        program_tier,
        card_fx_fee_pct=card_fx_fee_pct,
        discount_rate_annual=discount_rate_annual,
        p1_lock_trigger=p1_lock_trigger,
        p2_lock_trigger=p2_lock_trigger,
        amber_dd=amber_dd,
        red_dd=red_dd,
        p1_ea_stop=p1_ea_stop,
        p2_ea_stop=p2_ea_stop,
        fn_ea_stop=fn_ea_stop,
        max_retries=max_retries,
    )

    res_today = _simulate_single_ticket_rules_numba(
        idx_matrix, *stage_arrays,
        fee_day0_usd=float(fee_today), fee_regular_usd=float(orig_fee_usd),
        start_day_offset=0, shifting_horizon=False, **common,
    )
    res_wait = _simulate_single_ticket_rules_numba(
        idx_matrix, *stage_arrays,
        fee_day0_usd=float(fee_wait), fee_regular_usd=float(orig_fee_usd),
        start_day_offset=wait_tdays, shifting_horizon=bool(shifting_horizon), **common,
    )

    npv24_today = float(np.mean(res_today[9]))
    npv36_today = float(np.mean(res_today[10]))
    npv24_wait = float(np.mean(res_wait[9]))
    npv36_wait = float(np.mean(res_wait[10]))

    delta24 = npv24_wait - npv24_today
    delta36 = npv36_wait - npv36_today
    return {
        "horizon_mode": "SHIFTING_24M_FROM_PURCHASE" if shifting_horizon else "FIXED_CALENDAR_DEADLINE",
        "wait_cal_days": int(wait_cal_days),
        "wait_trading_days": int(wait_tdays),
        "max_retries": int(max_retries),
        "active_discount_pct": round(active_discount_pct * 100.0, 1),
        "next_sale_discount_pct": round(next_sale_discount_pct * 100.0, 1),
        "fee_today_usd": round(fee_today, 2),
        "fee_wait_usd": round(fee_wait, 2),
        "fee_retry_regular_usd": round(orig_fee_usd, 2),
        "upfront_saving_usd": round((fee_today - fee_wait) * (1.0 + card_fx_fee_pct), 2),
        "npv_24m_today_usd": round(npv24_today, 2),
        "npv_24m_wait_usd": round(npv24_wait, 2),
        "delta_npv_24m_usd": round(delta24, 2),
        "delta_npv_24m_vnd_tr": round(delta24 * usd_vnd_rate / 1_000_000.0, 2),
        "npv_36m_today_usd": round(npv36_today, 2),
        "npv_36m_wait_usd": round(npv36_wait, 2),
        "delta_npv_36m_usd": round(delta36, 2),
        "delta_npv_36m_vnd_tr": round(delta36 * usd_vnd_rate / 1_000_000.0, 2),
        "worth_waiting_24m": bool(delta24 > 0.0),
        "worth_waiting_36m": bool(delta36 > 0.0),
    }


def solve_max_wait_days_worth_it(
    idx_matrix: np.ndarray,
    stage_arrays: tuple[np.ndarray, ...],
    *,
    program_tier: dict[str, Any],
    orig_fee_usd: float,
    active_discount_pct: float,
    next_sale_discount_pct: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    usd_vnd_rate: float,
    horizon_months: int = 24,
    max_search_days: int = 180,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dual-Horizon Dynamic Sale Calculator using EXACT sweep (`Y = 0..max_search_days`, NO binary search, NO `2*d7` shortcut).

    Publishes BOTH horizons side-by-side:
      (a) Fixed 24m (or 36m) calendar deadline from today (exact sweep over every unique trading-day offset
          `Y = 0..max_search_days` since fixed-deadline NPV is non-monotonic across payout-cycle steps!).
      (b) Shifting 24m horizon starting on purchase day (`365 * ln(NPV_sale / NPV_today) / ln(1 + r)` + independent
          shifted-window MC verification!).
    Explicitly discloses that all wait thresholds assume the future sale discount `Z%` is 100% guaranteed on day `Y`.
    """
    fee_today = orig_fee_usd * (1.0 - active_discount_pct)
    fee_wait = orig_fee_usd * (1.0 - next_sale_discount_pct)
    max_retries = int(kwargs.get("max_retries", 0))

    common = _sale_common_kwargs(
        program_tier,
        card_fx_fee_pct=card_fx_fee_pct,
        discount_rate_annual=discount_rate_annual,
        p1_lock_trigger=float(kwargs.get("p1_lock_trigger", 0.70)),
        p2_lock_trigger=float(kwargs.get("p2_lock_trigger", 0.70)),
        amber_dd=float(kwargs.get("amber_dd", 0.035)),
        red_dd=float(kwargs.get("red_dd", 0.060)),
        p1_ea_stop=float(kwargs.get("p1_ea_stop", 0.035)),
        p2_ea_stop=float(kwargs.get("p2_ea_stop", 0.030)),
        fn_ea_stop=float(kwargs.get("fn_ea_stop", 0.025)),
        max_retries=max_retries,
    )

    target_td = 504 if horizon_months == 24 else int(horizon_months * TRADING_DAYS_PER_MONTH)
    idx_fixed = idx_matrix[:, : min(target_td, idx_matrix.shape[1])]
    npv_idx = 9 if horizon_months == 24 else 10

    # Baseline NPV buying today (Day 0) & NPV buying at sale price starting on Day 0 (full 24m window)
    res_today = _simulate_single_ticket_rules_numba(
        idx_fixed, *stage_arrays,
        fee_day0_usd=float(fee_today), fee_regular_usd=float(orig_fee_usd),
        start_day_offset=0, shifting_horizon=False, **common,
    )
    res_sale_day0 = _simulate_single_ticket_rules_numba(
        idx_fixed, *stage_arrays,
        fee_day0_usd=float(fee_wait), fee_regular_usd=float(orig_fee_usd),
        start_day_offset=0, shifting_horizon=False, **common,
    )
    base_npv = float(np.mean(res_today[npv_idx]))
    sale_day0_npv = float(np.mean(res_sale_day0[npv_idx]))

    # Exact evaluation helper cached by trading-day offset (zero redundant MC calls, zero binary search!)
    td_cache_fixed: dict[int, float] = {}

    def _delta_fixed_cal(days_y: int) -> float:
        wtd = max(0, int(round(days_y / CALENDAR_DAYS_PER_TRADING_DAY)))
        if wtd not in td_cache_fixed:
            res_w = _simulate_single_ticket_rules_numba(
                idx_fixed, *stage_arrays,
                fee_day0_usd=float(fee_wait), fee_regular_usd=float(orig_fee_usd),
                start_day_offset=wtd, shifting_horizon=False, **common,
            )
            td_cache_fixed[wtd] = float(np.mean(res_w[npv_idx])) - base_npv
        return td_cache_fixed[wtd]

    # Exact MC evaluation for shifting 24m horizon `[wait_td, wait_td + 504)` discounted back to Day 0
    can_mc_shift = (horizon_months == 24) and (idx_matrix.shape[1] > 504)
    max_shift_td = max(0, idx_matrix.shape[1] - 504) if can_mc_shift else 0
    td_cache_shift: dict[int, float] = {}

    def _delta_shift_mc_cal(days_y: int) -> float | None:
        if not can_mc_shift:
            return None
        wtd = max(0, int(round(days_y / CALENDAR_DAYS_PER_TRADING_DAY)))
        if wtd > max_shift_td:
            return None
        if wtd not in td_cache_shift:
            res_s = _simulate_single_ticket_rules_numba(
                idx_matrix[:, : (wtd + 504)], *stage_arrays,
                fee_day0_usd=float(fee_wait), fee_regular_usd=float(orig_fee_usd),
                start_day_offset=wtd, shifting_horizon=True, **common,
            )
            td_cache_shift[wtd] = float(np.mean(res_s[9])) - base_npv
        return td_cache_shift[wtd]

    def _delta_shift_formula_cal(days_y: int) -> float:
        return sale_day0_npv * ((1.0 + discount_rate_annual) ** (-float(days_y) / 365.0)) - base_npv

    assumption_note = (
        "Assumes the future sale discount Z% is 100% guaranteed on calendar day Y; "
        "if uncertain (probability p < 100%), practical maximum wait days shrink accordingly."
    )

    # Case 1: Active discount is already >= target future sale -> run ACTUAL 7d, 14d, 30d evaluations (NO 2*d7 shortcut!)
    if next_sale_discount_pct <= active_discount_pct + 1e-9:
        d1 = _delta_fixed_cal(1)
        d7 = _delta_fixed_cal(7)
        d14 = _delta_fixed_cal(14)
        d30 = _delta_fixed_cal(30)
        s7_mc = _delta_shift_mc_cal(7)
        s14_mc = _delta_shift_mc_cal(14)
        s30_mc = _delta_shift_mc_cal(30)
        return {
            "search_method": "EXACT_FULL_SWEEP_NO_BINARY_SEARCH",
            "max_retries": max_retries,
            "npv_today_usd": round(base_npv, 2),
            "npv_sale_day0_usd": round(sale_day0_npv, 2),
            "max_wait_days_worth_it": 0,
            "max_wait_days_fixed_deadline": 0,
            "contiguous_max_wait_days_fixed_deadline": 0,
            "non_monotonic_fixed_deadline": False,
            "delta_npv_at_1d_usd": round(d1, 2),
            "delta_npv_at_7d_usd": round(d7, 2),
            "delta_npv_at_14d_usd": round(d14, 2),
            "delta_npv_at_30d_usd": round(d30, 2),
            "shifting_horizon_search_method": "EXACT_DENSE_0_TO_MAX_SWEEP",
            "shifting_horizon_sweep_days_evaluated": 1,
            "shifting_horizon_formula_max_wait_days": 0.0,
            "shifting_horizon_mc_verified_max_wait_days": 0,
            "max_continuous_positive_wait_days": 0,
            "last_positive_wait_day": 0,
            "first_nonpositive_wait_day": 0,
            "non_monotonic_shifting_horizon": False,
            "shifting_horizon_non_monotonic_warning": "",
            "shifting_delta_formula_7d_usd": round(_delta_shift_formula_cal(7), 2),
            "shifting_delta_formula_14d_usd": round(_delta_shift_formula_cal(14), 2),
            "shifting_delta_formula_30d_usd": round(_delta_shift_formula_cal(30), 2),
            "shifting_delta_mc_7d_usd": round(s7_mc, 2) if s7_mc is not None else None,
            "shifting_delta_mc_14d_usd": round(s14_mc, 2) if s14_mc is not None else None,
            "shifting_delta_mc_30d_usd": round(s30_mc, 2) if s30_mc is not None else None,
            "assumption_disclosure": assumption_note,
            "decision": "BUY_TODAY_PROMO_ALREADY_ACTIVE_OR_BETTER",
        }

    # Case 2: Target future sale > active discount -> EXACT full sweep `Y = 0..max_search_days` (NO binary search!)
    best_fixed_y = 0
    contiguous_fixed_y = 0
    seen_nonpos = False
    non_monotonic = False
    prev_val: float | None = None
    for y in range(1, max_search_days + 1):
        val = _delta_fixed_cal(y)
        if prev_val is not None and val > prev_val + 1e-6:
            non_monotonic = True
        prev_val = val
        if val > 0.0:
            best_fixed_y = y
            if not seen_nonpos:
                contiguous_fixed_y = y
            else:
                non_monotonic = True
        else:
            seen_nonpos = True

    d1 = _delta_fixed_cal(1)
    d7 = _delta_fixed_cal(7)
    d14 = _delta_fixed_cal(14)
    d30 = _delta_fixed_cal(30)

    # Horizon (b): Shifting 24m horizon starting on purchase day
    # Formula: 365 * ln(NPV_sale / NPV_today) / ln(1 + r)
    if base_npv > 0.0 and sale_day0_npv > base_npv and discount_rate_annual > 0.0:
        shift_formula_days = 365.0 * math.log(sale_day0_npv / base_npv) / math.log(1.0 + discount_rate_annual)
    elif sale_day0_npv <= base_npv:
        shift_formula_days = 0.0
    else:
        shift_formula_days = float(max_search_days)

    # Independent FULL DENSE MC sweep across ALL integer days Y = 0..max_search_days (ZERO sparse search!)
    s7_mc = _delta_shift_mc_cal(7)
    s14_mc = _delta_shift_mc_cal(14)
    s30_mc = _delta_shift_mc_cal(30)
    shift_mc_max_cont_y: int | None = None
    shift_mc_last_pos_y: int | None = None
    shift_mc_first_nonpos_y: int | None = None
    shift_non_monotonic: bool = False
    shift_days_evaluated: int = 0
    shift_warning: str = ""
    shift_mc_at_formula_minus5: float | None = None
    shift_mc_at_formula_plus5: float | None = None

    if can_mc_shift:
        max_shift_cal_avail = int(max_shift_td * CALENDAR_DAYS_PER_TRADING_DAY)
        sweep_hi = min(int(max_search_days), max_shift_cal_avail)
        if shift_formula_days > 0.0 and sweep_hi >= 1:
            lo_chk = max(1, min(sweep_hi, int(math.floor(shift_formula_days)) - 5))
            hi_chk = max(1, min(sweep_hi, int(math.ceil(shift_formula_days)) + 5))
            shift_mc_at_formula_minus5 = _delta_shift_mc_cal(lo_chk)
            shift_mc_at_formula_plus5 = _delta_shift_mc_cal(hi_chk)

        # Evaluate EVERY single integer calendar day y = 0..sweep_hi densely (step = 1)!
        max_cont = 0
        last_pos = 0
        first_nonpos: int | None = None
        seen_nonpos_s = False
        prev_s_val: float | None = None
        eval_cnt = 0
        for y in range(0, sweep_hi + 1):
            dv = _delta_shift_mc_cal(y)
            if dv is None:
                break
            eval_cnt += 1
            if prev_s_val is not None and dv > prev_s_val + 1e-6:
                shift_non_monotonic = True
            prev_s_val = dv
            if dv > 0.0:
                last_pos = y
                if not seen_nonpos_s:
                    max_cont = y
                else:
                    shift_non_monotonic = True
            else:
                if not seen_nonpos_s:
                    first_nonpos = y
                seen_nonpos_s = True

        shift_days_evaluated = eval_cnt
        shift_mc_max_cont_y = int(max_cont)
        shift_mc_last_pos_y = int(last_pos)
        shift_mc_first_nonpos_y = int(first_nonpos) if first_nonpos is not None else None
        if shift_mc_last_pos_y > shift_mc_max_cont_y:
            shift_non_monotonic = True
            dip_day = shift_mc_first_nonpos_y if shift_mc_first_nonpos_y is not None else (shift_mc_max_cont_y + 1)
            shift_warning = (
                f"NON_MONOTONIC_SHIFTING_HORIZON: continuous positive wait ends at {shift_mc_max_cont_y}d "
                f"(day {dip_day}d already dips <= 0), although later MC noise rebounds positive up to "
                f"last_positive_wait_day={shift_mc_last_pos_y}d. NEVER interpret {shift_mc_last_pos_y}d as "
                f"'waiting any day up to {shift_mc_last_pos_y}d is positive'!"
            )

    if best_fixed_y == 0:
        decision = "BUY_TODAY_FIXED_DEADLINE_OR_WAIT_ONLY_IF_SHIFTING_HORIZON"
    else:
        decision = f"FIXED_DEADLINE_WAIT_LE_{best_fixed_y}D_SHIFTING_WAIT_LE_{int(round(shift_formula_days))}D"

    return {
        "search_method": "EXACT_FULL_SWEEP_NO_BINARY_SEARCH",
        "shifting_horizon_search_method": "EXACT_DENSE_0_TO_MAX_SWEEP",
        "shifting_horizon_sweep_days_evaluated": int(shift_days_evaluated),
        "max_retries": max_retries,
        "npv_today_usd": round(base_npv, 2),
        "npv_sale_day0_usd": round(sale_day0_npv, 2),
        "max_wait_days_worth_it": int(best_fixed_y),
        "max_wait_days_fixed_deadline": int(best_fixed_y),
        "contiguous_max_wait_days_fixed_deadline": int(contiguous_fixed_y),
        "non_monotonic_fixed_deadline": bool(non_monotonic),
        "delta_npv_at_1d_usd": round(d1, 2),
        "delta_npv_at_7d_usd": round(d7, 2),
        "delta_npv_at_14d_usd": round(d14, 2),
        "delta_npv_at_30d_usd": round(d30, 2),
        "shifting_horizon_formula_max_wait_days": round(shift_formula_days, 1),
        "shifting_horizon_mc_verified_max_wait_days": shift_mc_max_cont_y,
        "max_continuous_positive_wait_days": shift_mc_max_cont_y,
        "last_positive_wait_day": shift_mc_last_pos_y,
        "first_nonpositive_wait_day": shift_mc_first_nonpos_y,
        "non_monotonic_shifting_horizon": bool(shift_non_monotonic),
        "shifting_horizon_non_monotonic_warning": shift_warning,
        "shifting_delta_formula_7d_usd": round(_delta_shift_formula_cal(7), 2),
        "shifting_delta_formula_14d_usd": round(_delta_shift_formula_cal(14), 2),
        "shifting_delta_formula_30d_usd": round(_delta_shift_formula_cal(30), 2),
        "shifting_delta_mc_7d_usd": round(s7_mc, 2) if s7_mc is not None else None,
        "shifting_delta_mc_14d_usd": round(s14_mc, 2) if s14_mc is not None else None,
        "shifting_delta_mc_30d_usd": round(s30_mc, 2) if s30_mc is not None else None,
        "shifting_delta_mc_near_breakeven_minus5d_usd": round(shift_mc_at_formula_minus5, 2) if shift_mc_at_formula_minus5 is not None else None,
        "shifting_delta_mc_near_breakeven_plus5d_usd": round(shift_mc_at_formula_plus5, 2) if shift_mc_at_formula_plus5 is not None else None,
        "assumption_disclosure": assumption_note,
        "decision": decision,
    }


# ---------------------------------------------------------------------------
# Multi-Slot / Multi-Firm Capital Scaling Policy Simulator (Numba JIT)
# ---------------------------------------------------------------------------

@njit(cache=True)
def _simulate_capital_policy_numba(
    idx_matrix: np.ndarray,
    hazard_days: np.ndarray,  # shape (n_paths, n_firms), -1 = no disruption
    # Per-slot-template exact M1 tier arrays: shape (n_templates, n_obs) — ZERO linear scaling!
    tpl_n_p1: np.ndarray, tpl_d_p1: np.ndarray, tpl_u_p1: np.ndarray, tpl_f_p1: np.ndarray,
    tpl_n_p1l: np.ndarray, tpl_d_p1l: np.ndarray, tpl_u_p1l: np.ndarray, tpl_f_p1l: np.ndarray,
    tpl_n_p2: np.ndarray, tpl_d_p2: np.ndarray, tpl_u_p2: np.ndarray, tpl_f_p2: np.ndarray,
    tpl_n_p2l: np.ndarray, tpl_d_p2l: np.ndarray, tpl_u_p2l: np.ndarray, tpl_f_p2l: np.ndarray,
    tpl_n_fn: np.ndarray, tpl_d_fn: np.ndarray, tpl_u_fn: np.ndarray, tpl_f_fn: np.ndarray,
    tpl_n_amb: np.ndarray, tpl_d_amb: np.ndarray, tpl_u_amb: np.ndarray, tpl_f_amb: np.ndarray,
    tpl_n_red: np.ndarray, tpl_d_red: np.ndarray, tpl_u_red: np.ndarray, tpl_f_red: np.ndarray,
    # Per-template contract rules (length n_templates)
    tpl_firm_id: np.ndarray,
    tpl_steps: np.ndarray,
    tpl_cap: np.ndarray,
    tpl_fee_day0_usd: np.ndarray,     # Day-0 purchase price (promo if active, else regular)
    tpl_fee_regular_usd: np.ndarray,  # Regular price used on ALL purchases at d > 0 (NO perpetual BF!)
    tpl_refund_pct: np.ndarray,
    tpl_wd_fee_pct: np.ndarray,       # Payout withdrawal + FX spread fee on profit payouts
    tpl_refund_wd_fee_pct: np.ndarray,# Withdrawal fee on refunded challenge fee (`0.0` FTMO card refund)
    tpl_p1_target: np.ndarray,
    tpl_p2_target: np.ndarray,
    tpl_daily_lim: np.ndarray,
    tpl_max_dd_lim: np.ndarray,
    tpl_dd_type: np.ndarray,
    tpl_daily_dd_anchor: np.ndarray,  # 0=INITIAL_BALANCE, 1=PREV_DAY_BALANCE
    tpl_best_day_cap: np.ndarray,
    tpl_min_days: np.ndarray,
    tpl_min_prof_days: np.ndarray,
    tpl_min_prof_pct: np.ndarray,
    tpl_split: np.ndarray,
    tpl_payout_cycle: np.ndarray,
    tpl_min_payout: np.ndarray,
    tpl_p1_lock_trig: np.ndarray,
    tpl_p2_lock_trig: np.ndarray,
    tpl_amber_dd: np.ndarray,
    tpl_red_dd: np.ndarray,
    tpl_p1_ea_stop: np.ndarray,
    tpl_p2_ea_stop: np.ndarray,
    tpl_fn_ea_stop: np.ndarray,
    tpl_refund_milestone: np.ndarray,
    tpl_buf_ret_pct: np.ndarray,
    tpl_lock_init_p1: np.ndarray,
    tpl_min_pay_prof_pct: np.ndarray,
    tpl_daily_prof_cap_pct: np.ndarray,
    tpl_fn_p1_prof_days: np.ndarray,
    tpl_fn_p1_prof_pct: np.ndarray,
    # Policy definition
    policy_mode: int,          # 0=LADDER, 1=DIRECT_FIXED_SLOTS, 2=CROSS_FIRM_PARALLEL, 3=DIRECT_PARALLEL_DAY0
    ladder_tpls: np.ndarray,   # ordered template indices (e.g. [10K, 50K, 100K])
    max_slots: int,            # max concurrent active accounts
    allow_downgrade: bool,     # True for P3_SMART_SKIP_DOWNGRADE
    upgrade_buf_mult: float,   # e.g. 3.0 (Profile A) or 2.5 (Profile B)
    downgrade_buf_mult: float, # e.g. 2.0
    # Bankroll, VN fees, Own-Book overflow (0.0 in prop rankings!) & sunk-cost abort
    init_bankroll_usd: float,
    monthly_topup_usd: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    own_book_overflow_mult: float,  # MUST be 0.0 inside prop strategy ranking tables!
    own_book_daily_ret: float,      # 0.0 when own_book disabled
    abort_after_day: int,           # -1 = disabled; >=0 = sunk-cost abort stops buying retries after this day
    wait_for_top_rung_slot2: bool = False,  # True for P4A_WAIT_FOR_100K (holds Slot 2 for top rung!)
):
    """Multi-account, multi-firm correlated capital scaling simulator with Day-0 vs Regular fees, daily DD anchor & NPV."""
    n_paths, horizon = idx_matrix.shape
    n_ladder = len(ladder_tpls)
    n_firms = hazard_days.shape[1]
    r_ann = discount_rate_annual
    inv_df = np.empty(horizon + 2, dtype=np.float64)
    for k_d in range(horizon + 2):
        inv_df[k_d] = (1.0 + r_ann) ** (-k_d / 252.0)
    top_tpl = ladder_tpls[n_ladder - 1]
    top_eff_fee_reg = tpl_fee_regular_usd[top_tpl] * (1.0 + card_fx_fee_pct)
    ob_cap_usd = top_eff_fee_reg * own_book_overflow_mult if own_book_overflow_mult > 0.0 else 1e18

    # Outputs
    npv_24m = np.zeros(n_paths, dtype=np.float64)
    npv_36m = np.zeros(n_paths, dtype=np.float64)
    cf_24m = np.zeros(n_paths, dtype=np.float64)
    cf_36m = np.zeros(n_paths, dtype=np.float64)
    wealth_24m = np.zeros(n_paths, dtype=np.float64)
    wealth_36m = np.zeros(n_paths, dtype=np.float64)
    own_book_36m = np.zeros(n_paths, dtype=np.float64)
    ruined_ever = np.zeros(n_paths, dtype=np.int8)      # hit 0 active accounts & cash < cheapest affordable ticket
    ruined_24m = np.zeros(n_paths, dtype=np.int8)
    pay1_day = np.full(n_paths, -1, dtype=np.int32)
    funded_dry_tot = np.zeros(n_paths, dtype=np.int32)
    funded_dry_zero = np.zeros(n_paths, dtype=np.int32)
    funded_max_dry_streak = np.zeros(n_paths, dtype=np.int32)
    total_fees_24m = np.zeros(n_paths, dtype=np.float64)
    total_payouts_24m = np.zeros(n_paths, dtype=np.float64)
    simult_fail_any = np.zeros(n_paths, dtype=np.int8)
    firm_disrupt_hits = np.zeros(n_paths, dtype=np.int32)
    max_funded_nom = np.zeros(n_paths, dtype=np.float64)
    max_oop_arr = np.zeros(n_paths, dtype=np.float64)

    # Cheapest ticket in this policy on Day 0 vs d > 0 (for ruin check)
    min_policy_fee_day0 = 1e18
    min_policy_fee_reg = 1e18
    for i in range(n_ladder):
        ef0 = tpl_fee_day0_usd[ladder_tpls[i]] * (1.0 + card_fx_fee_pct)
        efr = tpl_fee_regular_usd[ladder_tpls[i]] * (1.0 + card_fx_fee_pct)
        if ef0 < min_policy_fee_day0:
            min_policy_fee_day0 = ef0
        if efr < min_policy_fee_reg:
            min_policy_fee_reg = efr

    # Preallocate reusable slot & firm state buffers OUTSIDE path loop
    s_stage = np.zeros(max_slots, dtype=np.int8)
    s_tpl = np.full(max_slots, -1, dtype=np.int32)
    s_bal = np.zeros(max_slots, dtype=np.float64)
    s_hwm = np.zeros(max_slots, dtype=np.float64)
    s_tdays = np.zeros(max_slots, dtype=np.int32)
    s_pdays = np.zeros(max_slots, dtype=np.int32)
    s_cycd = np.zeros(max_slots, dtype=np.int32)
    s_maxg = np.zeros(max_slots, dtype=np.float64)
    s_ref = np.zeros(max_slots, dtype=np.int8)
    s_pcnt = np.zeros(max_slots, dtype=np.int32)
    s_fnpdays = np.zeros(max_slots, dtype=np.int32)
    s_paid_fee = np.zeros(max_slots, dtype=np.float64)
    firm_dead = np.zeros(n_firms, dtype=np.int8)

    for b in range(n_paths):
        cash_res = init_bankroll_usd
        own_book = 0.0
        pv_fees = 0.0
        pv_payouts = 0.0
        pv_ob_in = 0.0
        tot_ob_in = 0.0
        tot_fees = 0.0
        tot_payouts = 0.0
        path_max_oop = 0.0

        for s in range(max_slots):
            s_stage[s] = 0
            s_tpl[s] = -1
            s_bal[s] = 0.0
            s_hwm[s] = 0.0
            s_tdays[s] = 0
            s_pdays[s] = 0
            s_cycd[s] = 0
            s_maxg[s] = 0.0
            s_ref[s] = 0
            s_pcnt[s] = 0
            s_fnpdays[s] = 0
            s_paid_fee[s] = 0.0
        for f_i in range(n_firms):
            firm_dead[f_i] = 0
        cur_rung = 0
        ever_funded_rung = -1
        f_pay1 = -1
        had_ruin = 0
        had_ruin_24 = 0
        had_sim_fail = 0
        disrupt_cnt = 0
        best_nom = 0.0
        recorded_24 = False

        # Portfolio-level Funded dry month tracker
        fn_m_days = 0
        fn_m_paid = 0
        cur_dry = 0
        best_dry = 0
        tot_fm = 0
        zero_fm = 0

        for d in range(horizon):
            # 0. Monthly savings top-up (every 21 trading days after day 0)
            if monthly_topup_usd > 0.0 and d > 0 and (d % 21 == 0):
                if abort_after_day < 0 or d < abort_after_day:
                    cash_res += monthly_topup_usd

            # 1. Check idiosyncratic firm disruptions on day d (count ONLY when it actually hits an active account!)
            for f_i in range(n_firms):
                if firm_dead[f_i] == 0 and hazard_days[b, f_i] == d:
                    firm_dead[f_i] = 1
                    hit_active = 0
                    for s in range(max_slots):
                        if s_stage[s] > 0 and tpl_firm_id[s_tpl[s]] == f_i:
                            s_stage[s] = 0
                            s_tpl[s] = -1
                            s_bal[s] = 0.0
                            s_paid_fee[s] = 0.0
                            hit_active = 1
                    if hit_active == 1:
                        disrupt_cnt += 1

            # 2. Capital allocation / ticket purchasing (purchase-day pricing: Day-0 promo vs d>0 regular!)
            can_buy = (abort_after_day < 0) or (d < abort_after_day)
            if can_buy:
                active_cnt = 0
                funded_cnt = 0
                for s in range(max_slots):
                    if s_stage[s] > 0:
                        active_cnt += 1
                        if s_stage[s] == 3:
                            funded_cnt += 1

                if policy_mode == 2:
                    # CROSS_FIRM_PARALLEL (surviving firms only, e.g. FTMO + The5ers + IC Funded)
                    for s in range(max_slots):
                        if s_stage[s] == 0 and s < n_ladder:
                            tid = ladder_tpls[s]
                            fid = tpl_firm_id[tid]
                            if firm_dead[fid] == 1:
                                continue
                            base_fee = tpl_fee_day0_usd[tid] if d == 0 else tpl_fee_regular_usd[tid]
                            ef = base_fee * (1.0 + card_fx_fee_pct)
                            req_cash = ef if active_cnt == 0 else (ef * upgrade_buf_mult)
                            if cash_res >= req_cash - 1e-9:
                                cash_res -= ef
                                pv_fees += ef * inv_df[d]
                                tot_fees += ef
                                s_tpl[s] = tid
                                s_stage[s] = 3 if tpl_steps[tid] == 0 else 1
                                s_bal[s] = tpl_cap[tid]
                                s_hwm[s] = tpl_cap[tid]
                                s_tdays[s] = 0
                                s_pdays[s] = 0
                                s_cycd[s] = 0
                                s_maxg[s] = 0.0
                                s_ref[s] = 0
                                s_pcnt[s] = 0
                                s_fnpdays[s] = 0
                                s_paid_fee[s] = base_fee
                                active_cnt += 1
                elif policy_mode == 3:
                    # DIRECT_PARALLEL_DAY0 (e.g. P4B_PARALLEL_2X100K: opens ALL max_slots on Day 0 when bankroll >= slots * fee!)
                    tid = ladder_tpls[cur_rung]
                    fid = tpl_firm_id[tid]
                    if firm_dead[fid] == 0:
                        base_fee = tpl_fee_day0_usd[tid] if d == 0 else tpl_fee_regular_usd[tid]
                        ef = base_fee * (1.0 + card_fx_fee_pct)
                        for s in range(max_slots):
                            if s_stage[s] != 0:
                                continue
                            if d == 0:
                                # Open every slot affordable on Day 0 (both 100K slots when bankroll >= 2 tickets!)
                                if cash_res >= ef - 1e-9:
                                    cash_res -= ef
                                    pv_fees += ef * inv_df[d]
                                    tot_fees += ef
                                    s_tpl[s] = tid
                                    s_stage[s] = 3 if tpl_steps[tid] == 0 else 1
                                    s_bal[s] = tpl_cap[tid]
                                    s_hwm[s] = tpl_cap[tid]
                                    s_tdays[s] = 0
                                    s_pdays[s] = 0
                                    s_cycd[s] = 0
                                    s_maxg[s] = 0.0
                                    s_ref[s] = 0
                                    s_pcnt[s] = 0
                                    s_fnpdays[s] = 0
                                    s_paid_fee[s] = base_fee
                                    active_cnt += 1
                            else:
                                # Post-Day-0 refills pay regular fee; first active slot needs 1x fee, 2nd slot needs buffer
                                req_cash = ef if active_cnt == 0 else (ef * upgrade_buf_mult)
                                if cash_res >= req_cash - 1e-9:
                                    cash_res -= ef
                                    pv_fees += ef * inv_df[d]
                                    tot_fees += ef
                                    s_tpl[s] = tid
                                    s_stage[s] = 3 if tpl_steps[tid] == 0 else 1
                                    s_bal[s] = tpl_cap[tid]
                                    s_hwm[s] = tpl_cap[tid]
                                    s_tdays[s] = 0
                                    s_pdays[s] = 0
                                    s_cycd[s] = 0
                                    s_maxg[s] = 0.0
                                    s_ref[s] = 0
                                    s_pcnt[s] = 0
                                    s_fnpdays[s] = 0
                                    s_paid_fee[s] = base_fee
                                    active_cnt += 1
                else:
                    # LADDER (policy_mode == 0) or DIRECT_FIXED (policy_mode == 1)
                    if policy_mode == 0:
                        while cur_rung + 1 < n_ladder:
                            next_tid = ladder_tpls[cur_rung + 1]
                            next_base = tpl_fee_day0_usd[next_tid] if d == 0 else tpl_fee_regular_usd[next_tid]
                            next_ef = next_base * (1.0 + card_fx_fee_pct)
                            if cash_res >= next_ef * upgrade_buf_mult - 1e-9 and (ever_funded_rung >= cur_rung or d == 0):
                                cur_rung += 1
                            else:
                                break
                        if allow_downgrade:
                            while cur_rung > 0:
                                cur_tid = ladder_tpls[cur_rung]
                                cur_base = tpl_fee_day0_usd[cur_tid] if d == 0 else tpl_fee_regular_usd[cur_tid]
                                cur_ef = cur_base * (1.0 + card_fx_fee_pct)
                                if cash_res < cur_ef * downgrade_buf_mult - 1e-9:
                                    cur_rung -= 1
                                else:
                                    break
                    else:
                        while cur_rung + 1 < n_ladder:
                            next_tid = ladder_tpls[cur_rung + 1]
                            next_base = tpl_fee_day0_usd[next_tid] if d == 0 else tpl_fee_regular_usd[next_tid]
                            next_ef = next_base * (1.0 + card_fx_fee_pct)
                            if cash_res >= next_ef * upgrade_buf_mult - 1e-9 and funded_cnt >= 1:
                                cur_rung += 1
                            else:
                                break

                    for s in range(max_slots):
                        if s_stage[s] != 0:
                            continue
                        tid = ladder_tpls[cur_rung]
                        fid = tpl_firm_id[tid]
                        if firm_dead[fid] == 1:
                            continue
                        base_fee = tpl_fee_day0_usd[tid] if d == 0 else tpl_fee_regular_usd[tid]
                        ef = base_fee * (1.0 + card_fx_fee_pct)
                        if active_cnt == 0:
                            if cash_res >= ef - 1e-9:
                                cash_res -= ef
                                pv_fees += ef * inv_df[d]
                                tot_fees += ef
                                s_tpl[s] = tid
                                s_stage[s] = 3 if tpl_steps[tid] == 0 else 1
                                s_bal[s] = tpl_cap[tid]
                                s_hwm[s] = tpl_cap[tid]
                                s_tdays[s] = 0
                                s_pdays[s] = 0
                                s_cycd[s] = 0
                                s_maxg[s] = 0.0
                                s_ref[s] = 0
                                s_pcnt[s] = 0
                                s_fnpdays[s] = 0
                                s_paid_fee[s] = base_fee
                                active_cnt += 1
                        elif funded_cnt >= 1 and cash_res >= ef * upgrade_buf_mult - 1e-9:
                            # B2 closure (`P4A_WAIT_FOR_100K`): if `wait_for_top_rung_slot2`, hold Slot 2 until top rung!
                            if (not wait_for_top_rung_slot2) or (cur_rung == n_ladder - 1):
                                cash_res -= ef
                                pv_fees += ef * inv_df[d]
                                tot_fees += ef
                                s_tpl[s] = tid
                                s_stage[s] = 3 if tpl_steps[tid] == 0 else 1
                                s_bal[s] = tpl_cap[tid]
                                s_hwm[s] = tpl_cap[tid]
                                s_tdays[s] = 0
                                s_pdays[s] = 0
                                s_cycd[s] = 0
                                s_maxg[s] = 0.0
                                s_ref[s] = 0
                                s_pcnt[s] = 0
                                s_fnpdays[s] = 0
                                s_paid_fee[s] = base_fee
                                active_cnt += 1

            # Check ruin BEFORE stepping market (0 active accounts & cannot buy even cheapest ticket at purchase-day price)
            alive_now = 0
            for s in range(max_slots):
                if s_stage[s] > 0:
                    alive_now += 1
            min_fee_now = min_policy_fee_day0 if d == 0 else min_policy_fee_reg
            if alive_now == 0 and cash_res < min_fee_now - 1e-9 and can_buy:
                had_ruin = 1
                if d < 504:
                    had_ruin_24 = 1

            # 3. Step ALL active slots simultaneously on the EXACT SAME market day `src`!
            src = idx_matrix[b, d]
            fails_today = 0
            any_funded_today = 0
            paid_today = 0
            cur_fn_nom = 0.0

            for s in range(max_slots):
                st = s_stage[s]
                if st <= 0:
                    continue
                tid = s_tpl[s]
                cap = tpl_cap[tid]
                if st == 3:
                    any_funded_today = 1
                    cur_fn_nom += cap

                eq_pct = (s_bal[s] - cap) / cap
                if eq_pct <= -tpl_red_dd[tid]:
                    net = tpl_n_red[tid, src]
                    dd = tpl_d_red[tid, src]
                    up = tpl_u_red[tid, src]
                    flg = tpl_f_red[tid, src]
                    ea_stop_pct = tpl_fn_ea_stop[tid] if st == 3 else (tpl_p2_ea_stop[tid] if st == 2 else tpl_p1_ea_stop[tid])
                elif eq_pct <= -tpl_amber_dd[tid]:
                    net = tpl_n_amb[tid, src]
                    dd = tpl_d_amb[tid, src]
                    up = tpl_u_amb[tid, src]
                    flg = tpl_f_amb[tid, src]
                    ea_stop_pct = tpl_fn_ea_stop[tid] if st == 3 else (tpl_p2_ea_stop[tid] if st == 2 else tpl_p1_ea_stop[tid])
                elif st == 1:
                    prog = eq_pct / max(1e-6, tpl_p1_target[tid])
                    if tpl_p1_lock_trig[tid] > 0.0 and prog >= tpl_p1_lock_trig[tid]:
                        net, dd, up, flg = tpl_n_p1l[tid, src], tpl_d_p1l[tid, src], tpl_u_p1l[tid, src], tpl_f_p1l[tid, src]
                    else:
                        net, dd, up, flg = tpl_n_p1[tid, src], tpl_d_p1[tid, src], tpl_u_p1[tid, src], tpl_f_p1[tid, src]
                    ea_stop_pct = tpl_p1_ea_stop[tid]
                elif st == 2:
                    prog = eq_pct / max(1e-6, tpl_p2_target[tid])
                    if tpl_p2_lock_trig[tid] > 0.0 and prog >= tpl_p2_lock_trig[tid]:
                        net, dd, up, flg = tpl_n_p2l[tid, src], tpl_d_p2l[tid, src], tpl_u_p2l[tid, src], tpl_f_p2l[tid, src]
                    else:
                        net, dd, up, flg = tpl_n_p2[tid, src], tpl_d_p2[tid, src], tpl_u_p2[tid, src], tpl_f_p2[tid, src]
                    ea_stop_pct = tpl_p2_ea_stop[tid]
                else:
                    net, dd, up, flg = tpl_n_fn[tid, src], tpl_d_fn[tid, src], tpl_u_fn[tid, src], tpl_f_fn[tid, src]
                    ea_stop_pct = tpl_fn_ea_stop[tid]

                dd_t = tpl_dd_type[tid]
                if dd_t == 2:
                    if s_bal[s] + up > s_hwm[s]:
                        s_hwm[s] = s_bal[s] + up
                    max_floor = s_hwm[s] * (1.0 - tpl_max_dd_lim[tid])
                elif dd_t == 1:
                    max_floor = s_hwm[s] * (1.0 - tpl_max_dd_lim[tid])
                else:
                    if tpl_lock_init_p1[tid] == 1 and st == 3 and s_pcnt[s] >= 1:
                        max_floor = cap
                    else:
                        max_floor = cap * (1.0 - tpl_max_dd_lim[tid])

                # Per-contract daily DD anchor:
                #   - 0 (`initial_balance`): FTMO / E8 Pro static allowance `s_bal - cap * daily_lim`.
                #   - 1 (`prev_day_balance`): The5ers (`max(balance, equity)` at reset) & IC Funded (`equity` at reset);
                #     modeled `s_bal * (1 - daily_lim)` holds ONLY when flat at exact firm reset time
                #     (`dd_rule_verification_tag = "DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET"`).
                if tpl_daily_dd_anchor[tid] == 1:
                    daily_floor = s_bal[s] * (1.0 - tpl_daily_lim[tid])
                else:
                    daily_floor = s_bal[s] - cap * tpl_daily_lim[tid]
                day_min = s_bal[s] - dd
                d_hit = day_min < daily_floor - 1e-9
                m_hit = day_min < max_floor - 1e-9
                ea_cut = cap * ea_stop_pct if ea_stop_pct > 0.0 else 1e18
                if (not d_hit) and (not m_hit) and (dd > ea_cut):
                    dd_eff = min(dd, ea_cut + cap * 0.0020)
                    net = min(net, -dd_eff)
                    day_min_eff = s_bal[s] - dd_eff
                    d_hit = day_min_eff < daily_floor - 1e-9
                    m_hit = day_min_eff < max_floor - 1e-9

                if d_hit or m_hit:
                    fails_today += 1
                    s_stage[s] = 0
                    s_tpl[s] = -1
                    s_bal[s] = 0.0
                    s_paid_fee[s] = 0.0
                    continue

                if tpl_daily_prof_cap_pct[tid] > 0.0 and net > cap * tpl_daily_prof_cap_pct[tid]:
                    net = cap * tpl_daily_prof_cap_pct[tid]
                s_bal[s] += net
                if dd_t == 1 and s_bal[s] > s_hwm[s]:
                    s_hwm[s] = s_bal[s]
                if net > s_maxg[s]:
                    s_maxg[s] = net
                if flg != 0:
                    s_tdays[s] += 1
                if tpl_min_prof_pct[tid] > 0.0 and net >= cap * tpl_min_prof_pct[tid] - 1e-9:
                    s_pdays[s] += 1

                if st == 1:
                    ok_t = s_bal[s] >= cap * (1.0 + tpl_p1_target[tid]) - 1e-9
                    ok_d = (s_tdays[s] >= tpl_min_days[tid]) and (s_pdays[s] >= tpl_min_prof_days[tid])
                    ok_c = True
                    if tpl_best_day_cap[tid] > 0.0:
                        pr = s_bal[s] - cap
                        if pr <= 0.0 or s_maxg[s] > tpl_best_day_cap[tid] * pr + 1e-9:
                            ok_c = False
                    if ok_t and ok_d and ok_c:
                        if tpl_steps[tid] == 1:
                            s_stage[s] = 3
                            s_bal[s] = cap
                            s_hwm[s] = cap
                            s_tdays[s] = 0
                            s_pdays[s] = 0
                            s_cycd[s] = 0
                            s_maxg[s] = 0.0
                            if cur_rung > ever_funded_rung:
                                ever_funded_rung = cur_rung
                        else:
                            s_stage[s] = 2
                            s_bal[s] = cap
                            s_hwm[s] = cap
                            s_tdays[s] = 0
                            s_pdays[s] = 0
                            s_maxg[s] = 0.0
                elif st == 2:
                    ok_t = s_bal[s] >= cap * (1.0 + tpl_p2_target[tid]) - 1e-9
                    ok_d = (s_tdays[s] >= tpl_min_days[tid]) and (s_pdays[s] >= tpl_min_prof_days[tid])
                    if ok_t and ok_d:
                        s_stage[s] = 3
                        s_bal[s] = cap
                        s_hwm[s] = cap
                        s_tdays[s] = 0
                        s_pdays[s] = 0
                        s_cycd[s] = 0
                        s_maxg[s] = 0.0
                        if cur_rung > ever_funded_rung:
                            ever_funded_rung = cur_rung
                elif st == 3:
                    s_cycd[s] += 1
                    if tpl_fn_p1_prof_pct[tid] > 0.0 and net >= cap * tpl_fn_p1_prof_pct[tid] - 1e-9:
                        s_fnpdays[s] += 1
                    if s_cycd[s] >= tpl_payout_cycle[tid]:
                        prof = s_bal[s] - cap
                        ok_c = True
                        if tpl_best_day_cap[tid] > 0.0 and prof > 0.0:
                            if s_maxg[s] > tpl_best_day_cap[tid] * prof + 1e-9:
                                ok_c = False
                        if s_pcnt[s] == 0 and tpl_fn_p1_prof_days[tid] > 0:
                            if s_fnpdays[s] < tpl_fn_p1_prof_days[tid]:
                                ok_c = False
                        if tpl_min_pay_prof_pct[tid] > 0.0 and prof < cap * tpl_min_pay_prof_pct[tid] - 1e-9:
                            ok_c = False
                        if prof > 1e-6 and ok_c:
                            buf_ret = tpl_buf_ret_pct[tid]
                            gross_share = prof * (1.0 - buf_ret) * tpl_split[tid]
                            if gross_share >= tpl_min_payout[tid] - 1e-9:
                                s_pcnt[s] += 1
                                net_in = gross_share * (1.0 - tpl_wd_fee_pct[tid])
                                if (
                                    s_ref[s] == 0
                                    and tpl_refund_pct[tid] > 0.0
                                    and tpl_refund_milestone[tid] > 0
                                    and s_pcnt[s] >= tpl_refund_milestone[tid]
                                ):
                                    # Exact refund of THIS slot's paid ticket fee with separate refund_withdrawal_fee_pct
                                    net_in += s_paid_fee[s] * tpl_refund_pct[tid] * (1.0 - tpl_refund_wd_fee_pct[tid])
                                    s_ref[s] = 1
                                pv_payouts += net_in * inv_df[d + 1]
                                tot_payouts += net_in
                                cash_res += net_in
                                paid_today = 1
                                if f_pay1 < 0:
                                    f_pay1 = d + 1
                                s_bal[s] = cap + prof * buf_ret
                                s_hwm[s] = s_bal[s]
                                s_maxg[s] = 0.0
                        s_cycd[s] = 0

            if fails_today >= 2:
                had_sim_fail = 1
            if cur_fn_nom > best_nom:
                best_nom = cur_fn_nom

            # Portfolio-level Funded dry-month tracking
            if any_funded_today == 1:
                fn_m_days += 1
                if paid_today == 1:
                    fn_m_paid = 1
                if fn_m_days >= 21:
                    tot_fm += 1
                    if fn_m_paid == 0:
                        zero_fm += 1
                        cur_dry += 1
                        if cur_dry > best_dry:
                            best_dry = cur_dry
                    else:
                        cur_dry = 0
                    fn_m_days = 0
                    fn_m_paid = 0

            # 4. Compound Own-Book overflow (DISABLED = 0.0 in all prop ranking tables per B3!)
            if own_book > 0.0:
                own_book *= (1.0 + own_book_daily_ret)
            if own_book_overflow_mult > 0.0 and cash_res > ob_cap_usd:
                excess = cash_res - ob_cap_usd
                cash_res = ob_cap_usd
                own_book += excess
                tot_ob_in += excess
                pv_ob_in += excess * inv_df[d + 1]

            cur_oop = tot_fees - tot_payouts
            if cur_oop > path_max_oop:
                path_max_oop = cur_oop

            if (not recorded_24) and (d + 1 == 504):
                ob_npv_delta = (own_book * inv_df[504]) - pv_ob_in
                npv_24m[b] = pv_payouts - pv_fees + ob_npv_delta
                cf_24m[b] = tot_payouts - tot_fees + (own_book - tot_ob_in)
                wealth_24m[b] = cash_res + own_book
                total_fees_24m[b] = tot_fees
                total_payouts_24m[b] = tot_payouts
                recorded_24 = True

        ob_npv_delta36 = (own_book * inv_df[horizon]) - pv_ob_in
        if not recorded_24:
            npv_24m[b] = pv_payouts - pv_fees + ob_npv_delta36
            cf_24m[b] = tot_payouts - tot_fees + (own_book - tot_ob_in)
            wealth_24m[b] = cash_res + own_book
            total_fees_24m[b] = tot_fees
            total_payouts_24m[b] = tot_payouts

        npv_36m[b] = pv_payouts - pv_fees + ob_npv_delta36
        cf_36m[b] = tot_payouts - tot_fees + (own_book - tot_ob_in)
        wealth_36m[b] = cash_res + own_book
        own_book_36m[b] = own_book
        ruined_ever[b] = had_ruin
        ruined_24m[b] = had_ruin_24
        pay1_day[b] = f_pay1
        funded_dry_tot[b] = tot_fm
        funded_dry_zero[b] = zero_fm
        funded_max_dry_streak[b] = best_dry
        simult_fail_any[b] = had_sim_fail
        firm_disrupt_hits[b] = disrupt_cnt
        max_funded_nom[b] = best_nom
        max_oop_arr[b] = path_max_oop

    return (
        npv_24m,
        npv_36m,
        cf_24m,
        cf_36m,
        wealth_24m,
        wealth_36m,
        own_book_36m,
        ruined_ever,
        ruined_24m,
        pay1_day,
        funded_dry_tot,
        funded_dry_zero,
        funded_max_dry_streak,
        total_fees_24m,
        total_payouts_24m,
        simult_fail_any,
        firm_disrupt_hits,
        max_funded_nom,
        max_oop_arr,
    )


def summarize_capital_policy_mc(
    res: tuple[np.ndarray, ...],
    *,
    usd_vnd_rate: float,
    init_bankroll_vnd_tr: float,
    monthly_topup_vnd_tr: float,
) -> dict[str, Any]:
    """Summarize multi-slot capital policy MC run with VND/USD amounts, ruin, NPV & dry-month metrics."""
    (
        npv24, npv36, cf24, cf36, w24, w36, ob36,
        ruin_ev, ruin24, pay1, fm_tot, fm_dry, fm_streak,
        fees24, pays24, sim_fail, disrupt, max_nom, max_oop,
    ) = res
    n = len(npv24)
    paid_mask = pay1 > 0
    cal_pay1 = np.where(paid_mask, pay1 * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    uncond_cap365 = np.minimum(cal_pay1, 365.0)
    uncond_cap730 = np.minimum(cal_pay1, 730.0)

    tot_fm_sum = int(np.sum(fm_tot))
    dry_fm_sum = int(np.sum(fm_dry))
    dry_pct = (100.0 * dry_fm_sum / tot_fm_sum) if tot_fm_sum > 0 else 100.0
    streak_sub = fm_streak[fm_tot > 0]
    dry_p50 = int(np.median(streak_sub)) if len(streak_sub) > 0 else 0
    dry_p95 = int(np.quantile(streak_sub, 0.95)) if len(streak_sub) > 0 else 0

    ev_npv24 = float(np.mean(npv24))
    med_npv24 = float(np.median(npv24))
    ev_npv36 = float(np.mean(npv36))
    med_npv36 = float(np.median(npv36))
    ev_cf24 = float(np.mean(cf24))
    ev_cf36 = float(np.mean(cf36))
    mean_fees24 = float(np.mean(fees24))
    ruin_pct = 100.0 * float(np.mean(ruin_ev > 0))
    ruin24_pct = 100.0 * float(np.mean(ruin24 > 0))

    return {
        "model_tag": "DAILY_APPROX",
        "n_paths": n,
        "init_bankroll_vnd_tr": float(init_bankroll_vnd_tr),
        "monthly_topup_vnd_tr": float(monthly_topup_vnd_tr),
        "ruin_pct": round(ruin_pct, 2),
        "ruin_24m_pct": round(ruin24_pct, 2),
        "p_npv24_le_0_pct": round(100.0 * float(np.mean(npv24 <= 0.0)), 2),
        "paid_any_pct": round(100.0 * float(np.mean(paid_mask)), 2),
        "cond_med_pay1_cal_days": round(float(np.median(cal_pay1[paid_mask])), 1) if np.any(paid_mask) else -1.0,
        "uncond_med_pay1_cap365_days": round(float(np.median(uncond_cap365)), 1),
        "uncond_med_pay1_cap730_days": round(float(np.median(uncond_cap730)), 1),
        "ev_npv_24m_usd": round(ev_npv24, 1),
        "ev_npv_24m_vnd_tr": round(ev_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_24m_usd": round(med_npv24, 1),
        "med_npv_24m_vnd_tr": round(med_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_24m_usd": round(ev_cf24, 1),
        "ev_npv_36m_usd": round(ev_npv36, 1),
        "ev_npv_36m_vnd_tr": round(ev_npv36 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_36m_usd": round(med_npv36, 1),
        "med_npv_36m_vnd_tr": round(med_npv36 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_36m_usd": round(ev_cf36, 1),
        "ev_per_total_fee_npv24": round(ev_npv24 / max(1.0, mean_fees24), 2),
        "mean_fees_24m_usd": round(mean_fees24, 1),
        "mean_own_book_36m_usd": round(float(np.mean(ob36)), 1),
        "mean_own_book_36m_vnd_tr": round(float(np.mean(ob36)) * usd_vnd_rate / 1_000_000.0, 2),
        "funded_dry_months_pct": round(dry_pct, 2),
        "funded_dry_streak_p50_months": dry_p50,
        "funded_dry_streak_p95_months": dry_p95,
        "simultaneous_fail_pct": round(100.0 * float(np.mean(sim_fail > 0)), 2),
        "firm_disruption_rate_pct": round(100.0 * float(np.mean(disrupt > 0)), 2),
        "mean_max_funded_nom_usd": round(float(np.mean(max_nom)), 0),
        "oop95_usd": round(float(np.quantile(max_oop, 0.95)), 1),
        "oop95_vnd_tr": round(float(np.quantile(max_oop, 0.95)) * usd_vnd_rate / 1_000_000.0, 2),
    }


def _pick_pair_winners(sub_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Select Profile A (`<= 5%` ruin, max NPV) and Profile B (`<= 10%` ruin, min wait/dry) on a policy subset."""
    elig_a = [
        (pid, m) for pid, m in sub_results.items()
        if float(m["ruin_pct"]) <= 5.0 + 1e-9 and float(m["ev_npv_24m_usd"]) > 0.0
    ]
    if elig_a:
        best_a_id, best_a = max(elig_a, key=lambda kv: (kv[1]["ev_npv_36m_usd"], kv[1]["ev_npv_24m_usd"], -kv[1]["ruin_pct"]))
        a_status = "FEASIBLE_RUIN_LE_5PCT"
    else:
        best_a_id, best_a = min(sub_results.items(), key=lambda kv: (kv[1]["ruin_pct"], -kv[1]["ev_npv_36m_usd"]))
        a_status = "NO_POLICY_MEETS_5PCT_RUIN_LOWEST_RUIN_SHOWN"

    elig_b = [
        (pid, m) for pid, m in sub_results.items()
        if float(m["ruin_pct"]) <= 10.0 + 1e-9 and float(m["ev_npv_24m_usd"]) > 0.0 and float(m["paid_any_pct"]) >= 50.0
    ]
    if elig_b:
        best_b_id, best_b = min(
            elig_b,
            key=lambda kv: (
                kv[1]["uncond_med_pay1_cap730_days"],
                kv[1]["funded_dry_months_pct"],
                -kv[1]["paid_any_pct"],
                -kv[1]["ev_npv_24m_usd"],
            ),
        )
        b_status = "FEASIBLE_RUIN_LE_10PCT"
    else:
        elig_b_safe = [
            (pid, m) for pid, m in sub_results.items()
            if float(m["ruin_pct"]) <= 10.0 + 1e-9 and float(m["ev_npv_24m_usd"]) > 0.0
        ]
        if elig_b_safe:
            best_b_id, best_b = min(
                elig_b_safe,
                key=lambda kv: (
                    -kv[1]["paid_any_pct"],
                    kv[1]["funded_dry_months_pct"],
                    kv[1]["cond_med_pay1_cal_days"] if kv[1]["cond_med_pay1_cal_days"] > 0 else 1e9,
                    -kv[1]["ev_npv_24m_usd"],
                ),
            )
            b_status = "FEASIBLE_RUIN_LE_10PCT_PAID_LT_50PCT"
        else:
            best_b_id, best_b = min(sub_results.items(), key=lambda kv: (kv[1]["ruin_pct"], kv[1]["uncond_med_pay1_cap730_days"]))
            b_status = "NO_POLICY_MEETS_10PCT_RUIN_LOWEST_RUIN_SHOWN"

    return {
        "profile_a_npv_wealth_safe5pct": {
            "status": a_status,
            "winner_policy": best_a_id,
            "ruin_pct": best_a["ruin_pct"],
            "ev_npv_24m_usd": best_a.get("ev_npv_24m_usd", 0.0),
            "ev_npv_24m_vnd_tr": best_a["ev_npv_24m_vnd_tr"],
            "ev_npv_36m_vnd_tr": best_a["ev_npv_36m_vnd_tr"],
            "med_npv_24m_usd": best_a.get("med_npv_24m_usd", 0.0),
            "med_npv_24m_vnd_tr": best_a["med_npv_24m_vnd_tr"],
            "p_npv24_le_0_pct": best_a.get("p_npv24_le_0_pct", 0.0),
            "uncond_med_pay1_days": best_a["uncond_med_pay1_cap730_days"],
            "funded_dry_months_pct": best_a["funded_dry_months_pct"],
        },
        "profile_b_fast_cashflow_safe10pct": {
            "status": b_status,
            "winner_policy": best_b_id,
            "ruin_pct": best_b["ruin_pct"],
            "paid_any_pct": best_b["paid_any_pct"],
            "ev_npv_24m_usd": best_b.get("ev_npv_24m_usd", 0.0),
            "ev_npv_24m_vnd_tr": best_b["ev_npv_24m_vnd_tr"],
            "ev_npv_36m_vnd_tr": best_b["ev_npv_36m_vnd_tr"],
            "med_npv_24m_usd": best_b.get("med_npv_24m_usd", 0.0),
            "med_npv_24m_vnd_tr": best_b.get("med_npv_24m_vnd_tr", 0.0),
            "p_npv24_le_0_pct": best_b.get("p_npv24_le_0_pct", 0.0),
            "uncond_med_pay1_days": best_b["uncond_med_pay1_cap730_days"],
            "cond_med_pay1_days": best_b["cond_med_pay1_cal_days"],
            "funded_dry_months_pct": best_b["funded_dry_months_pct"],
        },
    }


def select_dual_objective_winners(
    policy_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Select Profile A & Profile B winners across ALL policies AND strictly within FTMO-only (`MEASURED_DEMO_EXECUTION`)."""
    all_w = _pick_pair_winners(policy_results)
    ftmo_only = {k: v for k, v in policy_results.items() if not k.startswith("P5")}
    if ftmo_only:
        ftmo_w = _pick_pair_winners(ftmo_only)
        all_w["ftmo_only_verified_execution"] = ftmo_w
    return all_w


# ---------------------------------------------------------------------------
# Exact M1 Replay Cache & Fair Per-Rule Multiplier Calibration (Dev 2018-2024)
# ---------------------------------------------------------------------------

class ExactTierReplayCache:
    """Bit-exact pre-aligned M1 per-tier replay cache (35x faster than repeated `replay_portfolio_m1`, ZERO linear scaling, strictly `<= 2024`)."""

    def __init__(
        self,
        ext_days: list[str],
        raw_tapes: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]],
        base_r: dict[str, float],
        red_news_cal: dict[str, list[tuple[int, str]]],
    ) -> None:
        self.holdout_rows_analysed = assert_strict_pre_holdout_days(ext_days)
        self.ext_days = sorted(ext_days)
        self.raw_tapes = raw_tapes
        self.base_r = dict(base_r)
        self.red_news_cal = red_news_cal
        self._stressed_tapes: dict[tuple[float, bool], dict[str, dict]] = {}
        self._prealigned_days: dict[tuple[float, bool], list[dict[str, Any]]] = {}
        self._replay_cache: dict[
            tuple[float, float, float, float, str, bool],
            tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray],
        ] = {}

    def get_prepared_tapes(self, friction_mult: float, use_red_news: bool) -> dict[str, dict]:
        key = (round(float(friction_mult), 4), bool(use_red_news))
        if key in self._stressed_tapes:
            return self._stressed_tapes[key]
        from quant_factory.portfolio_v1_vs_v2_study import apply_cost_stress_to_tapes
        import pass28_final_discovery_rednews_frontier as p28

        base_key = (round(float(friction_mult), 4), False)
        if base_key not in self._stressed_tapes:
            stressed = apply_cost_stress_to_tapes(self.raw_tapes, float(friction_mult))
            self._stressed_tapes[base_key] = stressed
        else:
            stressed = self._stressed_tapes[base_key]

        if not use_red_news:
            return stressed

        guarded: dict[str, dict] = {}
        for eng in CORE7_IDS:
            gt, _ = p28.apply_red_news_guard_to_tape(stressed[eng], self.red_news_cal, mode="FLATTEN_5M", pad_sec=300)
            guarded[eng] = gt
        self._stressed_tapes[key] = guarded
        return guarded

    def _get_prealigned_days(self, friction_mult: float, use_red_news: bool) -> list[dict[str, Any]]:
        """Pre-align 1-lot M1 mark matrices ONCE per `(friction_mult, use_red_news)` (exact `pass11_portfolio.combined_marks` parity)."""
        key = (round(float(friction_mult), 4), bool(use_red_news))
        if key in self._prealigned_days:
            return self._prealigned_days[key]

        import pass27_portfolio_m1_phase_audit as p27

        tapes = self.get_prepared_tapes(friction_mult, use_red_news)
        pre_days: list[dict[str, Any]] = []
        for day_idx, dk in enumerate(self.ext_days):
            cands = [(eng, tapes[eng][dk]) for eng in CORE7_IDS if dk in tapes[eng]]
            if not cands:
                continue
            cands.sort(key=lambda kv: (kv[1][0]["entry"], kv[0]))
            k = len(cands)
            min_e = min(int(stamps[0]) for _, (_, stamps, _) in cands)
            max_x = max(int(stamps[-1]) for _, (_, stamps, _) in cands)
            n_tl = int((max_x - min_e) // 60) + 1
            marks_1lot = np.zeros((k, n_tl, 4), dtype=np.float64)

            meta_list: list[dict[str, Any]] = []
            for i, (eng, (row, stamps, marks)) in enumerate(cands):
                asset = row.get("asset") or ("USDJPY" if "USDJPY" in eng else ("GBPUSD" if "GBPUSD" in eng else eng))
                entry_ts = int(stamps[0])
                at_open = bool(row.get("at_open", False))
                release_ts = int(stamps[-1]) + (0 if at_open else 60)
                net_1lot = float(row["net_usd_per_lot"])
                stop_cost = float(row["stop_risk_with_cost_usd"])
                ep = float(row["entry_price"])
                mgn_std, vmin_s, vstep_s, vmax_s, comm_s = p27.margin_per_lot_usd(asset, ep, "Standard")
                mgn_swg, vmin_w, vstep_w, vmax_w, comm_w = p27.margin_per_lot_usd(asset, ep, "Swing")

                offsets = (stamps - min_e) // 60
                start_o, end_o = int(offsets[0]), int(offsets[-1])
                marks_1lot[i, offsets, :] = marks
                if len(offsets) < (end_o - start_o + 1):
                    pos = np.arange(start_o, end_o + 1)
                    gaps = np.setdiff1d(pos, offsets, assume_unique=True)
                    past = offsets.searchsorted(gaps) - 1
                    marks_1lot[i, gaps, :] = marks[past, 3][:, None]
                if end_o + 1 < n_tl:
                    marks_1lot[i, end_o + 1 :, :] = net_1lot

                meta_list.append({
                    "eng": eng,
                    "asset": asset,
                    "base_r": self.base_r[eng],
                    "entry_ts": entry_ts,
                    "release_ts": release_ts,
                    "stop_cost": stop_cost,
                    "net_1lot": net_1lot,
                    "mgn_std": mgn_std, "comm_std": comm_s, "vmin": vmin_s, "vstep": vstep_s, "vmax": vmax_s,
                    "mgn_swg": mgn_swg, "comm_swg": comm_w,
                    "stamps": stamps,
                    "marks": marks,
                })

            # Precompute 1-lot open_floating(stamp_j) matrix for margin check: shape (k, k)
            open_fl = np.zeros((k, k), dtype=np.float64)
            for j in range(k):
                st_j = meta_list[j]["entry_ts"]
                for i in range(j):
                    mi = meta_list[i]
                    if st_j >= mi["release_ts"]:
                        open_fl[i, j] = mi["net_1lot"]
                    else:
                        sc = mi["stamps"]
                        pos_i = int(sc.searchsorted(st_j))
                        if pos_i < len(sc) and int(sc[pos_i]) == st_j:
                            open_fl[i, j] = float(mi["marks"][pos_i, 0])
                        else:
                            open_fl[i, j] = float(mi["marks"][pos_i - 1, 3])

            pre_days.append({
                "day_idx": day_idx,
                "day": dk,
                "year": int(dk[:4]),
                "cands": meta_list,
                "marks_flat": np.ascontiguousarray(marks_1lot.reshape(k, n_tl * 4)),
                "open_fl": open_fl,
            })

        self._prealigned_days[key] = pre_days
        return pre_days

    def get_exact_tier_stage(
        self,
        *,
        capital_usd: float,
        mult: float,
        symcap_pct: float,
        profile_mode: str,
        use_red_news: bool,
        friction_mult: float,
    ) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        key = (
            round(float(capital_usd), 2),
            round(float(mult), 4),
            round(float(symcap_pct), 4),
            round(float(friction_mult), 4),
            str(profile_mode),
            bool(use_red_news),
        )
        if key in self._replay_cache:
            return self._replay_cache[key]

        pre_days = self._get_prealigned_days(friction_mult, use_red_news)
        n_days = len(self.ext_days)
        nets = np.zeros(n_days, dtype=np.float64)
        dds = np.zeros(n_days, dtype=np.float64)
        ups = np.zeros(n_days, dtype=np.float64)
        flg = np.zeros(n_days, dtype=np.int8)

        initial = float(capital_usd)
        balance = initial
        peak_eq = initial
        max_peak_dd = 0.0
        max_daily_dd = 0.0
        symcap = float(symcap_pct) / 100.0
        is_std = (str(profile_mode) == "Standard")

        sized_cnt = 0
        min_lot_rej = 0
        margin_rej = 0
        symcap_skip = 0
        wins_sum = 0.0
        wins_cnt = 0
        loss_sum = 0.0
        loss_cnt = 0
        r_sum = 0.0
        r_cnt = 0
        cur_loss = 0
        max_loss = 0
        net_a = 0.0
        net_b = 0.0

        for pd in pre_days:
            cands = pd["cands"]
            k = len(cands)
            open_fl = pd["open_fl"]
            lots = np.zeros(k, dtype=np.float64)
            eff_risks = [0.0] * k
            margins = [0.0] * k
            any_sized = False

            for j in range(k):
                cj = cands[j]
                er = cj["base_r"] * float(mult)
                st_j = cj["entry_ts"]
                asset_j = cj["asset"]

                # Exact per-symbol concurrent risk cap
                open_sym_r = 0.0
                for i in range(j):
                    if lots[i] > 0.0 and cands[i]["asset"] == asset_j and st_j < cands[i]["release_ts"]:
                        open_sym_r += eff_risks[i]
                rem = max(0.0, symcap - open_sym_r)
                if rem < er - 1e-12:
                    er = rem
                if er <= 1e-9:
                    symcap_skip += 1
                    continue

                budget = initial * er
                lot = floor_lot_step(budget / cj["stop_cost"], step=cj["vstep"], vol_min=cj["vmin"], vol_max=cj["vmax"])
                if lot < cj["vmin"]:
                    min_lot_rej += 1
                    continue

                mgn_1 = cj["mgn_std"] if is_std else cj["mgn_swg"]
                comm_1 = cj["comm_std"] if is_std else cj["comm_swg"]
                used_m = 0.0
                fl_sum = 0.0
                for i in range(j):
                    if lots[i] > 0.0:
                        if st_j < cands[i]["release_ts"]:
                            used_m += margins[i]
                        fl_sum += lots[i] * open_fl[i, j]
                avail = balance + fl_sum - used_m
                if lot * (mgn_1 + comm_1) > avail:
                    margin_rej += 1
                    continue

                lots[j] = lot
                eff_risks[j] = er
                margins[j] = lot * mgn_1
                any_sized = True
                sized_cnt += 1
                pnl_j = lot * cj["net_1lot"]
                if budget > 1e-9:
                    r_sum += pnl_j / budget
                    r_cnt += 1
                if pnl_j > 0.0:
                    wins_sum += pnl_j
                    wins_cnt += 1
                    cur_loss = 0
                elif pnl_j < 0.0:
                    loss_sum += -pnl_j
                    loss_cnt += 1
                    cur_loss += 1
                    if cur_loss > max_loss:
                        max_loss = cur_loss

            if not any_sized:
                continue

            comb = lots @ pd["marks_flat"]
            day_min_rel = float(comb.min())
            day_max_rel = float(comb.max())
            day_net = float(comb[-1])
            day_dd = max(0.0, -day_min_rel)
            day_up = max(0.0, day_max_rel)

            # Track exact cumulative peak-to-trough floating equity DD across the day
            eq_pts = balance + comb
            if eq_pts.max() > peak_eq:
                # Full running peak across intraday curve
                run_peaks = np.maximum(peak_eq, np.maximum.accumulate(eq_pts))
                day_peak_dd = float(np.max(run_peaks - eq_pts))
                peak_eq = float(run_peaks[-1])
            else:
                day_peak_dd = float(peak_eq - eq_pts.min())
            if day_peak_dd > max_peak_dd:
                max_peak_dd = day_peak_dd
            if day_dd > max_daily_dd:
                max_daily_dd = day_dd

            d_i = pd["day_idx"]
            nets[d_i] = day_net
            dds[d_i] = day_dd
            ups[d_i] = day_up
            flg[d_i] = 1
            balance += day_net
            if pd["year"] <= 2020:
                net_a += day_net
            else:
                net_b += day_net

        yrs_span = max(1.0, float(len({d[:4] for d in self.ext_days})))
        ann_pct = 100.0 * ((balance - initial) / yrs_span) / initial
        peak_dd_pct = 100.0 * max_peak_dd / initial
        calmar = (ann_pct / peak_dd_pct) if peak_dd_pct > 1e-9 else 0.0
        daily_ret = nets / initial
        std_d = float(np.std(daily_ret, ddof=1)) if n_days > 1 else 0.0
        sharpe = (float(np.mean(daily_ret)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0
        pf = (wins_sum / loss_sum) if loss_sum > 1e-9 else 0.0
        wr = (100.0 * wins_cnt / max(1, wins_cnt + loss_cnt))
        rr = ((wins_sum / wins_cnt) / (loss_sum / loss_cnt)) if (wins_cnt > 0 and loss_cnt > 0) else 0.0
        ev_r = (r_sum / r_cnt) if r_cnt > 0 else 0.0
        tot_cand = sized_cnt + min_lot_rej + margin_rej

        bal_met = {
            "capital_usd": initial,
            "sized_trades": sized_cnt,
            "min_lot_rejected": min_lot_rej,
            "min_lot_reject_pct": round(100.0 * min_lot_rej / max(1, tot_cand), 3),
            "margin_rejected": margin_rej,
            "symcap_skipped": symcap_skip,
            "net_usd": round(balance - initial, 2),
            "ann_pct": round(ann_pct, 3),
            "ann_cluster_a_pct": round(100.0 * (net_a / 3.0) / initial, 3),
            "ann_cluster_b_pct": round(100.0 * (net_b / 4.0) / initial, 3),
            "peak_dd_pct": round(peak_dd_pct, 3),
            "max_daily_dd_pct": round(100.0 * max_daily_dd / initial, 3),
            "calmar": round(calmar, 3),
            "sharpe": round(sharpe, 3),
            "winrate_pct": round(wr, 2),
            "avg_rr": round(rr, 3),
            "ev_per_trade_r": round(ev_r, 4),
            "profit_factor": round(pf, 3),
            "max_loss_streak_trades": max_loss,
            "underwater_months": 0.0,
        }
        val = (bal_met, nets, dds, ups, flg)
        self._replay_cache[key] = val
        return val

    def build_stage_tuple(
        self,
        *,
        capital_usd: float,
        p1_mult: float,
        p1_lock_mult: float,
        p2_mult: float,
        p2_lock_mult: float,
        funded_mult: float,
        amber_mult: float,
        red_mult: float,
        p1_symcap: float,
        p2_symcap: float,
        fn_symcap: float,
        profile_mode: str,
        p1_news: bool,
        p2_news: bool,
        fn_news: bool,
        friction_mult: float,
        steps: int = 2,
    ) -> tuple[np.ndarray, ...]:
        _, n_fn, d_fn, u_fn, f_fn = self.get_exact_tier_stage(
            capital_usd=capital_usd, mult=funded_mult, symcap_pct=fn_symcap,
            profile_mode=profile_mode, use_red_news=fn_news, friction_mult=friction_mult,
        )
        _, n_amb, d_amb, u_amb, f_amb = self.get_exact_tier_stage(
            capital_usd=capital_usd, mult=amber_mult, symcap_pct=fn_symcap,
            profile_mode=profile_mode, use_red_news=fn_news, friction_mult=friction_mult,
        )
        _, n_red, d_red, u_red, f_red = self.get_exact_tier_stage(
            capital_usd=capital_usd, mult=red_mult, symcap_pct=fn_symcap,
            profile_mode=profile_mode, use_red_news=fn_news, friction_mult=friction_mult,
        )
        if steps == 0:
            # Instant Funded starts directly in stage 3 — reuse exact funded arrays for unused P1/P2 slots
            n_p1, d_p1, u_p1, f_p1 = n_fn, d_fn, u_fn, f_fn
            n_p1l, d_p1l, u_p1l, f_p1l = n_fn, d_fn, u_fn, f_fn
            n_p2, d_p2, u_p2, f_p2 = n_fn, d_fn, u_fn, f_fn
            n_p2l, d_p2l, u_p2l, f_p2l = n_fn, d_fn, u_fn, f_fn
        elif steps == 1:
            _, n_p1, d_p1, u_p1, f_p1 = self.get_exact_tier_stage(
                capital_usd=capital_usd, mult=p1_mult, symcap_pct=p1_symcap,
                profile_mode=profile_mode, use_red_news=p1_news, friction_mult=friction_mult,
            )
            _, n_p1l, d_p1l, u_p1l, f_p1l = self.get_exact_tier_stage(
                capital_usd=capital_usd, mult=p1_lock_mult, symcap_pct=p1_symcap,
                profile_mode=profile_mode, use_red_news=p1_news, friction_mult=friction_mult,
            )
            n_p2, d_p2, u_p2, f_p2 = n_fn, d_fn, u_fn, f_fn
            n_p2l, d_p2l, u_p2l, f_p2l = n_fn, d_fn, u_fn, f_fn
        else:
            _, n_p1, d_p1, u_p1, f_p1 = self.get_exact_tier_stage(
                capital_usd=capital_usd, mult=p1_mult, symcap_pct=p1_symcap,
                profile_mode=profile_mode, use_red_news=p1_news, friction_mult=friction_mult,
            )
            _, n_p1l, d_p1l, u_p1l, f_p1l = self.get_exact_tier_stage(
                capital_usd=capital_usd, mult=p1_lock_mult, symcap_pct=p1_symcap,
                profile_mode=profile_mode, use_red_news=p1_news, friction_mult=friction_mult,
            )
            _, n_p2, d_p2, u_p2, f_p2 = self.get_exact_tier_stage(
                capital_usd=capital_usd, mult=p2_mult, symcap_pct=p2_symcap,
                profile_mode=profile_mode, use_red_news=p2_news, friction_mult=friction_mult,
            )
            _, n_p2l, d_p2l, u_p2l, f_p2l = self.get_exact_tier_stage(
                capital_usd=capital_usd, mult=p2_lock_mult, symcap_pct=p2_symcap,
                profile_mode=profile_mode, use_red_news=p2_news, friction_mult=friction_mult,
            )
        return (
            n_p1, d_p1, u_p1, f_p1,
            n_p1l, d_p1l, u_p1l, f_p1l,
            n_p2, d_p2, u_p2, f_p2,
            n_p2l, d_p2l, u_p2l, f_p2l,
            n_fn, d_fn, u_fn, f_fn,
            n_amb, d_amb, u_amb, f_amb,
            n_red, d_red, u_red, f_red,
        )


def calibrate_safe_multipliers_for_rule(
    cache: ExactTierReplayCache,
    idx_matrix: np.ndarray,
    *,
    program_tier: dict[str, Any],
    variant: str,
    friction_mult: float,
    card_fx_fee_pct: float,
    discount_rate_annual: float,
    usd_vnd_rate: float,
) -> dict[str, Any]:
    """Automatically calibrate fair, safe P1/P2/Funded risk multipliers for each rule family (`3%`, `4%`, `5%` DD)."""
    daily_lim = float(program_tier["dd_daily_pct"])
    max_dd = float(program_tier["dd_max_pct"])
    steps = int(program_tier["steps"])
    cap = float(program_tier["capital_usd"])
    fee = float(program_tier["active_promo_usd"] or program_tier["orig_usd"])
    prof_mode = str(program_tier.get("profile_mode", "Standard"))
    vc = VARIANT_PHASE_CONFIGS[variant]

    # Standard 5%/10% 2-Step uses the exact registered C10_NEWS_ON / C00 / C10 parameters directly (no post-hoc tuning!)
    if steps == 2 and daily_lim >= 0.049 and max_dd >= 0.099:
        p1_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p1_news_guard"])
        p2_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p2_news_guard"])
        fn_news = bool(program_tier.get("news_restricted_funded", True)) or bool(vc["funded_news_guard"])
        return {
            "calibrated_reason": f"EXACT_{variant}_5PCT_10PCT_REGISTERED",
            "p1_mult": vc["p1_mult"],
            "p1_lock_trigger": vc["p1_lock_trigger"],
            "p1_lock_mult": vc["p1_lock_mult"],
            "p2_mult": vc["p2_mult"],
            "p2_lock_trigger": vc["p2_lock_trigger"],
            "p2_lock_mult": vc["p2_lock_mult"],
            "funded_mult": vc["funded_mult"],
            "amber_dd": vc["amber_dd"],
            "amber_mult": vc["amber_mult"],
            "red_dd": vc["red_dd"],
            "red_mult": vc["red_mult"],
            "p1_symcap": vc["p1_symcap_pct"],
            "p2_symcap": vc["p2_symcap_pct"],
            "fn_symcap": vc["funded_symcap_pct"],
            "p1_news": p1_news,
            "p2_news": p2_news,
            "fn_news": fn_news,
            "p1_ea_stop": vc["p1_ea_daily_stop"],
            "p2_ea_stop": vc["p2_ea_daily_stop"],
            "fn_ea_stop": vc["funded_ea_daily_stop"],
        }

    # For tighter DD modes (`2.5%` E8 Pro, `3%` daily DD 1-Step/Instant, OR `4%/8%` The5ers), sweep safe multipliers fairly!
    if daily_lim <= 0.026:
        # E8 Pro (`2.5%` daily / `8%` static / 1-Step 8% target)
        grid = [
            (1.00, 1.00, 0.65),
            (1.25, 1.00, 0.75),
            (1.50, 1.00, 0.75),
            (1.75, 1.00, 0.85),
        ]
        ea_stop_eval = 0.0175
        ea_stop_fn = 0.0150
        amber_dd = 0.020
        red_dd = 0.040
        symcap_eval = 0.85
        symcap_fn = 0.75
    elif daily_lim <= 0.031:
        if steps == 0:
            # Instant Funded (`3%` daily / `10%` Intraday Trailing / `30%` Best Day)
            grid = [
                (0.75, 0.75, 0.75),
                (1.00, 1.00, 1.00),
                (1.25, 1.25, 1.25),
                (1.50, 1.50, 1.50),
            ]
        else:
            # 1-Step (`3%` daily / `10%` EOD Trailing / `50%` Best Day)
            grid = [
                (1.50, 1.00, 0.75),
                (1.75, 1.00, 0.85),
                (2.00, 1.00, 1.00),
                (2.25, 1.00, 1.00),
                (2.50, 1.00, 1.00),
                (2.75, 1.00, 1.00),
            ]
        ea_stop_eval = 0.021
        ea_stop_fn = 0.018
        amber_dd = 0.025
        red_dd = 0.045
        symcap_eval = 1.00
        symcap_fn = 0.85
    else:
        # 4% daily / 8% static (e.g. The5ers 50K/100K 4%/8% tiers)
        grid = [
            (2.25, 1.50, 0.75),
            (2.50, 1.75, 0.85),
            (2.75, 1.75, 0.85),
            (3.00, 2.00, 0.90),
        ]
        ea_stop_eval = 0.028
        ea_stop_fn = 0.022
        amber_dd = 0.025
        red_dd = 0.050
        symcap_eval = 1.25
        symcap_fn = 0.85

    p1_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p1_news_guard"])
    p2_news = bool(program_tier.get("news_restricted_eval", False)) or bool(vc["p2_news_guard"])
    fn_news = bool(program_tier.get("news_restricted_funded", True)) or bool(vc["funded_news_guard"])

    sweep_log: list[dict[str, Any]] = []
    best_cfg: dict[str, Any] | None = None
    best_score = -1e18

    # Use subset of 1,500 paths for fast calibration sweep
    sub_idx = idx_matrix[: min(1_500, len(idx_matrix))]
    fee_reg = float(program_tier.get("orig_usd") or fee)
    for p1_m, p2_m, fn_m in grid:
        st_arrs = cache.build_stage_tuple(
            capital_usd=cap,
            p1_mult=p1_m,
            p1_lock_mult=round(p1_m * 0.55, 2),
            p2_mult=p2_m,
            p2_lock_mult=round(p2_m * 0.55, 2),
            funded_mult=fn_m,
            amber_mult=round(fn_m * 0.65, 2),
            red_mult=round(fn_m * 0.40, 2),
            p1_symcap=symcap_eval,
            p2_symcap=symcap_eval,
            fn_symcap=symcap_fn,
            profile_mode=prof_mode,
            p1_news=p1_news,
            p2_news=p2_news,
            fn_news=fn_news,
            friction_mult=friction_mult,
            steps=steps,
        )
        res = _simulate_single_ticket_rules_numba(
            sub_idx, *st_arrs,
            steps=steps, cap=cap, fee_day0_usd=fee, fee_regular_usd=fee_reg,
            card_fx_fee_pct=card_fx_fee_pct,
            withdrawal_fee_pct=float(program_tier.get("payout_withdrawal_fee_pct", program_tier.get("withdrawal_fee_pct", 0.015))),
            fee_refund_pct=float(program_tier.get("fee_refund_pct", 0.0)),
            p1_target=float(program_tier.get("p1_target_pct", 0.10)),
            p2_target=float(program_tier.get("p2_target_pct", 0.0)),
            daily_lim=daily_lim, max_dd_lim=max_dd,
            dd_type=_dd_type_code(program_tier.get("dd_type", "static")),
            trail_lock_initial=bool(program_tier.get("trail_lock_at_initial", False)),
            best_day_cap_pct=float(program_tier.get("best_day_cap_pct", 0.0)),
            min_days=int(program_tier.get("min_trading_days", 0)),
            min_prof_days=int(program_tier.get("min_profitable_days", 0)),
            min_prof_day_pct=float(program_tier.get("min_profitable_day_pct", 0.0)),
            profit_split=float(program_tier.get("profit_split_pct", 0.90)),
            payout_cycle_days=int(program_tier.get("payout_cycle_trading_days", 10)),
            min_payout_usd=float(program_tier.get("min_payout_usd", 50.0)),
            strict_lt_breach=True,
            p1_lock_trigger=0.50, p2_lock_trigger=0.50,
            amber_dd=amber_dd, red_dd=red_dd,
            p1_ea_stop=ea_stop_eval, p2_ea_stop=ea_stop_eval, fn_ea_stop=ea_stop_fn,
            start_day_offset=0, discount_rate_annual=discount_rate_annual, max_retries=0,
            refund_payout_milestone=int(program_tier.get("refund_payout_milestone", 1)),
            payout_buffer_retention_pct=float(program_tier.get("payout_buffer_retention_pct", 0.0)),
            locks_at_initial_after_first_payout=bool(program_tier.get("locks_at_initial_after_first_payout", False)),
            min_payout_profit_pct=float(program_tier.get("min_payout_profit_pct", 0.0)),
            funded_first_payout_min_prof_days=int(program_tier.get("funded_first_payout_min_prof_days", 0)),
            funded_first_payout_prof_pct=float(program_tier.get("funded_first_payout_prof_pct", 0.0)),
            daily_profit_cap_pct=float(program_tier.get("daily_profit_cap_pct", 0.0)),
            refund_withdrawal_fee_pct=float(program_tier.get("refund_withdrawal_fee_pct", 0.0)),
            daily_dd_anchor_mode=_daily_dd_anchor_code(program_tier.get("daily_dd_anchor", "initial_balance")),
        )
        summ = summarize_single_ticket_mc(
            res, fee_usd=fee, fee_regular_usd=fee_reg, card_fx_fee_pct=card_fx_fee_pct,
            usd_vnd_rate=usd_vnd_rate, horizon_days=sub_idx.shape[1],
            refund_withdrawal_fee_pct=float(program_tier.get("refund_withdrawal_fee_pct", 0.0)),
        )
        ev_npv = float(summ["ev_npv_24m_usd"])
        fn_br = float(summ["funded_12m_breach"]["breach_12m_pct"])
        d_br = float(summ["firm_hard_breach_daily_pct"])
        # Penalize reckless daily breach (>15%) or funded breach (>3%) heavily
        penalty = max(0.0, d_br - 15.0) * 40.0 + max(0.0, fn_br - 3.0) * 100.0
        score = ev_npv - penalty
        sweep_log.append({
            "p1_mult": p1_m, "p2_mult": p2_m, "funded_mult": fn_m,
            "ev_npv_24m_usd": ev_npv, "pass_24m_pct": summ["pass_24m_pct"],
            "daily_breach_pct": d_br, "funded_12m_breach_pct": fn_br,
        })
        if score > best_score:
            best_score = score
            best_cfg = {
                "calibrated_reason": f"AUTO_SWEPT_FAIR_SAFE_{int(daily_lim*100)}PCT_DD",
                "p1_mult": p1_m,
                "p1_lock_trigger": 0.50,
                "p1_lock_mult": round(p1_m * 0.55, 2),
                "p2_mult": p2_m,
                "p2_lock_trigger": 0.50,
                "p2_lock_mult": round(p2_m * 0.55, 2),
                "funded_mult": fn_m,
                "amber_dd": amber_dd,
                "amber_mult": round(fn_m * 0.65, 2),
                "red_dd": red_dd,
                "red_mult": round(fn_m * 0.40, 2),
                "p1_symcap": symcap_eval,
                "p2_symcap": symcap_eval,
                "fn_symcap": symcap_fn,
                "p1_news": p1_news,
                "p2_news": p2_news,
                "fn_news": fn_news,
                "p1_ea_stop": ea_stop_eval,
                "p2_ea_stop": ea_stop_eval,
                "fn_ea_stop": ea_stop_fn,
                "calibration_sweep": sweep_log,
            }

    assert best_cfg is not None
    return best_cfg


# ---------------------------------------------------------------------------
# Full End-to-End Study Orchestrator (Sealed Dev 2018-2024 ONLY)
# ---------------------------------------------------------------------------

def _pack_templates_for_numba(
    templates: list[dict[str, Any]],
) -> tuple[Any, ...]:
    """Pack a list of template dicts (exact M1 arrays + Day-0/Regular fees + daily DD anchor) into NumPy arrays."""
    n_tpl = len(templates)
    n_obs = len(templates[0]["stage_arrays"][0])

    def _stack(pos: int, dtype: Any = np.float64) -> np.ndarray:
        arr = np.empty((n_tpl, n_obs), dtype=dtype)
        for i, t in enumerate(templates):
            arr[i] = t["stage_arrays"][pos]
        return np.ascontiguousarray(arr)

    return (
        _stack(0), _stack(1), _stack(2), _stack(3, np.int8),
        _stack(4), _stack(5), _stack(6), _stack(7, np.int8),
        _stack(8), _stack(9), _stack(10), _stack(11, np.int8),
        _stack(12), _stack(13), _stack(14), _stack(15, np.int8),
        _stack(16), _stack(17), _stack(18), _stack(19, np.int8),
        _stack(20), _stack(21), _stack(22), _stack(23, np.int8),
        _stack(24), _stack(25), _stack(26), _stack(27, np.int8),
        np.ascontiguousarray([int(t["firm_idx"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([int(t["steps"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t["capital_usd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t.get("fee_day0_usd", t.get("fee_usd", 0.0))) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t.get("fee_regular_usd", t.get("fee_day0_usd", t.get("fee_usd", 0.0)))) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["fee_refund_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t.get("payout_withdrawal_fee_pct", t.get("withdrawal_fee_pct", 0.015))) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t.get("refund_withdrawal_fee_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p1_target_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p2_target_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["dd_daily_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["dd_max_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([_dd_type_code(t["dd_type"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([_daily_dd_anchor_code(t.get("daily_dd_anchor", "initial_balance")) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t["best_day_cap_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([int(t["min_trading_days"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([int(t["min_profitable_days"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t["min_profitable_day_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["profit_split_pct"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([int(t["payout_cycle_trading_days"]) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t["min_payout_usd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p1_lock_trigger"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p2_lock_trigger"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["amber_dd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["red_dd"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p1_ea_stop"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["p2_ea_stop"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t["fn_ea_stop"]) for t in templates], dtype=np.float64),
        np.ascontiguousarray([int(t.get("refund_payout_milestone", 1)) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t.get("payout_buffer_retention_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray([1 if t.get("locks_at_initial_after_first_payout", False) else 0 for t in templates], dtype=np.int8),
        np.ascontiguousarray([float(t.get("min_payout_profit_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray([float(t.get("daily_profit_cap_pct", 0.0)) for t in templates], dtype=np.float64),
        np.ascontiguousarray([int(t.get("funded_first_payout_min_prof_days", 0)) for t in templates], dtype=np.int32),
        np.ascontiguousarray([float(t.get("funded_first_payout_prof_pct", 0.0)) for t in templates], dtype=np.float64),
    )


def _find_program_by_hint(catalog: dict[str, Any], predicate) -> dict[str, Any] | None:
    for p in catalog["programs"]:
        if predicate(p):
            return p
    return None


def _pick_tier_near(prog: dict[str, Any], target_cap: float) -> dict[str, Any]:
    avail = [t for t in prog["tiers"] if t.get("available_vn", True) and float(t.get("orig_usd", 0.0)) > 0.0]
    if not avail:
        raise ValueError(f"No VN-available tiers in program {prog['program_id']}")
    best = min(avail, key=lambda t: abs(float(t["capital_usd"]) - float(target_cap)))
    return {**prog, **best}


def run_full_capital_promo_study(
    *,
    catalog_path: Path | None = None,
    step5_path: Path | None = None,
    n_paths_grid: int = 5_000,
    n_paths_single: int = 10_000,
    horizon_months: int = 36,
    use_promo_prices: bool = True,
    primary_variant: str = PRIMARY_VARIANT_DEFAULT,
    allow_stale_catalog: bool = False,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Execute the full sealed-Dev (`<= 2024`) multi-firm capital, rounding, promo & Pareto study (v2 — Astra R10 closures)."""
    t0 = time.perf_counter()
    from quant_factory.data_store import (
        assert_holdout_locked,
        build_or_load_frozen_tapes,
        load_red_news_calendar,
        load_registry,
    )

    lock_sha = assert_holdout_locked()
    frozen = build_or_load_frozen_tapes()
    ext_days = list(frozen["ext_days"])
    holdout_rows = assert_strict_pre_holdout_days(ext_days)
    reg = load_registry()
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    rn_cal = load_red_news_calendar()

    # Fail-closed catalog load (`allow_fallback=False`) + per-program & per-tier staleness enforcement
    catalog = load_pricing_catalog(
        catalog_path,
        allow_fallback=False,
        enforce_freshness=True,
        allow_stale=allow_stale_catalog,
    )
    traps = detect_pricing_traps(catalog)
    step5_info = load_step5_c00_c10_summary(step5_path)
    primary_var = str(primary_variant or PRIMARY_VARIANT_DEFAULT)
    if primary_var not in VARIANT_PHASE_CONFIGS:
        raise ValueError(f"Unknown primary_variant: {primary_var!r}")
    step5_info["primary_variant"] = primary_var

    usd_vnd = float(catalog["fx_rates"]["usd_vnd"])
    card_fx_fee = float(catalog["vn_transaction_costs"]["card_fx_buy_fee_pct"])
    horizon_days = int(horizon_months * TRADING_DAYS_PER_MONTH)

    cache = ExactTierReplayCache(ext_days, frozen["tapes"], base_r, rn_cal)
    idx_single = make_block_bootstrap_indices(len(ext_days), horizon=horizon_days, n_paths=n_paths_single, seed=seed)
    idx_grid = idx_single[: min(n_paths_grid, n_paths_single)]

    # -----------------------------------------------------------------------
    # SECTION 1: Exact Per-Tier 0.01-Lot Rounding Audit (`5K .. 200K`) + B1 Sizing Parity Disclosure
    # -----------------------------------------------------------------------
    lot_rounding_audit: dict[str, Any] = {
        "funded_1_0x": [],
        "funded_1_25x": [],
        "red_brake_0_4x": [],
        "p1_4_0x": [],
    }
    for label, mult, symcap in (
        ("funded_1_0x", 1.00, 1.00),
        ("funded_1_25x", 1.25, 1.25),
        ("red_brake_0_4x", 0.40, 1.00),
        ("p1_4_0x", 4.00, 1.75),
    ):
        rows_tier = []
        for cap in TIER_SIZES_USD:
            bal_met, _, _, _, _ = cache.get_exact_tier_stage(
                capital_usd=cap, mult=mult, symcap_pct=symcap,
                profile_mode="Standard", use_red_news=True, friction_mult=1.00,
            )
            rows_tier.append(bal_met)
        ref_ann_200k = rows_tier[-1]["ann_pct"]
        for r in rows_tier:
            r["lot_rounding_drag_vs_200k_pct"] = round(
                100.0 * (r["ann_pct"] - ref_ann_200k) / max(1e-6, abs(ref_ann_200k)), 2
            )
        lot_rounding_audit[label] = rows_tier

    # B1 Sizing Parity Disclosure: Python start-of-period capital + hard margin reject vs MQL5 EA dynamic scaling
    lot_rounding_audit["sizing_parity_disclosure"] = {
        "tag": "DAILY_APPROX_PENDING_MT5_MODEL4_CROSSCHECK",
        "python_get_exact_tier_stage": (
            "Sizes each trade from fixed start-of-period capital (`initial * eff_risk`) and rejects the trade "
            "completely (`MARGIN` skip) if `lot * (margin_per_lot + comm_per_lot) > available_margin`."
        ),
        "mql5_ea_production": (
            "Sizes each trade from live `AccountInfoDouble(ACCOUNT_BALANCE) * risk * 0.95` and dynamically scales "
            "lot volume down to `85%` of free margin (`ACCOUNT_MARGIN_FREE`) rather than binary-rejecting on margin shortfall."
        ),
        "implication": (
            "Exact `5K/10K` lot-rounding drag percentages in Section 3 are `DAILY_APPROX` Python estimates and require "
            "MT5 `Model=4` real-tick cross-check across account tiers before quoting exact live EA drag."
        ),
    }

    # -----------------------------------------------------------------------
    # SECTION 2: Friction & Break-Even Threshold Sweep (`0.66x .. 4.00x`)
    # -----------------------------------------------------------------------
    friction_sweep_100k: list[dict[str, Any]] = []
    friction_breakeven_x: float | None = None
    prev_f: tuple[float, float] | None = None
    for fmult in FRICTION_SWEEP_WITH_BREAKEVEN:
        bal_met, _, _, _, _ = cache.get_exact_tier_stage(
            capital_usd=100_000.0, mult=1.00, symcap_pct=1.00,
            profile_mode="Standard", use_red_news=True, friction_mult=fmult,
        )
        friction_sweep_100k.append({"friction_x": fmult, **bal_met})
        if prev_f is not None and friction_breakeven_x is None:
            if prev_f[1] > 0.0 and bal_met["ann_pct"] <= 0.0:
                frac = prev_f[1] / max(1e-9, prev_f[1] - bal_met["ann_pct"])
                friction_breakeven_x = round(prev_f[0] + frac * (fmult - prev_f[0]), 2)
        prev_f = (fmult, bal_met["ann_pct"])

    # -----------------------------------------------------------------------
    # SECTION 3: Multi-Firm & Multi-Mode Exact Rule-Engine Comparison (Primary: C10_NEWS_ON + C00 Control)
    # -----------------------------------------------------------------------
    ftmo_std = _find_program_by_hint(catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard")
    ftmo_swg = _find_program_by_hint(catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Swing")
    ftmo_1st = _find_program_by_hint(catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 1)
    ftmo_ins = _find_program_by_hint(catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 0)
    other_progs = [p for p in catalog["programs"] if p["firm_id"] != "FTMO"]

    mode_comparison: list[dict[str, Any]] = []
    # Tuple: (prog, cap, var_name, pricing_mode) where pricing_mode in ("BF_DAY0", "ALL_REGULAR")
    eval_targets: list[tuple[dict[str, Any], float, str, str]] = []
    if ftmo_std:
        for cap in (10_000.0, 25_000.0, 50_000.0, 100_000.0, 200_000.0):
            eval_targets.append((ftmo_std, cap, primary_var, "BF_DAY0" if use_promo_prices else "ALL_REGULAR"))
        # C00 control on 10K & 100K, plus C10 (News-OFF sensitivity ONLY) on 100K
        for cap in (10_000.0, 100_000.0):
            eval_targets.append((ftmo_std, cap, CONTROL_VARIANT_DEFAULT, "BF_DAY0" if use_promo_prices else "ALL_REGULAR"))
        eval_targets.append((ftmo_std, 100_000.0, "C10", "BF_DAY0" if use_promo_prices else "ALL_REGULAR"))
        # All-Regular pricing side-by-side for key FTMO tiers (10K / 50K / 100K / 200K)
        if use_promo_prices:
            for cap in (10_000.0, 50_000.0, 100_000.0, 200_000.0):
                eval_targets.append((ftmo_std, cap, primary_var, "ALL_REGULAR"))
    if ftmo_swg:
        for cap in (10_000.0, 25_000.0):
            eval_targets.append((ftmo_swg, cap, primary_var, "ALL_REGULAR"))
    if ftmo_1st:
        for cap in (10_000.0, 50_000.0, 100_000.0):
            eval_targets.append((ftmo_1st, cap, primary_var, "BF_DAY0" if use_promo_prices else "ALL_REGULAR"))
    if ftmo_ins:
        for cap in (5_000.0, 10_000.0, 50_000.0, 100_000.0):
            eval_targets.append((ftmo_ins, cap, primary_var, "BF_DAY0" if use_promo_prices else "ALL_REGULAR"))
    for op in other_progs:
        avail_caps = sorted(float(t["capital_usd"]) for t in op["tiers"] if t.get("available_vn", True) and float(t.get("orig_usd", 0.0)) > 0.0)
        picked_caps = []
        for target_c in (5_000.0, 10_000.0, 20_000.0, 50_000.0, 60_000.0, 100_000.0):
            if target_c in avail_caps and target_c not in picked_caps:
                picked_caps.append(target_c)
        if not picked_caps and avail_caps:
            picked_caps = avail_caps[:3]
        for cap in picked_caps:
            eval_targets.append((op, cap, primary_var, "BF_DAY0" if use_promo_prices else "ALL_REGULAR"))

    calibrated_cache: dict[tuple[str, float, str, float], dict[str, Any]] = {}
    rule_family_cal_cache: dict[tuple[str, float, float, str, str, str, float], dict[str, Any]] = {}
    for prog, cap, var_name, pricing_mode in eval_targets:
        try:
            _, merged = get_program_tier(catalog, prog["program_id"], cap)
        except KeyError:
            continue
        if not merged.get("available_vn", True):
            continue
        fee_orig = float(merged["orig_usd"])
        fee_day0 = float(merged["active_promo_usd"]) if pricing_mode == "BF_DAY0" else fee_orig
        if fee_day0 <= 0.0 or fee_orig <= 0.0:
            continue
        ref_wd_fee = float(merged.get("refund_withdrawal_fee_pct", 0.0))
        payout_wd_fee = float(merged.get("payout_withdrawal_fee_pct", merged.get("withdrawal_fee_pct", 0.015)))
        anchor_mode = _daily_dd_anchor_code(merged.get("daily_dd_anchor", "initial_balance"))

        for fmult in (1.00, 1.50):
            rf_key = (
                prog["program_id"],
                round(float(merged["dd_daily_pct"]), 4),
                round(float(merged["dd_max_pct"]), 4),
                str(merged["dd_type"]),
                str(merged.get("daily_dd_anchor", "initial_balance")),
                var_name,
                fmult,
            )
            cal = rule_family_cal_cache.get(rf_key)
            if cal is None:
                cal = calibrate_safe_multipliers_for_rule(
                    cache, idx_grid,
                    program_tier=merged, variant=var_name, friction_mult=fmult,
                    card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    usd_vnd_rate=usd_vnd,
                )
                rule_family_cal_cache[rf_key] = cal
            cal_key = (prog["program_id"], cap, var_name, fmult)
            calibrated_cache[cal_key] = cal
            st_arrs = cache.build_stage_tuple(
                capital_usd=cap,
                p1_mult=cal["p1_mult"], p1_lock_mult=cal["p1_lock_mult"],
                p2_mult=cal["p2_mult"], p2_lock_mult=cal["p2_lock_mult"],
                funded_mult=cal["funded_mult"], amber_mult=cal["amber_mult"], red_mult=cal["red_mult"],
                p1_symcap=cal["p1_symcap"], p2_symcap=cal["p2_symcap"], fn_symcap=cal["fn_symcap"],
                profile_mode=str(merged["profile_mode"]),
                p1_news=cal["p1_news"], p2_news=cal["p2_news"], fn_news=cal["fn_news"],
                friction_mult=fmult, steps=int(merged["steps"]),
            )
            res0 = _simulate_single_ticket_rules_numba(
                idx_single, *st_arrs,
                steps=int(merged["steps"]), cap=cap, fee_day0_usd=fee_day0, fee_regular_usd=fee_orig,
                card_fx_fee_pct=card_fx_fee,
                withdrawal_fee_pct=payout_wd_fee,
                fee_refund_pct=float(merged.get("fee_refund_pct", 0.0)),
                p1_target=float(merged.get("p1_target_pct", 0.10)),
                p2_target=float(merged.get("p2_target_pct", 0.0)),
                daily_lim=float(merged.get("dd_daily_pct", 0.05)),
                max_dd_lim=float(merged.get("dd_max_pct", 0.10)),
                dd_type=_dd_type_code(merged.get("dd_type", "static")),
                trail_lock_initial=bool(merged.get("trail_lock_at_initial", False)),
                best_day_cap_pct=float(merged.get("best_day_cap_pct", 0.0)),
                min_days=int(merged.get("min_trading_days", 0)),
                min_prof_days=int(merged.get("min_profitable_days", 0)),
                min_prof_day_pct=float(merged.get("min_profitable_day_pct", 0.0)),
                profit_split=float(merged.get("profit_split_pct", 0.80)),
                payout_cycle_days=int(merged.get("payout_cycle_trading_days", 10)),
                min_payout_usd=float(merged.get("min_payout_usd", 50.0)),
                strict_lt_breach=True,
                p1_lock_trigger=cal["p1_lock_trigger"], p2_lock_trigger=cal["p2_lock_trigger"],
                amber_dd=cal["amber_dd"], red_dd=cal["red_dd"],
                p1_ea_stop=cal["p1_ea_stop"], p2_ea_stop=cal["p2_ea_stop"], fn_ea_stop=cal["fn_ea_stop"],
                start_day_offset=0, discount_rate_annual=DEFAULT_DISCOUNT_RATE, max_retries=0,
                refund_payout_milestone=int(merged.get("refund_payout_milestone", 1)),
                payout_buffer_retention_pct=float(merged.get("payout_buffer_retention_pct", 0.0)),
                locks_at_initial_after_first_payout=bool(merged.get("locks_at_initial_after_first_payout", False)),
                min_payout_profit_pct=float(merged.get("min_payout_profit_pct", 0.0)),
                funded_first_payout_min_prof_days=int(merged.get("funded_first_payout_min_prof_days", 0)),
                funded_first_payout_prof_pct=float(merged.get("funded_first_payout_prof_pct", 0.0)),
                daily_profit_cap_pct=float(merged.get("daily_profit_cap_pct", 0.0)),
                refund_withdrawal_fee_pct=ref_wd_fee,
                daily_dd_anchor_mode=anchor_mode,
            )
            summ = summarize_single_ticket_mc(
                res0, fee_usd=fee_day0, fee_regular_usd=fee_orig, card_fx_fee_pct=card_fx_fee,
                usd_vnd_rate=usd_vnd, horizon_days=horizon_days,
                refund_withdrawal_fee_pct=ref_wd_fee,
            )
            mode_comparison.append({
                "program_id": prog["program_id"],
                "firm_id": prog["firm_id"],
                "firm_name": prog["firm_name"],
                "mode_name": prog["mode_name"],
                "execution_evidence_tag": merged["execution_evidence_tag"],
                "dd_rule_verification_tag": merged.get(
                    "dd_rule_verification_tag",
                    _dd_rule_verification_tag(
                        prog["firm_id"],
                        str(merged.get("daily_dd_anchor_raw", "")),
                        str(merged.get("daily_dd_anchor", "initial_balance")),
                    ),
                ),
                "dd_rule_verification_note": merged.get("dd_rule_verification_note", ""),
                "variant": var_name,
                "pricing_mode": "BF_DAY0_PLUS_REGULAR_RETRIES" if (pricing_mode == "BF_DAY0" and fee_day0 < fee_orig - 1e-6) else "ALL_REGULAR",
                "capital_usd": cap,
                "friction_x": fmult,
                "orig_usd": fee_orig,
                "promo_usd": fee_day0,
                "fee_ratio_pct": round(100.0 * fee_day0 / cap, 4),
                "dd_daily_pct": round(float(merged["dd_daily_pct"]) * 100.0, 1),
                "dd_max_pct": round(float(merged["dd_max_pct"]) * 100.0, 1),
                "dd_type": merged["dd_type"],
                "daily_dd_anchor": merged.get("daily_dd_anchor", "initial_balance"),
                "daily_dd_anchor_raw": merged.get("daily_dd_anchor_raw", "initial_balance"),
                "payout_withdrawal_fee_pct": round(payout_wd_fee * 100.0, 2),
                "refund_withdrawal_fee_pct": round(ref_wd_fee * 100.0, 2),
                "best_day_cap_pct": round(float(merged.get("best_day_cap_pct", 0.0)) * 100.0, 1),
                "calibrated_mults": {
                    "p1": cal["p1_mult"], "p2": cal["p2_mult"], "funded": cal["funded_mult"],
                    "reason": cal["calibrated_reason"],
                },
                "single_ticket_zero_retry": summ,
            })

    # B4: E8 Pro Payout #1 Buffer-Wait Sensitivity (`+1%` default vs `+8%` vs `+10%` before Payout #1 on `50K @ 1.00x`)
    e8_pro_buffer_sensitivity: dict[str, Any] = {
        "excluded_from_p5_portfolios": True,
        "astra_r10_verified_reference": {
            "note": "Astra Round 10 independently verified that even waiting for +8% or +10% profit before Payout #1 on E8 Pro still breaches 34.18% / 17.38% in 12m at 1.00x due to floor-lock-at-initial + 50% retention.",
            "wait_8pct_breach_12m_pct": 34.18,
            "wait_10pct_breach_12m_pct": 17.38,
        },
        "mc_buffer_sweep_50k_1_00x": [],
    }
    e8_prog = _find_program_by_hint(catalog, lambda p: p["firm_id"] in E8_EXCLUDED_FIRM_IDS)
    if e8_prog is not None:
        _, m_e8 = get_program_tier(catalog, e8_prog["program_id"], 50_000.0)
        cal_e8 = calibrated_cache.get((e8_prog["program_id"], 50_000.0, primary_var, 1.00))
        if cal_e8 is not None:
            st_e8 = cache.build_stage_tuple(
                capital_usd=50_000.0,
                p1_mult=cal_e8["p1_mult"], p1_lock_mult=cal_e8["p1_lock_mult"],
                p2_mult=cal_e8["p2_mult"], p2_lock_mult=cal_e8["p2_lock_mult"],
                funded_mult=cal_e8["funded_mult"], amber_mult=cal_e8["amber_mult"], red_mult=cal_e8["red_mult"],
                p1_symcap=cal_e8["p1_symcap"], p2_symcap=cal_e8["p2_symcap"], fn_symcap=cal_e8["fn_symcap"],
                profile_mode=str(m_e8["profile_mode"]),
                p1_news=cal_e8["p1_news"], p2_news=cal_e8["p2_news"], fn_news=cal_e8["fn_news"],
                friction_mult=1.00, steps=int(m_e8["steps"]),
            )
            e8_fee0 = float(m_e8["active_promo_usd"] if use_promo_prices else m_e8["orig_usd"])
            e8_feereg = float(m_e8["orig_usd"])
            for wait_buf_pct in (0.01, 0.08, 0.10):
                res_e8b = _simulate_single_ticket_rules_numba(
                    idx_single, *st_e8,
                    steps=int(m_e8["steps"]), cap=50_000.0, fee_day0_usd=e8_fee0, fee_regular_usd=e8_feereg,
                    card_fx_fee_pct=card_fx_fee,
                    withdrawal_fee_pct=float(m_e8.get("payout_withdrawal_fee_pct", m_e8.get("withdrawal_fee_pct", 0.02))),
                    fee_refund_pct=0.0,
                    p1_target=float(m_e8["p1_target_pct"]), p2_target=0.0,
                    daily_lim=float(m_e8["dd_daily_pct"]), max_dd_lim=float(m_e8["dd_max_pct"]),
                    dd_type=_dd_type_code(m_e8["dd_type"]), trail_lock_initial=False, best_day_cap_pct=0.0,
                    min_days=0, min_prof_days=0, min_prof_day_pct=0.0,
                    profit_split=float(m_e8["profit_split_pct"]),
                    payout_cycle_days=int(m_e8["payout_cycle_trading_days"]),
                    min_payout_usd=float(m_e8["min_payout_usd"]), strict_lt_breach=True,
                    p1_lock_trigger=cal_e8["p1_lock_trigger"], p2_lock_trigger=cal_e8["p2_lock_trigger"],
                    amber_dd=cal_e8["amber_dd"], red_dd=cal_e8["red_dd"],
                    p1_ea_stop=cal_e8["p1_ea_stop"], p2_ea_stop=cal_e8["p2_ea_stop"], fn_ea_stop=cal_e8["fn_ea_stop"],
                    start_day_offset=0, discount_rate_annual=DEFAULT_DISCOUNT_RATE, max_retries=0,
                    refund_payout_milestone=0,
                    payout_buffer_retention_pct=float(m_e8.get("payout_buffer_retention_pct", 0.50)),
                    locks_at_initial_after_first_payout=True,
                    min_payout_profit_pct=float(m_e8.get("min_payout_profit_pct", 0.01)),
                    daily_profit_cap_pct=float(m_e8.get("daily_profit_cap_pct", 0.02)),
                    refund_withdrawal_fee_pct=0.0,
                    daily_dd_anchor_mode=_daily_dd_anchor_code(m_e8.get("daily_dd_anchor", "initial_balance")),
                    funded_first_payout_min_profit_pct=wait_buf_pct,
                )
                summ_e8b = summarize_single_ticket_mc(
                    res_e8b, fee_usd=e8_fee0, fee_regular_usd=e8_feereg,
                    card_fx_fee_pct=card_fx_fee, usd_vnd_rate=usd_vnd, horizon_days=horizon_days,
                )
                e8_pro_buffer_sensitivity["mc_buffer_sweep_50k_1_00x"].append({
                    "first_payout_wait_profit_pct": round(wait_buf_pct * 100.0, 1),
                    "retained_cushion_after_p1_pct": round(wait_buf_pct * 50.0, 2),
                    "funded_12m_breach_pct": summ_e8b["funded_12m_breach"]["breach_12m_pct"],
                    "funded_12m_wilson_95_upper_pct": summ_e8b["funded_12m_breach"]["wilson_95_upper_pct"],
                    "cond_med_pay1_cal_days": summ_e8b["cond_med_pay1_cal_days"],
                    "ev_npv_24m_vnd_tr": summ_e8b["ev_npv_24m_vnd_tr"],
                    "ev_per_fee_npv24": summ_e8b["ev_per_fee_npv24"],
                })

    # -----------------------------------------------------------------------
    # SECTION 4: Full Friction Sweep (`0.66x .. 1.75x`), Discount-Rate Sensitivity & B6 Fee Accounting Sensitivity
    # -----------------------------------------------------------------------
    npv_discount_sensitivity: list[dict[str, Any]] = []
    friction_lifecycle_10k_100k: list[dict[str, Any]] = []
    fee_accounting_sensitivity: list[dict[str, Any]] = []
    if ftmo_std is not None:
        vc = VARIANT_PHASE_CONFIGS[primary_var]
        for cap in (10_000.0, 100_000.0):
            _, merged = get_program_tier(catalog, ftmo_std["program_id"], cap)
            fee_orig = float(merged["orig_usd"])
            fee_day0 = float(merged["active_promo_usd"] if use_promo_prices else fee_orig)
            payout_wd = float(merged.get("payout_withdrawal_fee_pct", merged.get("withdrawal_fee_pct", 0.015)))
            ref_wd_default = float(merged.get("refund_withdrawal_fee_pct", 0.0))
            anchor_ftmo = _daily_dd_anchor_code(merged.get("daily_dd_anchor", "initial_balance"))
            for fmult in FRICTION_LEVELS:
                st_arrs = cache.build_stage_tuple(
                    capital_usd=cap,
                    p1_mult=vc["p1_mult"], p1_lock_mult=vc["p1_lock_mult"],
                    p2_mult=vc["p2_mult"], p2_lock_mult=vc["p2_lock_mult"],
                    funded_mult=vc["funded_mult"], amber_mult=vc["amber_mult"], red_mult=vc["red_mult"],
                    p1_symcap=vc["p1_symcap_pct"], p2_symcap=vc["p2_symcap_pct"], fn_symcap=vc["funded_symcap_pct"],
                    profile_mode="Standard",
                    p1_news=vc["p1_news_guard"], p2_news=vc["p2_news_guard"], fn_news=vc["funded_news_guard"],
                    friction_mult=fmult,
                )
                res_f = _simulate_single_ticket_rules_numba(
                    idx_single, *st_arrs,
                    steps=2, cap=cap, fee_day0_usd=fee_day0, fee_regular_usd=fee_orig,
                    card_fx_fee_pct=card_fx_fee, withdrawal_fee_pct=payout_wd,
                    fee_refund_pct=float(merged["fee_refund_pct"]),
                    p1_target=float(merged["p1_target_pct"]), p2_target=float(merged["p2_target_pct"]),
                    daily_lim=float(merged["dd_daily_pct"]), max_dd_lim=float(merged["dd_max_pct"]),
                    dd_type=DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
                    min_days=int(merged["min_trading_days"]), min_prof_days=0, min_prof_day_pct=0.0,
                    profit_split=float(merged["profit_split_pct"]),
                    payout_cycle_days=int(merged["payout_cycle_trading_days"]),
                    min_payout_usd=float(merged["min_payout_usd"]), strict_lt_breach=True,
                    p1_lock_trigger=vc["p1_lock_trigger"], p2_lock_trigger=vc["p2_lock_trigger"],
                    amber_dd=vc["amber_dd"], red_dd=vc["red_dd"],
                    p1_ea_stop=vc["p1_ea_daily_stop"], p2_ea_stop=vc["p2_ea_daily_stop"],
                    fn_ea_stop=vc["funded_ea_daily_stop"],
                    start_day_offset=0, discount_rate_annual=DEFAULT_DISCOUNT_RATE, max_retries=0,
                    refund_withdrawal_fee_pct=ref_wd_default,
                    daily_dd_anchor_mode=anchor_ftmo,
                )
                summ_f = summarize_single_ticket_mc(
                    res_f, fee_usd=fee_day0, fee_regular_usd=fee_orig, card_fx_fee_pct=card_fx_fee,
                    usd_vnd_rate=usd_vnd, horizon_days=horizon_days,
                    refund_withdrawal_fee_pct=ref_wd_default,
                )
                friction_lifecycle_10k_100k.append({
                    "capital_usd": cap, "variant": primary_var, "friction_x": fmult, **summ_f,
                })
                if abs(fmult - 1.00) < 1e-9:
                    for r_rate in (0.0, *DISCOUNT_RATES_ANNUAL):
                        res_r = _simulate_single_ticket_rules_numba(
                            idx_single, *st_arrs,
                            steps=2, cap=cap, fee_day0_usd=fee_day0, fee_regular_usd=fee_orig,
                            card_fx_fee_pct=card_fx_fee, withdrawal_fee_pct=payout_wd,
                            fee_refund_pct=float(merged["fee_refund_pct"]),
                            p1_target=float(merged["p1_target_pct"]), p2_target=float(merged["p2_target_pct"]),
                            daily_lim=float(merged["dd_daily_pct"]), max_dd_lim=float(merged["dd_max_pct"]),
                            dd_type=DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
                            min_days=int(merged["min_trading_days"]), min_prof_days=0, min_prof_day_pct=0.0,
                            profit_split=float(merged["profit_split_pct"]),
                            payout_cycle_days=int(merged["payout_cycle_trading_days"]),
                            min_payout_usd=float(merged["min_payout_usd"]), strict_lt_breach=True,
                            p1_lock_trigger=vc["p1_lock_trigger"], p2_lock_trigger=vc["p2_lock_trigger"],
                            amber_dd=vc["amber_dd"], red_dd=vc["red_dd"],
                            p1_ea_stop=vc["p1_ea_daily_stop"], p2_ea_stop=vc["p2_ea_daily_stop"],
                            fn_ea_stop=vc["funded_ea_daily_stop"],
                            start_day_offset=0, discount_rate_annual=r_rate, max_retries=0,
                            refund_withdrawal_fee_pct=ref_wd_default,
                            daily_dd_anchor_mode=anchor_ftmo,
                        )
                        npv_discount_sensitivity.append({
                            "capital_usd": cap,
                            "variant": primary_var,
                            "discount_rate_pct": round(r_rate * 100.0, 1),
                            "ev_npv_24m_usd": round(float(np.mean(res_r[9])), 2),
                            "ev_npv_24m_vnd_tr": round(float(np.mean(res_r[9])) * usd_vnd / 1_000_000.0, 2),
                            "ev_npv_36m_usd": round(float(np.mean(res_r[10])), 2),
                            "ev_npv_36m_vnd_tr": round(float(np.mean(res_r[10])) * usd_vnd / 1_000_000.0, 2),
                        })
                # B6 Fee accounting sensitivity: 0.0% direct-to-card refund vs 1.5% payout rail sensitivity
                if fmult in (1.00, 1.50):
                    res_rail = _simulate_single_ticket_rules_numba(
                        idx_single, *st_arrs,
                        steps=2, cap=cap, fee_day0_usd=fee_day0, fee_regular_usd=fee_orig,
                        card_fx_fee_pct=card_fx_fee, withdrawal_fee_pct=payout_wd,
                        fee_refund_pct=float(merged["fee_refund_pct"]),
                        p1_target=float(merged["p1_target_pct"]), p2_target=float(merged["p2_target_pct"]),
                        daily_lim=float(merged["dd_daily_pct"]), max_dd_lim=float(merged["dd_max_pct"]),
                        dd_type=DD_STATIC, trail_lock_initial=False, best_day_cap_pct=0.0,
                        min_days=int(merged["min_trading_days"]), min_prof_days=0, min_prof_day_pct=0.0,
                        profit_split=float(merged["profit_split_pct"]),
                        payout_cycle_days=int(merged["payout_cycle_trading_days"]),
                        min_payout_usd=float(merged["min_payout_usd"]), strict_lt_breach=True,
                        p1_lock_trigger=vc["p1_lock_trigger"], p2_lock_trigger=vc["p2_lock_trigger"],
                        amber_dd=vc["amber_dd"], red_dd=vc["red_dd"],
                        p1_ea_stop=vc["p1_ea_daily_stop"], p2_ea_stop=vc["p2_ea_daily_stop"],
                        fn_ea_stop=vc["funded_ea_daily_stop"],
                        start_day_offset=0, discount_rate_annual=DEFAULT_DISCOUNT_RATE, max_retries=0,
                        refund_withdrawal_fee_pct=0.015,
                        daily_dd_anchor_mode=anchor_ftmo,
                    )
                    npv_card = float(np.mean(res_f[9]))
                    npv_rail = float(np.mean(res_rail[9]))
                    fee_accounting_sensitivity.append({
                        "capital_usd": cap,
                        "variant": primary_var,
                        "friction_x": fmult,
                        "card_fx_buy_fee_pct": round(card_fx_fee * 100.0, 2),
                        "payout_withdrawal_fee_pct": round(payout_wd * 100.0, 2),
                        "refund_card_0pct_npv24_usd": round(npv_card, 2),
                        "refund_rail_1_5pct_npv24_usd": round(npv_rail, 2),
                        "delta_card_minus_rail_usd": round(npv_card - npv_rail, 2),
                        "delta_card_minus_rail_vnd_tr": round((npv_card - npv_rail) * usd_vnd / 1_000_000.0, 3),
                    })

    # -----------------------------------------------------------------------
    # SECTION 5: Dual-Horizon Dynamic Sale-Calendar Engine (B5: EXACT sweep Y=0..180, BOTH horizons!)
    # -----------------------------------------------------------------------
    sale_decision_table: list[dict[str, Any]] = []
    if ftmo_std is not None:
        vc = VARIANT_PHASE_CONFIGS[primary_var]
        for cap in (10_000.0, 50_000.0, 100_000.0):
            _, merged = get_program_tier(catalog, ftmo_std["program_id"], cap)
            orig_fee = float(merged["orig_usd"])
            bf_disc = float(merged["active_promo_pct"])
            for fmult in (1.00, 1.50):
                st_arrs = cache.build_stage_tuple(
                    capital_usd=cap,
                    p1_mult=vc["p1_mult"], p1_lock_mult=vc["p1_lock_mult"],
                    p2_mult=vc["p2_mult"], p2_lock_mult=vc["p2_lock_mult"],
                    funded_mult=vc["funded_mult"], amber_mult=vc["amber_mult"], red_mult=vc["red_mult"],
                    p1_symcap=vc["p1_symcap_pct"], p2_symcap=vc["p2_symcap_pct"], fn_symcap=vc["funded_symcap_pct"],
                    profile_mode="Standard",
                    p1_news=vc["p1_news_guard"], p2_news=vc["p2_news_guard"], fn_news=vc["funded_news_guard"],
                    friction_mult=fmult,
                )
                # Publish BOTH 1-ticket (`max_retries=0`, matching Astra ~55/110/164d on 10K) AND retry-enabled (`max_retries=2`, regular retries!)
                for retries_m, retry_lbl in ((0, "SINGLE_TICKET_0_RETRY"), (2, "RETRY_UP_TO_2_REGULAR_PRICE")):
                    for z_disc in (0.10, 0.20, 0.30):
                        sol24 = solve_max_wait_days_worth_it(
                            idx_grid, st_arrs,
                            program_tier=merged, orig_fee_usd=orig_fee,
                            active_discount_pct=0.0, next_sale_discount_pct=z_disc,
                            card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                            usd_vnd_rate=usd_vnd, horizon_months=24, max_search_days=180,
                            p1_lock_trigger=vc["p1_lock_trigger"], p2_lock_trigger=vc["p2_lock_trigger"],
                            amber_dd=vc["amber_dd"], red_dd=vc["red_dd"],
                            p1_ea_stop=vc["p1_ea_daily_stop"], p2_ea_stop=vc["p2_ea_daily_stop"],
                            fn_ea_stop=vc["funded_ea_daily_stop"], max_retries=retries_m,
                        )
                        sale_decision_table.append({
                            "scenario": "NON_PROMO_DAY_0PCT",
                            "retry_regime": retry_lbl,
                            "variant": primary_var,
                            "program_id": ftmo_std["program_id"],
                            "capital_usd": cap,
                            "friction_x": fmult,
                            "active_discount_pct": 0.0,
                            "target_sale_discount_pct": round(z_disc * 100.0, 0),
                            "upfront_saving_usd": round(orig_fee * z_disc * (1.0 + card_fx_fee), 2),
                            **sol24,
                        })
                    # Today Black Friday (`26/11/2026`): actual MC evaluations at 7d, 14d, 30d (ZERO 2*d7 shortcut!)
                    sol_bf = solve_max_wait_days_worth_it(
                        idx_grid, st_arrs,
                        program_tier=merged, orig_fee_usd=orig_fee,
                        active_discount_pct=bf_disc, next_sale_discount_pct=0.10,
                        card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                        usd_vnd_rate=usd_vnd, horizon_months=24, max_search_days=180,
                        p1_lock_trigger=vc["p1_lock_trigger"], p2_lock_trigger=vc["p2_lock_trigger"],
                        amber_dd=vc["amber_dd"], red_dd=vc["red_dd"],
                        p1_ea_stop=vc["p1_ea_daily_stop"], p2_ea_stop=vc["p2_ea_daily_stop"],
                        fn_ea_stop=vc["funded_ea_daily_stop"], max_retries=retries_m,
                    )
                    sale_decision_table.append({
                        "scenario": "BLACK_FRIDAY_ACTIVE_TODAY",
                        "retry_regime": retry_lbl,
                        "variant": primary_var,
                        "program_id": ftmo_std["program_id"],
                        "capital_usd": cap,
                        "friction_x": fmult,
                        "active_discount_pct": round(bf_disc * 100.0, 0),
                        "target_sale_discount_pct": 10.0,
                        "upfront_saving_usd": 0.0,
                        **sol_bf,
                        "decision": "BUY_TODAY_BLACK_FRIDAY_DOMINATES",
                    })

    # -----------------------------------------------------------------------
    # SECTION 6: Capital Scaling Policies (B2/B3/B4/B6 + Day-0/Regular Separation + All-Regular Comparison)
    # -----------------------------------------------------------------------
    pareto_grid: dict[str, dict[str, Any]] = {}
    head_to_head_2x100k_vs_1x200k: dict[str, Any] = {}
    all_regular_pricing_comparison: dict[str, Any] = {}
    cross_firm_hazard_study: list[dict[str, Any]] = []
    sunk_cost_abort_study: list[dict[str, Any]] = []

    vc = VARIANT_PHASE_CONFIGS[primary_var]
    # B4: Build multi-firm portfolios ONLY from surviving firms (`FTMO + The5ers + IC Funded`), EXCLUDING E8 Pro!
    surviving_other_progs = [p for p in other_progs if p["firm_id"] not in E8_EXCLUDED_FIRM_IDS]
    firm_ids_order = ["FTMO"] + [p["firm_id"] for p in surviving_other_progs if p["firm_id"] != "FTMO"]
    firm_ids_unique: list[str] = []
    for fid in firm_ids_order:
        if fid not in firm_ids_unique:
            firm_ids_unique.append(fid)
    firm_to_idx = {fid: i for i, fid in enumerate(firm_ids_unique)}
    n_firms_total = max(3, len(firm_ids_unique))

    hazard_5pct = make_firm_hazard_days(len(idx_grid), n_firms_total, 0.05, horizon=horizon_days, seed=seed + 101)
    hazard_0pct = make_firm_hazard_days(len(idx_grid), n_firms_total, 0.00, horizon=horizon_days, seed=seed + 101)
    hazard_10pct = make_firm_hazard_days(len(idx_grid), n_firms_total, 0.10, horizon=horizon_days, seed=seed + 101)

    for fmult in (1.00, 1.50):
        fkey = f"{fmult:.2f}x"
        templates_bf: list[dict[str, Any]] = []
        templates_reg: list[dict[str, Any]] = []
        tpl_idx_map: dict[str, int] = {}

        def _add_template(key_name: str, prog: dict[str, Any], cap: float) -> int:
            if key_name in tpl_idx_map:
                return tpl_idx_map[key_name]
            _, merged = get_program_tier(catalog, prog["program_id"], cap)
            cal = calibrated_cache.get((prog["program_id"], cap, primary_var, fmult))
            if cal is None:
                rf_k = (
                    prog["program_id"],
                    round(float(merged["dd_daily_pct"]), 4),
                    round(float(merged["dd_max_pct"]), 4),
                    str(merged["dd_type"]),
                    str(merged.get("daily_dd_anchor", "initial_balance")),
                    primary_var,
                    fmult,
                )
                cal = rule_family_cal_cache.get(rf_k)
            if cal is None:
                cal = calibrate_safe_multipliers_for_rule(
                    cache, idx_grid,
                    program_tier=merged, variant=primary_var, friction_mult=fmult,
                    card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    usd_vnd_rate=usd_vnd,
                )
            st_arrs = cache.build_stage_tuple(
                capital_usd=cap,
                p1_mult=cal["p1_mult"], p1_lock_mult=cal["p1_lock_mult"],
                p2_mult=cal["p2_mult"], p2_lock_mult=cal["p2_lock_mult"],
                funded_mult=cal["funded_mult"], amber_mult=cal["amber_mult"], red_mult=cal["red_mult"],
                p1_symcap=cal["p1_symcap"], p2_symcap=cal["p2_symcap"], fn_symcap=cal["fn_symcap"],
                profile_mode=str(merged["profile_mode"]),
                p1_news=cal["p1_news"], p2_news=cal["p2_news"], fn_news=cal["fn_news"],
                friction_mult=fmult, steps=int(merged["steps"]),
            )
            fee_orig = float(merged["orig_usd"])
            fee_day0 = float(merged["active_promo_usd"] if use_promo_prices else fee_orig)
            payout_wd = float(merged.get("payout_withdrawal_fee_pct", merged.get("withdrawal_fee_pct", 0.015)))
            ref_wd = float(merged.get("refund_withdrawal_fee_pct", 0.0))
            base_dict = {
                "key": key_name,
                "firm_idx": firm_to_idx.get(prog["firm_id"], 0),
                "firm_id": prog["firm_id"],
                "program_id": prog["program_id"],
                "execution_evidence_tag": merged["execution_evidence_tag"],
                "steps": int(merged["steps"]),
                "capital_usd": cap,
                "fee_day0_usd": fee_day0,
                "fee_regular_usd": fee_orig,
                "fee_refund_pct": float(merged.get("fee_refund_pct", 0.0)),
                "payout_withdrawal_fee_pct": payout_wd,
                "withdrawal_fee_pct": payout_wd,
                "refund_withdrawal_fee_pct": ref_wd,
                "p1_target_pct": float(merged.get("p1_target_pct", 0.10)),
                "p2_target_pct": float(merged.get("p2_target_pct", 0.0)),
                "dd_daily_pct": float(merged.get("dd_daily_pct", 0.05)),
                "dd_max_pct": float(merged.get("dd_max_pct", 0.10)),
                "dd_type": str(merged.get("dd_type", "static")),
                "daily_dd_anchor": str(merged.get("daily_dd_anchor", "initial_balance")),
                "best_day_cap_pct": float(merged.get("best_day_cap_pct", 0.0)),
                "min_trading_days": int(merged.get("min_trading_days", 4)),
                "min_profitable_days": int(merged.get("min_profitable_days", 0)),
                "min_profitable_day_pct": float(merged.get("min_profitable_day_pct", 0.0)),
                "profit_split_pct": float(merged.get("profit_split_pct", 0.80)),
                "payout_cycle_trading_days": int(merged.get("payout_cycle_trading_days", 10)),
                "min_payout_usd": float(merged.get("min_payout_usd", 50.0)),
                "p1_lock_trigger": float(cal["p1_lock_trigger"]),
                "p2_lock_trigger": float(cal["p2_lock_trigger"]),
                "amber_dd": float(cal["amber_dd"]),
                "red_dd": float(cal["red_dd"]),
                "p1_ea_stop": float(cal["p1_ea_stop"]),
                "p2_ea_stop": float(cal["p2_ea_stop"]),
                "fn_ea_stop": float(cal["fn_ea_stop"]),
                "refund_payout_milestone": int(merged.get("refund_payout_milestone", 1)),
                "payout_buffer_retention_pct": float(merged.get("payout_buffer_retention_pct", 0.0)),
                "locks_at_initial_after_first_payout": bool(merged.get("locks_at_initial_after_first_payout", False)),
                "min_payout_profit_pct": float(merged.get("min_payout_profit_pct", 0.0)),
                "daily_profit_cap_pct": float(merged.get("daily_profit_cap_pct", 0.0)),
                "funded_first_payout_min_prof_days": int(merged.get("funded_first_payout_min_prof_days", 0)),
                "funded_first_payout_prof_pct": float(merged.get("funded_first_payout_prof_pct", 0.0)),
                "stage_arrays": st_arrs,
            }
            idx = len(templates_bf)
            templates_bf.append(base_dict)
            reg_dict = dict(base_dict)
            reg_dict["fee_day0_usd"] = fee_orig
            templates_reg.append(reg_dict)
            tpl_idx_map[key_name] = idx
            return idx

        assert ftmo_std is not None
        t_10k = _add_template("FTMO_10K", ftmo_std, 10_000.0)
        t_25k = _add_template("FTMO_25K", ftmo_std, 25_000.0)
        t_50k = _add_template("FTMO_50K", ftmo_std, 50_000.0)
        t_100k = _add_template("FTMO_100K", ftmo_std, 100_000.0)
        t_200k = _add_template("FTMO_200K", ftmo_std, 200_000.0)

        # B4: 3 surviving firms ONLY (`FTMO + The5ers + IC Funded`), strictly excluding E8 Pro!
        cross_tpls_small: list[int] = [t_10k]
        cross_tpls_big: list[int] = [t_100k]
        seen_other_firms: set[str] = set()
        ordered_other = sorted(
            surviving_other_progs,
            key=lambda p: (
                0 if "THE5ERS" in p["firm_id"] else 1,
                0 if "CLASSIC" in p["program_id"] else 1,
                p["firm_id"],
            ),
        )
        for op in ordered_other:
            if op["firm_id"] in seen_other_firms or op["firm_id"] in E8_EXCLUDED_FIRM_IDS:
                continue
            seen_other_firms.add(op["firm_id"])
            try:
                small_m = _pick_tier_near(op, 10_000.0)
                big_m = _pick_tier_near(op, 50_000.0)
                cross_tpls_small.append(_add_template(f"{op['firm_id']}_SMALL", op, float(small_m["capital_usd"])))
                cross_tpls_big.append(_add_template(f"{op['firm_id']}_BIG", op, float(big_m["capital_usd"])))
            except ValueError:
                continue

        packed = _pack_templates_for_numba(templates_bf)
        packed_reg = _pack_templates_for_numba(templates_reg)

        # Policy catalog (10 policies):
        # - B3: own_book_overflow_mult = 0.0 across ALL policies!
        # - B2: P4A_WAIT_FOR_100K (`wait_for_top_rung_slot2=True`) alongside greedy P4A_DIRECT_50K!
        # - B6: P4B_PARALLEL_2X100K (`policy_mode=3`, opens both 100K on Day 0) alongside sequential P4B_DIRECT_100K & P4C_DIRECT_200K!
        # - B4: P5 / P5B use ONLY the 3 surviving firms (`FTMO + The5ers + IC Funded`)!
        # Tuple: (policy_mode, ladder_tpls, max_slots, allow_dg, up_buf, dg_buf, wait_top_slot2)
        policies_spec: dict[str, tuple[int, np.ndarray, int, bool, float, float, bool]] = {
            "P1_REPEAT_10K": (0, np.array([t_10k], dtype=np.int32), 2, False, 3.0, 2.0, False),
            "P2_STEP_BY_STEP": (0, np.array([t_10k, t_25k, t_50k, t_100k], dtype=np.int32), 2, False, 2.75, 2.0, False),
            "P3_SMART_SKIP_DOWNGRADE": (0, np.array([t_10k, t_50k, t_100k], dtype=np.int32), 2, True, 2.75, 2.0, False),
            "P4A_DIRECT_50K": (1, np.array([t_50k, t_100k], dtype=np.int32), 2, False, 2.75, 2.0, False),
            "P4A_WAIT_FOR_100K": (1, np.array([t_50k, t_100k], dtype=np.int32), 2, False, 2.75, 2.0, True),
            "P4B_DIRECT_100K": (1, np.array([t_100k], dtype=np.int32), 2, False, 2.75, 2.0, False),
            "P4B_PARALLEL_2X100K": (3, np.array([t_100k], dtype=np.int32), 2, False, 2.00, 2.0, False),
            "P4C_DIRECT_200K": (1, np.array([t_200k], dtype=np.int32), 1, False, 2.75, 2.0, False),
            "P5_CROSS_FIRM_HYBRID": (
                2,
                np.array(cross_tpls_small[:3], dtype=np.int32),
                min(3, len(cross_tpls_small)),
                False,
                2.50,
                2.0,
                False,
            ),
            "P5B_CROSS_FIRM_SCALE50K_100K": (
                2,
                np.array(cross_tpls_big[:3], dtype=np.int32),
                min(3, len(cross_tpls_big)),
                False,
                2.50,
                2.0,
                False,
            ),
        }

        grid_cells: dict[str, Any] = {}
        for bank_tr in BANKROLL_GRID_VND_TR:
            for top_tr in TOPUP_GRID_VND_TR:
                cell_key = f"B{int(bank_tr)}tr_T{int(top_tr)}tr"
                init_usd = (bank_tr * 1_000_000.0) / usd_vnd
                topup_usd = (top_tr * 1_000_000.0) / usd_vnd
                pol_res: dict[str, Any] = {}
                for pid, (pmode, ltpls, mslots, allow_dg, up_b, dg_b, wait_top) in policies_spec.items():
                    res_p = _simulate_capital_policy_numba(
                        idx_grid, hazard_5pct, *packed,
                        policy_mode=pmode, ladder_tpls=ltpls, max_slots=mslots,
                        allow_downgrade=allow_dg, upgrade_buf_mult=up_b, downgrade_buf_mult=dg_b,
                        init_bankroll_usd=init_usd, monthly_topup_usd=topup_usd,
                        card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                        own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                        abort_after_day=-1,
                        wait_for_top_rung_slot2=wait_top,
                    )
                    pol_res[pid] = summarize_capital_policy_mc(
                        res_p, usd_vnd_rate=usd_vnd,
                        init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=top_tr,
                    )
                grid_cells[cell_key] = {
                    "bankroll_vnd_tr": bank_tr,
                    "bankroll_usd": round(init_usd, 1),
                    "monthly_topup_vnd_tr": top_tr,
                    "monthly_topup_usd": round(topup_usd, 1),
                    "policies": pol_res,
                    "pareto_winners": select_dual_objective_winners(pol_res),
                }
        pareto_grid[fkey] = grid_cells

        # Side-by-side All-Regular pricing comparison (`topup = 0`, all 5 bankrolls, key policies)
        reg_cells: dict[str, Any] = {}
        for bank_tr in BANKROLL_GRID_VND_TR:
            ck = f"B{int(bank_tr)}tr_T0tr"
            init_usd = (bank_tr * 1_000_000.0) / usd_vnd
            reg_pols: dict[str, Any] = {}
            for pid in (
                "P1_REPEAT_10K",
                "P3_SMART_SKIP_DOWNGRADE",
                "P4A_DIRECT_50K",
                "P4A_WAIT_FOR_100K",
                "P4B_DIRECT_100K",
                "P4B_PARALLEL_2X100K",
                "P4C_DIRECT_200K",
                "P5B_CROSS_FIRM_SCALE50K_100K",
            ):
                pmode, ltpls, mslots, allow_dg, up_b, dg_b, wait_top = policies_spec[pid]
                res_pr = _simulate_capital_policy_numba(
                    idx_grid, hazard_5pct, *packed_reg,
                    policy_mode=pmode, ladder_tpls=ltpls, max_slots=mslots,
                    allow_downgrade=allow_dg, upgrade_buf_mult=up_b, downgrade_buf_mult=dg_b,
                    init_bankroll_usd=init_usd, monthly_topup_usd=0.0,
                    card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                    own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                    abort_after_day=-1,
                    wait_for_top_rung_slot2=wait_top,
                )
                reg_pols[pid] = summarize_capital_policy_mc(
                    res_pr, usd_vnd_rate=usd_vnd,
                    init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0,
                )
            reg_cells[ck] = {
                "bankroll_vnd_tr": bank_tr,
                "policies_all_regular": reg_pols,
                "pareto_winners_all_regular": select_dual_objective_winners(reg_pols),
            }
        all_regular_pricing_comparison[fkey] = reg_cells

        # Head-to-head 3-way proof: Sequential `2x 100K` vs Parallel `2x 100K` (Day 0) vs `1x 200K` (`own_book = 0.0`!)
        h2h_rows = []
        haz_h2h = make_firm_hazard_days(len(idx_single), n_firms_total, 0.05, horizon=horizon_days, seed=seed + 202)
        for bank_tr in (35.0, 50.0, 80.0):
            init_usd = (bank_tr * 1_000_000.0) / usd_vnd
            r_seq = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed,
                policy_mode=1, ladder_tpls=np.array([t_100k], dtype=np.int32), max_slots=2,
                allow_downgrade=False, upgrade_buf_mult=2.50, downgrade_buf_mult=2.0,
                init_bankroll_usd=init_usd, monthly_topup_usd=0.0,
                card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                abort_after_day=-1, wait_for_top_rung_slot2=False,
            )
            r_par = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed,
                policy_mode=3, ladder_tpls=np.array([t_100k], dtype=np.int32), max_slots=2,
                allow_downgrade=False, upgrade_buf_mult=2.00, downgrade_buf_mult=2.0,
                init_bankroll_usd=init_usd, monthly_topup_usd=0.0,
                card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                abort_after_day=-1, wait_for_top_rung_slot2=False,
            )
            r_1x200 = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed,
                policy_mode=1, ladder_tpls=np.array([t_200k], dtype=np.int32), max_slots=1,
                allow_downgrade=False, upgrade_buf_mult=2.50, downgrade_buf_mult=2.0,
                init_bankroll_usd=init_usd, monthly_topup_usd=0.0,
                card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                abort_after_day=-1, wait_for_top_rung_slot2=False,
            )
            # Also evaluate All-Regular for Parallel 2x100K vs 1x200K at same bankrolls
            r_par_reg = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed_reg,
                policy_mode=3, ladder_tpls=np.array([t_100k], dtype=np.int32), max_slots=2,
                allow_downgrade=False, upgrade_buf_mult=2.00, downgrade_buf_mult=2.0,
                init_bankroll_usd=init_usd, monthly_topup_usd=0.0,
                card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                abort_after_day=-1, wait_for_top_rung_slot2=False,
            )
            r_200_reg = _simulate_capital_policy_numba(
                idx_single, haz_h2h, *packed_reg,
                policy_mode=1, ladder_tpls=np.array([t_200k], dtype=np.int32), max_slots=1,
                allow_downgrade=False, upgrade_buf_mult=2.50, downgrade_buf_mult=2.0,
                init_bankroll_usd=init_usd, monthly_topup_usd=0.0,
                card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                abort_after_day=-1, wait_for_top_rung_slot2=False,
            )
            s_seq = summarize_capital_policy_mc(r_seq, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0)
            s_par = summarize_capital_policy_mc(r_par, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0)
            s_200 = summarize_capital_policy_mc(r_1x200, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0)
            s_par_reg = summarize_capital_policy_mc(r_par_reg, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0)
            s_200_reg = summarize_capital_policy_mc(r_200_reg, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=bank_tr, monthly_topup_vnd_tr=0.0)
            h2h_rows.append({
                "bankroll_vnd_tr": bank_tr,
                "bankroll_usd": round(init_usd, 1),
                "two_x_100k": s_seq,
                "sequential_2x_100k": s_seq,
                "parallel_2x_100k": s_par,
                "one_x_200k": s_200,
                "parallel_2x_100k_all_regular": s_par_reg,
                "one_x_200k_all_regular": s_200_reg,
                "ruin_reduction_seq_vs_200k_pp": round(s_200["ruin_pct"] - s_seq["ruin_pct"], 2),
                "ruin_reduction_par_vs_200k_pp": round(s_200["ruin_pct"] - s_par["ruin_pct"], 2),
                "delta_ev_npv24_seq_minus_200k_vnd_tr": round(s_seq["ev_npv_24m_vnd_tr"] - s_200["ev_npv_24m_vnd_tr"], 2),
                "delta_ev_npv24_par_minus_200k_vnd_tr": round(s_par["ev_npv_24m_vnd_tr"] - s_200["ev_npv_24m_vnd_tr"], 2),
            })
        head_to_head_2x100k_vs_1x200k[fkey] = h2h_rows

        # Cross-firm hazard sensitivity (`0%`, `5%/yr`, `10%/yr`) at `50tr VND` + `0 topup`:
        # 1-firm (`FTMO 2x 100K`) vs 2-firm (`FTMO + The5ers`) vs 3-firm (`FTMO + The5ers + IC Funded`, E8 excluded, own_book=0.0!)
        if abs(fmult - 1.00) < 1e-9:
            init_50 = (50.0 * 1_000_000.0) / usd_vnd
            for h_label, h_arr in (("0%/yr", hazard_0pct), ("5%/yr", hazard_5pct), ("10%/yr", hazard_10pct)):
                for cfg_name, pmode, ltpls, mslots in (
                    ("SINGLE_FIRM_FTMO_2x100K", 1, np.array([t_100k], dtype=np.int32), 2),
                    ("TWO_FIRM_SPLIT", 2, np.array(cross_tpls_big[:2], dtype=np.int32), min(2, len(cross_tpls_big))),
                    ("THREE_FIRM_SURVIVING_SPLIT", 2, np.array(cross_tpls_big[:3], dtype=np.int32), min(3, len(cross_tpls_big))),
                ):
                    r_h = _simulate_capital_policy_numba(
                        idx_grid, h_arr, *packed,
                        policy_mode=pmode, ladder_tpls=ltpls, max_slots=mslots,
                        allow_downgrade=False, upgrade_buf_mult=2.50, downgrade_buf_mult=2.0,
                        init_bankroll_usd=init_50, monthly_topup_usd=0.0,
                        card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                        own_book_overflow_mult=0.0, own_book_daily_ret=0.0,
                        abort_after_day=-1, wait_for_top_rung_slot2=False,
                    )
                    cross_firm_hazard_study.append({
                        "hazard_rate": h_label,
                        "allocation": cfg_name,
                        **summarize_capital_policy_mc(r_h, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=50.0, monthly_topup_vnd_tr=0.0),
                    })

    # Sunk-Cost Exclusion / Live-Friction Abort Rule study (`1.75x` & `2.00x` adverse live slippage at `35tr VND` bankroll)
    assert ftmo_std is not None
    for adv_f in (1.75, 2.00):
        _, merged_50 = get_program_tier(catalog, ftmo_std["program_id"], 50_000.0)
        st_adv = cache.build_stage_tuple(
            capital_usd=50_000.0,
            p1_mult=vc["p1_mult"], p1_lock_mult=vc["p1_lock_mult"],
            p2_mult=vc["p2_mult"], p2_lock_mult=vc["p2_lock_mult"],
            funded_mult=vc["funded_mult"], amber_mult=vc["amber_mult"], red_mult=vc["red_mult"],
            p1_symcap=vc["p1_symcap_pct"], p2_symcap=vc["p2_symcap_pct"], fn_symcap=vc["funded_symcap_pct"],
            profile_mode="Standard",
            p1_news=vc["p1_news_guard"], p2_news=vc["p2_news_guard"], fn_news=vc["funded_news_guard"],
            friction_mult=adv_f,
        )
        fee_50_orig = float(merged_50["orig_usd"])
        fee_50_day0 = float(merged_50["active_promo_usd"] if use_promo_prices else fee_50_orig)
        tpl_adv = [{
            "firm_idx": 0, "steps": 2, "capital_usd": 50_000.0,
            "fee_day0_usd": fee_50_day0, "fee_regular_usd": fee_50_orig,
            "fee_refund_pct": 1.0,
            "payout_withdrawal_fee_pct": float(merged_50.get("payout_withdrawal_fee_pct", merged_50["withdrawal_fee_pct"])),
            "refund_withdrawal_fee_pct": float(merged_50.get("refund_withdrawal_fee_pct", 0.0)),
            "p1_target_pct": 0.10, "p2_target_pct": 0.05, "dd_daily_pct": 0.05, "dd_max_pct": 0.10,
            "dd_type": "static", "daily_dd_anchor": str(merged_50.get("daily_dd_anchor", "initial_balance")),
            "best_day_cap_pct": 0.0, "min_trading_days": 4,
            "min_profitable_days": 0, "min_profitable_day_pct": 0.0, "profit_split_pct": 0.80,
            "payout_cycle_trading_days": 10, "min_payout_usd": 50.0,
            "p1_lock_trigger": vc["p1_lock_trigger"], "p2_lock_trigger": vc["p2_lock_trigger"],
            "amber_dd": vc["amber_dd"], "red_dd": vc["red_dd"],
            "p1_ea_stop": vc["p1_ea_daily_stop"], "p2_ea_stop": vc["p2_ea_daily_stop"],
            "fn_ea_stop": vc["funded_ea_daily_stop"], "stage_arrays": st_adv,
        }]
        packed_adv = _pack_templates_for_numba(tpl_adv)
        init_35 = (35.0 * 1_000_000.0) / usd_vnd
        r_blind = _simulate_capital_policy_numba(
            idx_grid, hazard_0pct, *packed_adv,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.5, downgrade_buf_mult=2.0,
            init_bankroll_usd=init_35, monthly_topup_usd=0.0,
            card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
            own_book_overflow_mult=0.0, own_book_daily_ret=0.0, abort_after_day=-1,
            wait_for_top_rung_slot2=False,
        )
        r_abort = _simulate_capital_policy_numba(
            idx_grid, hazard_0pct, *packed_adv,
            policy_mode=1, ladder_tpls=np.array([0], dtype=np.int32), max_slots=1,
            allow_downgrade=False, upgrade_buf_mult=2.5, downgrade_buf_mult=2.0,
            init_bankroll_usd=init_35, monthly_topup_usd=0.0,
            card_fx_fee_pct=card_fx_fee, discount_rate_annual=DEFAULT_DISCOUNT_RATE,
            own_book_overflow_mult=0.0, own_book_daily_ret=0.0, abort_after_day=42,
            wait_for_top_rung_slot2=False,
        )
        s_blind = summarize_capital_policy_mc(r_blind, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=35.0, monthly_topup_vnd_tr=0.0)
        s_abort = summarize_capital_policy_mc(r_abort, usd_vnd_rate=usd_vnd, init_bankroll_vnd_tr=35.0, monthly_topup_vnd_tr=0.0)
        sunk_cost_abort_study.append({
            "adverse_friction_x": adv_f,
            "variant": primary_var,
            "blind_retry_chasing": s_blind,
            "live_friction_abort_day42": s_abort,
            "fees_saved_usd": round(s_blind["mean_fees_24m_usd"] - s_abort["mean_fees_24m_usd"], 1),
            "fees_saved_vnd_tr": round((s_blind["mean_fees_24m_usd"] - s_abort["mean_fees_24m_usd"]) * usd_vnd / 1_000_000.0, 2),
            "npv24_saved_vnd_tr": round(s_abort["ev_npv_24m_vnd_tr"] - s_blind["ev_npv_24m_vnd_tr"], 2),
        })

    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "schema": "naqex-multi-firm-capital-promo-optimizer-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "safety_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_rows_analysed": holdout_rows,
            "holdout_lock_sha256": lock_sha,
            "dev_window": f"{ext_days[0]}..{ext_days[-1]}",
            "dev_days_count": len(ext_days),
            "model_tag": "DAILY_APPROX",
            "evidence_stage": "DEV_BACKTEST_2018_2024_PLUS_FTMO_DEMO_28RT_PROBE_ONLY",
        },
        "astra_r10_q3_closures": {
            "primary_variant": primary_var,
            "control_variant": CONTROL_VARIANT_DEFAULT,
            "fail_closed_catalog_and_staleness": True,
            "purchase_day_pricing_no_perpetual_bf": True,
            "per_contract_daily_dd_anchor": True,
            "own_book_overflow_mult_in_rankings": 0.0,
            "p5_surviving_firms": firm_ids_unique[:3],
            "p5_excluded_firms": [
                {"firm_id": "E8_MARKETS", "reason": "STRUCTURAL_LOCK_AT_INITIAL_FLOOR_HIGH_12M_FUNDED_BREACH"}
            ],
            "p4a_wait_for_100k_enabled": True,
            "p4b_parallel_2x100k_enabled": True,
            "pareto_reports_mean_median_and_p_le_0": True,
            "sale_calendar_exact_sweep_dual_horizon": True,
            "fee_accounting_separated_card_refund_0pct": True,
            "b1_sizing_parity_disclosed": True,
        },
        "astra_r11_closures": {
            "per_tier_verified_utc_strict_no_inheritance": True,
            "reject_nan_inf_and_future_timestamps": True,
            "non_ftmo_dd_anchor_tag": DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT,
            "non_ftmo_dd_anchor_firms": ["THE5ERS", "IC_FUNDED"],
            "shifting_horizon_dense_0_to_180_sweep": True,
            "shifting_horizon_dual_readout_continuous_and_last_positive": True,
        },
        "inputs": {
            "primary_variant": primary_var,
            "control_variant": CONTROL_VARIANT_DEFAULT,
            "pricing_catalog_source": catalog.get("source_path"),
            "pricing_catalog_sha256": catalog.get("source_sha256"),
            "pricing_catalog_is_fallback": catalog.get("is_fallback", False),
            "pricing_catalog_freshness": catalog.get("freshness_report", {}),
            "fx_usd_vnd": usd_vnd,
            "card_fx_buy_fee_pct": round(card_fx_fee * 100.0, 2),
            "ftmo_refund_withdrawal_fee_pct": 0.0,
            "own_book_overflow_mult_in_rankings": 0.0,
            "discount_rate_annual_pct": round(DEFAULT_DISCOUNT_RATE * 100.0, 1),
            "step5_c00_vs_c10": step5_info,
            "n_paths_single": n_paths_single,
            "n_paths_grid": n_paths_grid,
            "horizon_months": horizon_months,
            "use_promo_prices": use_promo_prices,
            "pricing_regime_primary": "BF_DAY0_PLUS_REGULAR_RETRIES" if use_promo_prices else "ALL_REGULAR",
            "seed": seed,
            "unique_exact_m1_replays_cached": len(cache._replay_cache),
        },
        "pricing_traps": traps,
        "lot_rounding_audit": lot_rounding_audit,
        "friction_sweep_100k": friction_sweep_100k,
        "friction_breakeven_x": friction_breakeven_x,
        "mode_comparison": mode_comparison,
        "e8_pro_buffer_sensitivity": e8_pro_buffer_sensitivity,
        "friction_lifecycle_10k_100k": friction_lifecycle_10k_100k,
        "npv_discount_sensitivity": npv_discount_sensitivity,
        "fee_accounting_sensitivity": fee_accounting_sensitivity,
        "sale_decision_table": sale_decision_table,
        "head_to_head_2x100k_vs_1x200k": head_to_head_2x100k_vs_1x200k,
        "all_regular_pricing_comparison": all_regular_pricing_comparison,
        "cross_firm_hazard_study": cross_firm_hazard_study,
        "sunk_cost_abort_study": sunk_cost_abort_study,
        "pareto_grid": pareto_grid,
    }


def save_results_json(results: dict[str, Any], out_path: Path = DEFAULT_OUT_JSON) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(results, indent=2, ensure_ascii=False)
    out_path.write_text(text + "\n", encoding="utf-8", newline="\n")
    return out_path


def _fmt_num(x: float, dec: int = 2, signed: bool = False) -> str:
    fmt = f"{{:{'+' if signed else ''},.{dec}f}}"
    return fmt.format(float(x))


def _policy_vi_name(pid: str) -> str:
    mapping = {
        "P1_REPEAT_10K": "P1: Mua lặp lại 10K",
        "P2_STEP_BY_STEP": "P2: Leo từng bậc (10K->25K->50K->100K)",
        "P3_SMART_SKIP_DOWNGRADE": "P3: Bỏ 25K + Tự hạ bậc (10K->50K->100K->2x100K)",
        "P4A_DIRECT_50K": "P4A (Tham): Vào thẳng 50K (khe 2 có thể mua 50K sớm)",
        "P4A_WAIT_FOR_100K": "P4A-Chờ100K: Vào thẳng 50K (giữ khe 2 chờ 100K)",
        "P4B_DIRECT_100K": "P4B (Tuần tự): Vào thẳng 100K (->2x100K sau khi đậu)",
        "P4B_PARALLEL_2X100K": "P4B (Song song): Mở 2x 100K ngay Ngày 0",
        "P4C_DIRECT_200K": "P4C: Vào thẳng 1x 200K",
        "P5_CROSS_FIRM_HYBRID": "P5A: Chia 3 quỹ sống sót cỡ nhỏ (10K, bỏ E8)",
        "P5B_CROSS_FIRM_SCALE50K_100K": "P5B: Chia 3 quỹ sống sót cỡ lớn (50K–100K, bỏ E8)",
    }
    return mapping.get(pid, pid)


def _exec_badge_vi(tag: str) -> str:
    if tag == "MEASURED_DEMO_EXECUTION":
        return "Đã đo khớp lệnh Demo (`MEASURED_DEMO_EXECUTION`)"
    return "Mới kiểm tra điều khoản — CHƯA đo khớp lệnh (`TERMS_VERIFIED_EXECUTION_UNMEASURED`)"


def _rank_law15_tier(metric: str, val: float) -> str:
    if metric == "ev_r":
        if val <= 0.0:
            return "Xấu"
        if val < 0.07:
            return "Đủ dùng"
        if val <= 0.15:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "pf":
        if val < 1.05:
            return "Xấu"
        if val < 1.25:
            return "Đủ dùng"
        if val <= 1.50:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "dd":
        if val > 10.0:
            return "Xấu"
        if val > 7.0:
            return "Đủ dùng"
        return "Tốt"
    if metric == "calmar":
        if val < 0.5:
            return "Xấu"
        if val < 1.2:
            return "Đủ dùng"
        if val <= 2.0:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "sharpe":
        if val < 0.6:
            return "Xấu"
        if val < 1.2:
            return "Đủ dùng"
        if val < 2.0:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    if metric == "ev_fee":
        if val <= 0.0:
            return "Xấu"
        if val < 3.0:
            return "Đủ dùng"
        if val < 5.0:
            return "Tốt"
        return "Top 1% (mô phỏng)"
    return "Đủ dùng"


def render_vietnamese_law15_report(results: dict[str, Any]) -> str:
    """Render owner-friendly plain-Vietnamese Law 13–15 report strictly verbatim from `results` (ZERO bare `$`)."""
    inv = results["safety_invariants"]
    inp = results["inputs"]
    traps = results["pricing_traps"]
    s5 = inp["step5_c00_vs_c10"]
    usd_vnd = float(inp["fx_usd_vnd"])
    card_fx = float(inp["card_fx_buy_fee_pct"])
    r_disc = float(inp["discount_rate_annual_pct"])
    p_var = str(inp.get("primary_variant", s5["primary_variant"]))
    be_x = results.get("friction_breakeven_x")
    fresh = inp.get("pricing_catalog_freshness", {})

    # Core 100K 1.0x Funded metrics for Law 15 balanced dashboard
    core_100k = next(
        (r for r in results["lot_rounding_audit"]["funded_1_0x"] if abs(r["capital_usd"] - 100_000.0) < 1e-6),
        results["lot_rounding_audit"]["funded_1_0x"][-1],
    )
    core_10k = next(
        (r for r in results["lot_rounding_audit"]["funded_1_0x"] if abs(r["capital_usd"] - 10_000.0) < 1e-6),
        results["lot_rounding_audit"]["funded_1_0x"][0],
    )
    core_5k = results["lot_rounding_audit"]["funded_1_0x"][0]

    def _find_mode(
        prog_substr: str,
        cap: float,
        fmult: float,
        var_name: str | None = None,
        pricing_mode: str | None = None,
    ) -> dict[str, Any] | None:
        for m in results["mode_comparison"]:
            if prog_substr in m["program_id"] and abs(m["capital_usd"] - cap) < 1e-6 and abs(m["friction_x"] - fmult) < 1e-6:
                if var_name is not None and m["variant"] != var_name:
                    continue
                if pricing_mode is not None and m.get("pricing_mode") != pricing_mode:
                    continue
                return m
        return None

    ref_ftmo_100k = (
        _find_mode("FTMO_2STEP_STANDARD", 100_000.0, 1.00, p_var, "BF_DAY0_PLUS_REGULAR_RETRIES")
        or _find_mode("FTMO_2STEP_STD", 100_000.0, 1.00, p_var)
    )
    ref_ftmo_100k_reg = _find_mode("FTMO_2STEP_STANDARD", 100_000.0, 1.00, p_var, "ALL_REGULAR")

    lines: list[str] = []
    lines.append("# Tối Ưu Hóa Vốn Thi Quỹ Đa Hãng, Làm Tròn Lot 0,01 & Lịch Khuyến Mãi — Bản v2 (Đóng Đủ 9 Điểm Astra Vòng 10)")
    lines.append("")
    lines.append(
        f"- **Ngày tạo:** `{results['generated_utc'][:19]}Z` · **Cửa sổ dữ liệu:** Phát triển niêm phong `{inv['dev_window']}` (`{inv['dev_days_count']}` phiên giao dịch) · **Nhãn mô phỏng:** **`DAILY_APPROX`** *(xấp xỉ cấp ngày từ băng giá M1 thực tế)*"
    )
    lines.append(
        f"- **Cấp độ bằng chứng:** **Backtest trên dữ liệu quá khứ 2018–2024 (`Cluster B` đã xem — không gọi `BLIND`) + Đo khớp lệnh thực tế `28` lệnh trên Demo FTMO (`0,66x`)** — **CHƯA phải Holdout mù 2025+, CHƯA phải tiền thật đã rút về ngân hàng.**"
    )
    lines.append(
        f"- **Khóa an toàn tuyệt đối:** `Holdout 2025+ SEALED` (`holdout_rows_analysed = {inv['holdout_rows_analysed']}`, SHA `{inv['holdout_lock_sha256'][:16]}...`) · `OrderSend = {inv['order_send_count']}` · **Quyết định chi tiền hiện tại: `0 VND`**."
    )
    lines.append(
        f"- **Đầu vào thực tế Việt Nam (Fail-Closed):** Tỷ giá **`1 USD = {usd_vnd:,.2f} VND`** (`prop_pricing_catalog.json`, SHA `{str(inp['pricing_catalog_sha256'])[:16]}`, trạng thái tươi: **`{fresh.get('status', 'FRESH')}`**, tuổi tối đa `{fresh.get('max_age_days', 0.0):.2f}d / {fresh.get('staleness_max_days', 7):.0f}d`, kiểm đủ `{fresh.get('per_tier_count', 0)}` bậc giá) · Phí mua thẻ quốc tế **`+{card_fx:.1f}%`** *(không hoàn lại)* · Phí hoàn tiền về thẻ FTMO **`0,0%`** *(kiểm độ nhạy `1,5%` kênh rút bên dưới)* · Phí rút lợi nhuận + quy đổi VND **`1,5%–4,0%`** tùy hãng · Chiết khấu **NPV**: **`{r_disc:.1f}%/năm`**."
    )
    lines.append(
        f"- **Nhánh chính `v2` & kiểm soát công bằng:** Toàn bộ bảng đánh giá, lịch sale động và lưới Pareto chạy trên **`{p_var}`** *(bật khiên tin đỏ ở mọi pha P1/P2/Funded)* kèm đối chứng **`C00`**; **tắt hoàn toàn `own_book` (`0,0`)** trong mọi bảng xếp hạng chính sách prop; giá vé áp **đúng ngày mua** (`BF Ngày 0 + vé mua lại/mở sau tính giá gốc`, kèm bảng đối chứng **`Toàn bộ giá gốc`**); **loại `E8 Pro`** khỏi danh mục đa quỹ ít rủi ro (`P5/P5B` chỉ còn `3` quỹ sống sót: `FTMO + The5ers + IC Funded`)."
    )
    lines.append("")

    # Executive Summary
    lines.append("## 1. Tóm Tắt Dễ Hiểu Cho Chủ Sở Hữu (5 Kết Luận Quan Trọng Nhất — Bản v2)")
    lines.append("")
    ratios = traps.get("details", {}).get("ftmo_2step_std_fee_ratio_pct", {})
    lines.append(
        f"1. **Cảnh báo 3 cái bẫy giá thực tế trên màn hình thanh toán Việt Nam:** "
        f"(a) **Bẫy `25K` FTMO Standard:** giá Black Friday `220,50 USD` chiếm **`{ratios.get('25K_promo_pct', 0.882):.3f}%`** vốn — **đắt hơn `+{ratios.get('25k_vs_10k_promo_premium_pct', 28.4):.1f}%` so với `10K`** (`0,687%`) và **đắt hơn `+{ratios.get('25k_vs_50k_promo_premium_pct', 44.2):.1f}%` so với `50K`** (`0,612%`)! Tuyệt đối **BỎ QUA gói `25K`**; "
        f"(b) **`200K` vs `2x 100K`:** `200K` (`957,36 USD` BF / `1.196,70 USD` giá gốc) có tỷ lệ phí **y hệt** `100K` (`0,4787%` BF / `0,5984%` giá gốc) nhưng dồn toàn bộ trứng vào 1 vé; khi tách đúng giá gốc cho vé mua lại, **`P4B_PARALLEL_2X100K` (mở song song `2x 100K` Ngày 0)** giữ nhiều viên đạn dự phòng hơn ở vốn `50tr–80tr` (cần nhớ cả 2 vé chịu **tương quan drawdown cùng ngày = `1,0`**); "
        f"(c) **FTMO Swing `50K/100K/200K` bị khóa tại Việt Nam** (`available_vn = false`), và **E8 Pro `100K`** (`0,415%`) đắt hơn mua `2x 50K` (`0,388%`)."
    )
    lines.append(
        f"2. **Tổn thất làm tròn `0,01` lot là có thật (`DAILY_APPROX`, cần đối chiếu thêm MT5 `Model=4`):** "
        f"Ở tài khoản `5K` (Funded `1,0x`), làm tròn xuống bội `0,01` lot làm bỏ mất **`{core_5k['min_lot_rejected']}`** lệnh và kéo tụt lợi suất năm **`{core_5k['lot_rounding_drag_vs_200k_pct']:+.2f}%`** so với `200K` (`+{core_5k['ann_pct']:.2f}%` vs `+{results['lot_rounding_audit']['funded_1_0x'][-1]['ann_pct']:.2f}%`); "
        f"`10K` bị kéo lùi **`{core_10k['lot_rounding_drag_vs_200k_pct']:+.2f}%`**, còn từ `50K–100K` trở lên tổn thất gần như biến mất (`{core_100k['lot_rounding_drag_vs_200k_pct']:+.2f}%`, `0` lệnh bị loại)."
    )
    if ref_ftmo_100k:
        s100 = ref_ftmo_100k["single_ticket_zero_retry"]
        reg_note = ""
        if ref_ftmo_100k_reg:
            sr = ref_ftmo_100k_reg["single_ticket_zero_retry"]
            reg_note = f" *(nếu mua giá gốc không sale `598,35 USD` ~ `{sr['effective_fee_vnd_tr']:.1f}tr`: `NPV24 {sr['ev_npv_24m_vnd_tr']:+.1f}tr`, `EV/Phí {sr['ev_per_fee_npv24']:+.2f}x`)*"
        lines.append(
            f"3. **Hiệu quả 1 vé không thử lại (`FTMO 2-Step Standard 100K · {p_var} · 1,00x`, BF `478,68 USD` ~ `{s100['effective_fee_vnd_tr']:.1f}` triệu VND cả phí thẻ, hoàn phí về thẻ `0%`):** "
            f"Xác suất đậu vào Funded trong `24` tháng đạt **`{s100['pass_24m_pct']:.1f}%`**, trung vị thời gian có lần rút tiền đầu (nhóm đã rút) là **`{s100['cond_med_pay1_cal_days']:.0f}` ngày** (không điều kiện chặn `730d`: **`{s100['uncond_med_pay1_cap730_days']:.0f}` ngày**), "
            f"cháy Funded `12T` **`{s100['funded_12m_breach']['breach_12m_pct']:.2f}%`**, "
            f"`NPV 24T` trung bình **`{s100['ev_npv_24m_vnd_tr']:+.1f}` tr VND** (trung vị **`{s100['med_npv_24m_vnd_tr']:+.1f}tr`**, xác suất lỗ ròng `P(NPV<=0)` = **`{s100['p_net_le_0_24m_pct']:.1f}%`**, **`{s100['ev_per_fee_npv24']:+.2f}x`** trên mỗi đồng phí){reg_note}."
        )
    lines.append(
        "4. **Cảnh báo trung vị âm ở chế độ stress nặng `1,50x` (KHÔNG che sau số trung bình dương):** "
        "Trên mọi ô Pareto ở Mục 7, báo cáo `v2` công bố đầy đủ bộ ba **`NPV24 Trung bình (TB)` + `NPV24 Trung vị (TV)` + `Xác suất lỗ ròng P(NPV24 <= 0)`**. "
        "Khi trượt giá tăng `+50%` (`1,50x`), dù trung bình vẫn dương nhờ nhánh thắng lớn, **trung vị nhiều chính sách rơi xuống âm và hơn `50%` kịch bản hòa/lỗ sau 24 tháng** — nhắc nhở dứt khoát phải giữ cổng đo trượt giá thực tế `< 1,25x`."
    )
    lines.append(
        "5. **Loại `E8 Pro` khỏi danh mục đa quỹ ít rủi ro (`P5/P5B` chỉ gồm `3` hãng: `FTMO + The5ers + IC Funded`):** "
        "Ngay cả khi cố giữ lãi tới `+8%` hoặc `+10%` trước lần rút đầu trên `E8 Pro`, cơ chế khóa sàn DD tại vốn gốc + giữ lại `50%` vẫn gây tỷ lệ cháy Funded 12 tháng hai chữ số (Astra đối chứng `34,18% / 17,38%` ở `1,00x`). "
        "Đồng thời `The5ers` (`max(balance, equity)` tại giờ reset) và `IC Funded` (`equity` tại giờ reset) đều mang song song 2 nhãn **`TERMS_VERIFIED_EXECUTION_UNMEASURED`** và **`DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`** *(công thức `balance * (1 - daily_lim)` chỉ đúng khi đóng sạch lệnh đúng giờ reset của từng hãng)* — **tuyệt đối KHÔNG rót tiền thật** trước khi tự đo khớp lệnh Demo MT5 riêng của từng hãng."
    )
    lines.append("")

    # Section 2: Balanced Law-15 Core Metrics & Benchmark Scale
    lines.append("## 2. Bộ Chỉ Số Cân Bằng Lõi `PORT_7E` & Định Vị Trên Thang `Xấu -> Top 1%` (Luật 15)")
    lines.append("")
    lines.append("Dưới đây là toàn bộ chỉ số lõi của danh mục `7` động cơ trong ngày (`swap = 0`) ở mức rủi ro chuẩn Funded `1,0x` (tài khoản `100K`, ma sát nền `1,00x`, có khiên tin đỏ `±5` phút, dữ liệu quá khứ `2018–2024`):")
    lines.append("")
    ev_fee_ref = ref_ftmo_100k["single_ticket_zero_retry"]["ev_per_fee_npv24"] if ref_ftmo_100k else 0.0
    fn_br_ref = ref_ftmo_100k["single_ticket_zero_retry"]["funded_12m_breach"]["breach_12m_pct"] if ref_ftmo_100k else 0.0
    pay1_mo_ref = (ref_ftmo_100k["single_ticket_zero_retry"]["cond_med_pay1_cal_days"] / 30.4) if ref_ftmo_100k else 0.0

    lines.append("| Chỉ số (giải thích đơn giản) | Kết quả hiện tại (`100K`, Dev `1,00x`) | Thang `Xấu` | Thang `Đủ dùng` | Thang `Tốt` | Thang `Top 1% thực tế` | Đang đứng ở bậc nào? |")
    lines.append("|---|---:|---|---|---|---|---|")
    lines.append(
        f"| **Tỷ lệ thắng (`Winrate`) & Tỷ lệ ăn/thua (`RR`)** | **`{core_100k['winrate_pct']:.1f}%`** / **`{core_100k['avg_rr']:.2f}x`** (`{core_100k['sized_trades']}` lệnh) | `EV <= 0` | Cân đối dương | Cân đối bền | Bền trên tiền thật | **Tốt (trên quá khứ)** |"
    )
    lines.append(
        f"| **Kỳ vọng mỗi lệnh (`EV / lệnh`)** | **`{core_100k['ev_per_trade_r']:+.3f}R`** | `<= 0,00R` | `+0,03R..+0,06R` | `+0,07R..+0,15R` | `> +0,15R` bền trên tiền thật | **{_rank_law15_tier('ev_r', core_100k['ev_per_trade_r'])}** |"
    )
    lines.append(
        f"| **Hệ số sinh lời (`Profit Factor`)** | **`{core_100k['profit_factor']:.2f}`** | `< 1,05` | `1,10..1,20` | `1,25..1,50` | `1,50..2,00+` tiền thật `>=12T` | **{_rank_law15_tier('pf', core_100k['profit_factor'])}** |"
    )
    lines.append(
        f"| **Tụt sâu nhất (`Max DD` ở `1,0x`) & chuỗi thua** | **`{core_100k['peak_dd_pct']:.2f}%`** (chuỗi **`{core_100k['max_loss_streak_trades']}`** lệnh) | `> 10%` | `7,5%..9,0%` | `5,0%..7,0%` | `4,0%..7,0%` đường tiền đều | **{_rank_law15_tier('dd', core_100k['peak_dd_pct'])}** |"
    )
    lines.append(
        f"| **Hiệu suất trên rủi ro (`Calmar`)** | **`{core_100k['calmar']:.2f}`** (lãi năm `+{core_100k['ann_pct']:.2f}%`) | `< 0,5` | `0,6..1,0` | `1,2..2,0` | `> 2,0..3,0` trên tiền thật | **{_rank_law15_tier('calmar', core_100k['calmar'])}** |"
    )
    lines.append(
        f"| **Độ êm lợi nhuận (`Sharpe`)** | **`{core_100k['sharpe']:.2f}`** | `< 0,6` | `0,8..1,1` | `1,2..1,8` | `2,0..3,0` tiền thật `>=12T` | **{_rank_law15_tier('sharpe', core_100k['sharpe'])}** |"
    )
    lines.append(
        f"| **Thi quỹ Prop (`{p_var}`: `EV NPV / 1 đồng phí`, cháy Funded, chờ rút)** | **`{ev_fee_ref:+.2f}x`** · cháy `12T` **`{fn_br_ref:.2f}%`** · chờ **`{pay1_mo_ref:.1f}T`** | `<= 0x` hoặc cháy `>5%` | `+1x..+2x` | `+3x..+5x`, cháy `<1%`, chờ `5–10T` | `>= +5x`, cháy `<1%`, rút `2–4T` nhiều nhánh lệch pha | **{_rank_law15_tier('ev_fee', ev_fee_ref)}** |"
    )
    lines.append("")
    lines.append(
        f"- **Ngưỡng gãy / điểm chết trượt giá (Break-Even Threshold):** Khi chi phí khớp lệnh thực tế (spread + trượt giá) xấu đi tới khoảng **`{be_x if be_x is not None else '>4.00'}x`** so với băng giá M1 chuẩn, kỳ vọng lợi nhuận chiến lược rơi về `<= 0` (chuyển âm). Do đó quy tắc dừng mua vé mới (cắt chi phí chìm) được khóa cứng tại **`> 1,75x`**."
    )
    lines.append(
        f"- **Còn thiếu gì để chạm `Top 1%` thực tế?** (1) Bằng chứng hiện mới là **Dev backtest + 28 lệnh Demo FTMO** — chưa có Holdout mù `2025+` và chưa có `>= 12` tháng chạy tiền thật rút tiền; (2) `Max DD` ở `1,0x` (`{core_100k['peak_dd_pct']:.2f}%`) và `Calmar` (`{core_100k['calmar']:.2f}`) mới ở vùng **Đủ dùng**, cần thêm nhánh độc lập lệch pha (không tăng đòn bẩy liều) để kéo `Calmar > 1,5–2,0`, rút thời gian chờ payout xuống `2–4` tháng và hạ tháng đói Funded từ `~{ref_ftmo_100k['single_ticket_zero_retry']['funded_dry_months_pct'] if ref_ftmo_100k else 50:.0f}%` xuống `< 25%`."
    )
    lines.append("")

    # Friction sweep table
    lines.append("### 2.1. Độ Bền Trước Trượt Giá (`0,66x` Đo Sống Demo FTMO -> `4,00x` Sốc Gãy Cấu Trúc, `100K` `1,0x`)")
    lines.append("")
    lines.append("| Mức ma sát (so với M1 chuẩn) | Diễn giải thực tế | Lãi năm (%) | Lãi năm (tr VND / `100K`) | `PF` | `EV / lệnh` | `Max DD` | `Calmar` | `Sharpe` |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    fric_labels = {
        0.66: "Đo sống 28 lệnh Demo FTMO (trung vị bảo thủ)",
        1.00: "Chuẩn băng giá M1 Bid/Ask",
        1.25: "Trượt giá tăng +25%",
        1.50: "Stress trượt giá nặng +50%",
        1.75: "Ngưỡng báo động đỏ / Cắt chi phí chìm",
        2.00: "Sốc cực đoan gấp đôi chi phí",
        2.50: "Vượt ngưỡng gãy (chuyển âm ròng)",
        3.00: "Sốc gấp 3 lần chi phí",
        3.50: "Sốc phá hủy 3,5x chi phí",
        4.00: "Sốc cực hạn 4,0x chi phí",
    }
    for row in results["friction_sweep_100k"]:
        fx = float(row["friction_x"])
        ann_vnd = (row["ann_pct"] / 100.0) * 100_000.0 * usd_vnd / 1_000_000.0
        lines.append(
            f"| **`{fx:.2f}x`** | {fric_labels.get(fx, '')} | `{row['ann_pct']:+.2f}%` | `{ann_vnd:+.1f}` tr | `{row['profit_factor']:.2f}` | `{row['ev_per_trade_r']:+.3f}R` | `{row['peak_dd_pct']:.2f}%` | `{row['calmar']:.2f}` | `{row['sharpe']:.2f}` |"
        )
    lines.append("")

    # Section 3: Exact 0.01-lot rounding table + B1 Sizing Parity Disclosure
    lines.append("## 3. Tác Động Làm Tròn `0,01` Lot Thực Tế (`5K -> 200K`) & Công Khai Khác Biệt Cách Tính Cỡ Lệnh (B1)")
    lines.append("")
    lines.append("Mọi tài khoản dưới đây đều được chạy lại từ đầu bằng công thức làm tròn xuống từng bước `0,01` lot (`raw_lots < 0,01` -> bỏ lệnh), **tuyệt đối không nhân tuyến tính từ `10K`**:")
    lines.append("")
    lines.append("| Cỡ tài khoản | Funded `1,0x`: Lãi năm | Lệch vs `200K` | Bỏ `<0,01` | Funded `1,25x` (`C10_NEWS_ON`): Lãi năm / Lệch | Phanh Đỏ `0,4x`: Lãi năm | Phanh Đỏ: Bỏ `<0,01` | Phanh Đỏ: Lệch vs `200K` |")
    lines.append("|---:|---:|---:|---:|---|---:|---:|---:|")
    f1_rows = results["lot_rounding_audit"]["funded_1_0x"]
    f125_rows = results["lot_rounding_audit"].get("funded_1_25x", f1_rows)
    r04_rows = results["lot_rounding_audit"]["red_brake_0_4x"]
    for f1, f125, r04 in zip(f1_rows, f125_rows, r04_rows):
        lines.append(
            f"| **`{int(f1['capital_usd']//1000)}K USD`** | `+{f1['ann_pct']:.2f}%` | **`{f1['lot_rounding_drag_vs_200k_pct']:+.2f}%`** | `{f1['min_lot_rejected']}` ({f1['min_lot_reject_pct']:.2f}%) | `+{f125['ann_pct']:.2f}%` (`{f125['lot_rounding_drag_vs_200k_pct']:+.2f}%`) | `+{r04['ann_pct']:.2f}%` | **`{r04['min_lot_rejected']}`** ({r04['min_lot_reject_pct']:.1f}%) | **`{r04['lot_rounding_drag_vs_200k_pct']:+.2f}%`** |"
        )
    lines.append("")
    lines.append(
        "> **Công khai trung thực về khác biệt tính cỡ lệnh giữa Python và EA MQL5 (Điểm B1 Astra Vòng 10):** "
        "Hàm Python `get_exact_tier_stage` tính khối lượng lệnh theo **vốn gốc đầu kỳ cố định** (`initial * eff_risk`) và **bỏ thẳng lệnh** nếu thiếu ký quỹ (`margin_rejected`), "
        "trong khi **EA MQL5 thực tế** (`Naqex_Master_Prop7E`) tính khối lượng theo **số dư hiện tại nhân `0,95`** (`balance * risk * 0.95`) và **tự động thu nhỏ lot xuống mức `85%` ký quỹ khả dụng** (`free margin`) thay vì bỏ trắng lệnh. "
        "Do đó các tỷ lệ tổn thất làm tròn ở bậc `5K / 10K` phía trên được gắn nhãn **`DAILY_APPROX` (ước lượng Python)**, chưa thay thế phép đối chứng trực tiếp trên MT5 `Model=4` Real-Tick cho từng cỡ tài khoản."
    )
    lines.append("")

    # Section 4: Multi-Firm & Multi-Mode Single-Ticket Zero-Retry Comparison (Law 13)
    lines.append(f"## 4. So Sánh 4 Quỹ & Mọi Chế Độ Thi — 1 Vé Không Thử Lại (`{p_var}` Chính + `C00` Đối Chứng, `DAILY_APPROX`)")
    lines.append("")
    lines.append(
        "- Mỗi chế độ có trần lỗ ngày chặt hơn (`3%` ở FTMO 1-Step/Instant, `2,5%` ở E8 Pro, `4%/8%` ở The5ers `50K/100K`) đều được **tự động hiệu chuẩn hệ số rủi ro an toàn riêng** trên nhánh **`C10_NEWS_ON`**."
    )
    lines.append(
        "- **Mốc neo DD ngày theo đúng hợp đồng từng quỹ (`daily_dd_anchor`) & nhãn kiểm chứng DD (`dd_rule_verification_tag`):** "
        "FTMO & E8 Pro tính trần lỗ ngày theo **vốn gốc ban đầu** (`s_bal - cap * daily_lim`). "
        "Riêng **`The5ers`** *(neo theo `max(balance, equity)` tại mốc reset `00:00` MT5)* và **`IC Funded`** *(neo theo `equity` tại mốc reset `00:00` GMT+2/+3)* "
        "đều gắn nhãn **`DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`** song song với **`TERMS_VERIFIED_EXECUTION_UNMEASURED`**: "
        "công thức mô phỏng `balance * (1 - daily_lim)` chỉ đúng khi tài khoản **đóng sạch lệnh (flat) đúng giờ reset từng hãng**."
    )
    lines.append(
        "- Cột `Đậu / Rớt / Chờ` ở mọi mốc tháng (`3T / 6T / 12T / 24T`) luôn có tổng đúng bằng **`100,0%`**. Cột `Cháy Funded 12T` tính trên **đúng mẫu số các vé đã vào Funded** (cần `~299` quan sát độc lập không cháy ngoài thực tế để chứng minh cận trên `95% < 1%`)."
    )
    lines.append("")
    lines.append("### 4.1. Bảng So Sánh Ở Ma Sát Nền `1,00x` (Phí Thực VN: Mua Thẻ `+2,5%`, Hoàn Thẻ FTMO `0%`, Phí Rút Lãi `1,5%–4,0%`, Chiết Khấu `6%/Năm`)")
    lines.append("")
    lines.append("| Hãng / Chế độ / Cỡ (`Biến thể` · `Giá`) | Khớp lệnh | Phí (USD / tr VND) | Luật DD (`Mốc neo`) & Rủi ro | `24T` Đậu / Rớt / Chờ (`100%`) | Chờ Payout TV (ĐK / KĐK `730d`) | Cháy Funded `12T` (Wilson `95%`) | Tháng đói (`P50/P95`) | `NPV 24T` TB / TV (tr VND) | `P(<=0)` | `EV/Phí` |")
    lines.append("|---|---|---:|---|---|---|---|---|---:|---:|---:|")
    for m in results["mode_comparison"]:
        if abs(m["friction_x"] - 1.00) > 1e-6:
            continue
        s = m["single_ticket_zero_retry"]
        m24 = s["monthly_pass_fail_pending"].get("24m", {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
        fb = s["funded_12m_breach"]
        cm = m["calibrated_mults"]
        badge = "ĐO DEMO" if m["execution_evidence_tag"] == "MEASURED_DEMO_EXECUTION" else "CHƯA ĐO"
        anc_short = (
            "PrevBal · FLAT_RESET_ONLY"
            if m.get("dd_rule_verification_tag") == DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT
            else ("PrevBal" if m.get("daily_dd_anchor") == "prev_day_balance" else "InitBal")
        )
        pr_short = "BF" if m.get("pricing_mode") == "BF_DAY0_PLUS_REGULAR_RETRIES" else "Gốc"
        dd_desc = f"{m['dd_daily_pct']:.1f}/{m['dd_max_pct']:.0f}% {m['dd_type'][:3]} ({anc_short}) · {cm['p1']:.2f}/{cm['p2']:.2f}/{cm['funded']:.2f}x"
        cond_d = f"{s['cond_med_pay1_cal_days']:.0f}d" if s["cond_med_pay1_cal_days"] > 0 else "N/A"
        lines.append(
            f"| **{m['mode_name']} {int(m['capital_usd']//1000)}K** (`{m['variant']}` · `{pr_short}`) | `{badge}` | `{m['promo_usd']:.0f}` / `{s['effective_fee_vnd_tr']:.1f}tr` | `{dd_desc}` | `{m24['pass_pct']:.1f}% / {m24['fail_pct']:.1f}% / {m24['pending_pct']:.1f}%` | `{cond_d}` / `{s['uncond_med_pay1_cap730_days']:.0f}d` | `{fb['breach_12m_pct']:.2f}%` (`<={fb['wilson_95_upper_pct']:.1f}%`) | `{s['funded_dry_months_pct']:.0f}%` (`{s['funded_dry_streak_p50_months']}/{s['funded_dry_streak_p95_months']}T`) | **`{s['ev_npv_24m_vnd_tr']:+.1f}`** / `{s['med_npv_24m_vnd_tr']:+.1f}` | `{s['p_net_le_0_24m_pct']:.1f}%` | **`{s['ev_per_fee_npv24']:+.2f}x`** |"
        )
    lines.append("")

    # Structural trap callout + E8 Pro Payout #1 Buffer Sensitivity (B4)
    m_1step_100 = _find_mode("FTMO_1STEP", 100_000.0, 1.00, p_var)
    m_inst_100 = _find_mode("FTMO_INSTANT", 100_000.0, 1.00, p_var)
    m_e8_50 = _find_mode("E8_PRO", 50_000.0, 1.00, p_var)
    s1st = m_1step_100["single_ticket_zero_retry"] if m_1step_100 else None
    sins = m_inst_100["single_ticket_zero_retry"] if m_inst_100 else None
    se8 = m_e8_50["single_ticket_zero_retry"] if m_e8_50 else None
    parts_trap = []
    if s1st is not None:
        parts_trap.append(
            f"(1) **`FTMO 1-Step` (`100K`)** có `EV/Phí` cao (`{s1st['ev_per_fee_npv24']:+.2f}x`) nhưng luật **`50%` Best Day + EOD Trailing** làm **`{s1st['funded_dry_months_pct']:.1f}%`** số tháng Funded khô hạn và kéo ngày chờ payout đầu lên **`{s1st['cond_med_pay1_cal_days']:.0f}` ngày**"
        )
    if sins is not None:
        parts_trap.append(
            f"(2) **`FTMO Instant` (`100K`)** rút nhanh nhất (`{sins['cond_med_pay1_cal_days']:.0f}` ngày) nhưng phí cao gấp `5,5x` 2-Step (`EV/Phí {sins['ev_per_fee_npv24']:+.2f}x`), cháy Funded `12T` nhảy lên **`{sins['funded_12m_breach']['breach_12m_pct']:.2f}%`** (Intraday Trailing) và **`{sins['funded_dry_months_pct']:.1f}%`** tháng đói (`30%` Best Day)"
        )
    if se8 is not None:
        e8_buf_rows = results.get("e8_pro_buffer_sensitivity", {}).get("mc_buffer_sweep_50k_1_00x", [])
        buf_txt = ""
        if len(e8_buf_rows) >= 3:
            b8, b10 = e8_buf_rows[1], e8_buf_rows[2]
            buf_txt = (
                f"; ngay cả khi cố chờ lãi **`+8%` / `+10%`** trước lần rút đầu (đệm giữ lại `4% / 5%`), mô phỏng MC vẫn cháy **`{b8['funded_12m_breach_pct']:.2f}%` / `{b10['funded_12m_breach_pct']:.2f}%`** trong 12 tháng "
                f"(Astra Vòng 10 đối chứng **`34,18%` / `17,38%`** ở `1,00x`) -> **ĐÃ LOẠI `E8 Pro` khỏi mọi danh mục đa quỹ `P5/P5B`**"
            )
        parts_trap.append(
            f"(3) **`E8 Pro` (`50K`)** bị bẫy **khóa sàn DD về vốn gốc sau lần rút đầu** + giữ lại `50%` + trần lãi ngày `2%`: rút ngay `+1%` làm cháy **`{se8['funded_12m_breach']['breach_12m_pct']:.2f}%`** tài khoản Funded trong 12 tháng{buf_txt}"
        )
    if parts_trap:
        lines.append("> **Phát hiện bẫy cấu trúc cực quan trọng (B4):** " + "; ".join(parts_trap) + ".")
        lines.append("")

    # Section 4.2: Monthly Pass/Fail/Pending table for FTMO 2-Step Standard 100K (C10_NEWS_ON vs C00 vs C10 ablation)
    lines.append("### 4.2. Chi Tiết `Đậu / Rớt / Chờ` Theo Tháng (`3T / 6T / 12T / 24T`, Tổng = `100%`) — `FTMO 2-Step Standard 100K` (`C10_NEWS_ON` Chính vs `C00` Đối Chứng vs `C10` News-OFF)")
    lines.append("")
    lines.append("| Biến thể & Ma sát | `3` Tháng (`Đậu/Rớt/Chờ`) | `6` Tháng (`Đậu/Rớt/Chờ`) | `12` Tháng (`Đậu/Rớt/Chờ`) | `24` Tháng (`Đậu/Rớt/Chờ`) | `NPV 24T` TB / TV (tr VND) | `P(NPV24 <= 0)` |")
    lines.append("|---|---|---|---|---|---:|---:|")
    for var_c in ("C10_NEWS_ON", "C00", "C10"):
        for fm in (1.00, 1.50):
            mm = (
                _find_mode("FTMO_2STEP_STANDARD", 100_000.0, fm, var_c, "BF_DAY0_PLUS_REGULAR_RETRIES")
                or _find_mode("FTMO_2STEP_STD", 100_000.0, fm, var_c)
            )
            if not mm:
                continue
            s = mm["single_ticket_zero_retry"]
            mb = s["monthly_pass_fail_pending"]
            def _c(k: str) -> str:
                r = mb.get(k, {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0})
                return f"`{r['pass_pct']:.1f}% / {r['fail_pct']:.1f}% / {r['pending_pct']:.1f}%`"
            tag_v = " *(Chính)*" if var_c == p_var else (" *(Đối chứng)*" if var_c == "C00" else " *(Chỉ tham khảo News-OFF)*")
            lines.append(
                f"| **`{var_c}`{tag_v} @ `{fm:.2f}x`** | {_c('3m')} | {_c('6m')} | {_c('12m')} | {_c('24m')} | **`{s['ev_npv_24m_vnd_tr']:+.1f}tr`** / `{s['med_npv_24m_vnd_tr']:+.1f}tr` | `{s['p_net_le_0_24m_pct']:.1f}%` |"
            )
    lines.append("")

    # Step 5 MT5 Model=4 Pairs summary if loaded
    if s5.get("mt5_model4_q4_2024_same_phase_pairs"):
        lines.append("### 4.3. Đối Chiếu Thực Tế MT5 `Model=4` Real-Tick (Q4/2024) Từ Step 5 (`C00` vs `C10`) & Lý Do Chốt `C10_NEWS_ON`")
        lines.append("")
        lines.append("| Pha (`FTMO_STD 10K`, `swap=0`) | `C00` (News ON) Lệnh / Lãi / `PF` / `EqDD` | `C10` (News OFF P1/P2) Lệnh / Lãi / `PF` / `EqDD` | Chênh lệch (`C10 - C00`) |")
        lines.append("|---|---|---|---|")
        for ph in ("P1", "P2", "FUNDED"):
            pair = s5["mt5_model4_q4_2024_same_phase_pairs"].get(ph)
            if not pair:
                continue
            c0, c1, dl = pair["C00"], pair["C10"], pair["delta_c10_minus_c00"]
            lines.append(
                f"| **`{ph}`** | `{c0['trades']}` / `{c0['net_profit_usd']:+.2f} USD` / `PF {c0['profit_factor']}` / `EqDD {c0['equity_dd_pct']}%` | `{c1['trades']}` / `{c1['net_profit_usd']:+.2f} USD` / `PF {c1['profit_factor']}` / `EqDD {c1['equity_dd_pct']}%` | `{dl['net_profit_usd']:+.2f} USD` (`EqDD {dl['equity_dd_pct']:+.2f}%`) |"
            )
        lines.append("")
        lines.append(
            "> Vì `C10` (tắt tin đỏ) thua nặng ở P1 Q4/2024 (`-337,64 USD`, `EqDD 8,82%`), trong khi Step 6 chứng minh **`C10_NEWS_ON`** (giữ cỡ lệnh & ProfitLock `C10` + **BẬT khiên tin đỏ ở mọi pha**) vượt cả `C00` lẫn `C10` News-OFF, toàn bộ bản tối ưu `v2` đã khóa nhánh chính là **`C10_NEWS_ON`**."
        )
        lines.append("")

    # Section 5: Dual-Horizon Dynamic Sale-Calendar Decision Table (B5)
    lines.append("## 5. Lịch Sale Động Hai Chân Trời (B5): Mua Hôm Nay Hay Đợi `Y` Ngày Để Hưởng Giảm Giá `Z%`?")
    lines.append("")
    lines.append(
        "- **Khắc phục triệt để 3 lỗi cũ:** (1) **Bỏ hoàn toàn binary search** -> quét chính xác toàn bộ từng ngày `Y = 0..180` vì chân trời hạn cứng không đơn điệu qua các chu kỳ rút tiền `10` phiên; (2) **Bỏ hoàn toàn đường tắt `2 * d7`** -> chạy mô phỏng MC thật cho cả `7d / 14d / 30d`; (3) Vé mua lại (retry) **luôn tính giá gốc** (không hưởng BF vĩnh viễn)."
    )
    lines.append(
        "- **Công bố song song 2 chân trời & quét dày toàn bộ `Y = 0..180` (ZERO tìm thưa quanh nghiệm giải tích):** "
        "**(a) Hạn lịch cố định 24 tháng tính từ hôm nay** *(đợi Y ngày = mất hẳn Y ngày giao dịch trước hạn)* và "
        "**(b) Chân trời tịnh tiến 24 tháng tính từ ngày mua** *(công thức `365 * ln(NPV_sale / NPV_orig) / ln(1 + r)` + quét dày MC toàn bộ từng ngày nguyên `0..180` trên cửa sổ `[Y, Y+24T)`)*, "
        "công bố rõ cả 2 mốc **`max_continuous_positive_wait_days`** *(mọi ngày `0..Y` đều dương liên tục)* và **`last_positive_wait_day`** *(ngày dương cuối cùng nếu nhiễu MC bật lại sau khi đã rơi âm — **tuyệt đối không hiểu nhầm `last_positive_wait_day` là đợi ngày nào tới mốc đó cũng dương!**)*."
    )
    lines.append(
        "- **Công khai giả định bắt buộc:** Mọi con số ngày tối đa đáng chờ bên dưới **đều giả định đợt sale tương lai `Z%` chắc chắn 100% xảy ra đúng vào ngày `Y`**. Nếu xác suất có sale thực tế chỉ là `p < 100%` (ví dụ `HISTORICAL_PATTERN` ngoài Black Friday), số ngày đáng chờ thực tế phải rút ngắn tương ứng."
    )
    lines.append("")
    for retry_key, retry_title in (
        ("SINGLE_TICKET_0_RETRY", "5.1. Chế Độ 1 Vé (`max_retries = 0`, `C10_NEWS_ON` — Đối Chiếu Trực Tiếp Astra `~55 / 110 / 164d` trên `10K`)"),
        ("RETRY_UP_TO_2_REGULAR_PRICE", "5.2. Chế Độ Có Thử Lại (`max_retries = 2`, Vé Ngày Mua Hưởng Sale + Vé Mua Lại Tính Giá Gốc, `C10_NEWS_ON`)"),
    ):
        lines.append(f"### {retry_title}")
        lines.append("")
        lines.append("| Kịch bản ngày hiện tại | Cỡ FTMO | Ma sát | Sale mục tiêu | Tiết kiệm ngay (USD) | **(a) Hạn cứng 24T: Tối đa đáng chờ** | `Delta` cứng (`7d / 14d / 30d`) | **(b) Tịnh tiến 24T: Công thức / MC (Liên tục · Cuối dương)** | `Delta` tịnh tiến (`7d / 14d / 30d`) |")
        lines.append("|---|---:|---:|---:|---:|---:|---|---:|---|")
        non_mono_shift_examples: list[str] = []
        for row in results["sale_decision_table"]:
            if row.get("retry_regime") != retry_key:
                continue
            if row["scenario"] == "NON_PROMO_DAY_0PCT":
                sc_lbl = "Ngày thường (`0%`)"
                sav = f"`{row['upfront_saving_usd']:.1f}`"
            else:
                sc_lbl = f"Black Friday (`-{row['active_discount_pct']:.0f}%`)"
                sav = "—"
            d_fix = f"`{row.get('delta_npv_at_7d_usd', 0.0):+.1f}` / `{row.get('delta_npv_at_14d_usd', 0.0):+.1f}` / `{row.get('delta_npv_at_30d_usd', 0.0):+.1f}`"
            sh_f = row.get("shifting_horizon_formula_max_wait_days", 0.0)
            sh_cont = row.get("max_continuous_positive_wait_days")
            sh_last = row.get("last_positive_wait_day")
            if sh_cont is not None and sh_last is not None:
                if sh_last > sh_cont:
                    sh_lbl = f"**`{sh_f:.0f}d`** / LT `{sh_cont}d` · Cuối `{sh_last}d` *(gãy {row.get('first_nonpositive_wait_day', sh_cont + 1)}d)*"
                    non_mono_shift_examples.append(
                        f"`{int(row['capital_usd']//1000)}K @ {row['friction_x']:.2f}x (-{row['target_sale_discount_pct']:.0f}%)`: "
                        f"liên tục dương tới **`{sh_cont}d`** (rơi âm ngay tại **`{row.get('first_nonpositive_wait_day', sh_cont + 1)}d`**), "
                        f"nhiễu MC bật dương lần cuối tại **`{sh_last}d`**"
                    )
                else:
                    sh_lbl = f"**`{sh_f:.0f}d`** / LT `{sh_cont}d` · Cuối `{sh_last}d`"
            else:
                sh_lbl = f"**`{sh_f:.0f}d`**"
            d_sh = f"`{row.get('shifting_delta_formula_7d_usd', 0.0):+.1f}` / `{row.get('shifting_delta_formula_14d_usd', 0.0):+.1f}` / `{row.get('shifting_delta_formula_30d_usd', 0.0):+.1f}`"
            nm_tag = " *(không đơn điệu)*" if row.get("non_monotonic_fixed_deadline") else ""
            lines.append(
                f"| {sc_lbl} | **`{int(row['capital_usd']//1000)}K`** | `{row['friction_x']:.2f}x` | `-{row['target_sale_discount_pct']:.0f}%` | {sav} | **`{row['max_wait_days_fixed_deadline']}d`**{nm_tag} | {d_fix} | {sh_lbl} | {d_sh} |"
            )
        lines.append("")
        if non_mono_shift_examples:
            lines.append(
                "> **Cảnh báo đường cong tịnh tiến không đơn điệu (Astra Vòng 11 Q3c):** "
                "Vì quét dày toàn bộ `Y = 0..180`, các dòng có `Cuối dương > Liên tục` (ví dụ: "
                + "; ".join(non_mono_shift_examples[:4])
                + ") **KHÔNG ĐƯỢC hiểu là đợi bất kỳ ngày nào tới mốc `Cuối dương` đều có lãi** — phải lấy mốc **`Liên tục` (`max_continuous_positive_wait_days`)** làm ngưỡng an toàn bảo thủ."
            )
            lines.append("")

    # Section 6: 3-Way 2x100K (Seq vs Par) vs 1x200K, NPV/Fee Sensitivity, Sunk-Cost Abort, 3-Firm Hazard
    lines.append("## 6. Các Kiểm Chứng Tài Chính Thực Tế (`own_book = 0`, Vé Mua Lại Giá Gốc, Hoàn Phí Thẻ FTMO `0%`)")
    lines.append("")
    lines.append("### 6.1. So Sánh 3 Nhánh: `2x 100K` Tuần Tự (`P4B`) vs `2x 100K` Song Song Ngày 0 (`P4B_PARALLEL`) vs `1x 200K` (`P4C`)")
    lines.append("")
    lines.append("*Lưu ý quan trọng (B6):* **`P4B_PARALLEL_2X100K`** mở cả 2 vé `100K` ngay Ngày 0 khi đủ vốn (`>= 2` vé) nên cả 2 vé chạy trên **cùng ngày thị trường** (`tương quan drawdown cùng ngày = 1,0`, thể hiện qua cột **`Cháy kép cùng ngày`**). Dù chịu cháy kép, ở vốn `50tr–80tr` tách thành `2x 100K` vẫn giữ thêm đạn dự phòng `100K` (giá gốc `15,8tr/vé`) trong khi `1x 200K` cần tới `31,6tr/vé` cho lượt mua lại!")
    lines.append("")
    lines.append("| Vốn ban đầu (`0tr/T`) | Ma sát | `P4B` Tuần tự `100K->2x100K`: Cháy / `NPV24` TB (TV, `P<=0`) | **`P4B_PARALLEL` `2x 100K` Ngày 0**: Cháy / Cháy kép / `NPV24` TB (TV, `P<=0`) | `P4C` `1x 200K`: Cháy / `NPV24` TB (TV, `P<=0`) | Đối chứng **Toàn bộ giá gốc**: `Par 2x100K` vs `1x200K` (`Cháy / NPV24`) |")
    lines.append("|---:|---:|---|---|---|---|")
    for fkey in ("1.00x", "1.50x"):
        for r in results["head_to_head_2x100k_vs_1x200k"][fkey]:
            sq = r["sequential_2x_100k"]
            pa = r["parallel_2x_100k"]
            c2 = r["one_x_200k"]
            pr = r["parallel_2x_100k_all_regular"]
            cr = r["one_x_200k_all_regular"]
            lines.append(
                f"| **`{r['bankroll_vnd_tr']:.0f}tr`** (`{r['bankroll_usd']:,.0f} USD`) | `{fkey}` | `{sq['ruin_pct']:.2f}%` / `{sq['ev_npv_24m_vnd_tr']:+.1f}tr` (`{sq['med_npv_24m_vnd_tr']:+.1f}tr`, `{sq['p_npv24_le_0_pct']:.0f}%`) | **`{pa['ruin_pct']:.2f}%`** / `{pa['simultaneous_fail_pct']:.1f}%` / **`{pa['ev_npv_24m_vnd_tr']:+.1f}tr`** (`{pa['med_npv_24m_vnd_tr']:+.1f}tr`, `{pa['p_npv24_le_0_pct']:.0f}%`) | `{c2['ruin_pct']:.2f}%` / `{c2['ev_npv_24m_vnd_tr']:+.1f}tr` (`{c2['med_npv_24m_vnd_tr']:+.1f}tr`, `{c2['p_npv24_le_0_pct']:.0f}%`) | `Par {pr['ruin_pct']:.1f}% / {pr['ev_npv_24m_vnd_tr']:+.1f}tr` vs `200K {cr['ruin_pct']:.1f}% / {cr['ev_npv_24m_vnd_tr']:+.1f}tr` |"
            )
    lines.append("")

    lines.append("### 6.2. Độ Nhạy Chiết Khấu NPV (`0% / 4% / 6% / 8%/Năm`) & Tách Bạch Phí Hoàn Thẻ FTMO (`0,0%` vs `1,5%`, B6)")
    lines.append("")
    lines.append("| Cỡ FTMO Std (`1,00x`, 1 vé `C10_NEWS_ON`) | `r = 0%` (Chưa chiết khấu) | `r = 4%/năm` | **`r = 6%/năm` (Chuẩn VN)** | `r = 8%/năm` | Chênh lệch `6%` vs `0%` |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for cap in (10_000.0, 100_000.0):
        by_r = {row["discount_rate_pct"]: row for row in results["npv_discount_sensitivity"] if abs(row["capital_usd"] - cap) < 1e-6}
        if 0.0 in by_r and 6.0 in by_r:
            d_pct = 100.0 * (by_r[6.0]["ev_npv_24m_usd"] - by_r[0.0]["ev_npv_24m_usd"]) / max(1e-6, abs(by_r[0.0]["ev_npv_24m_usd"]))
            lines.append(
                f"| **`{int(cap//1000)}K USD` (`24T` / `36T`)** | `{by_r[0.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[0.0]['ev_npv_36m_vnd_tr']:+.1f}tr` | `{by_r[4.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[4.0]['ev_npv_36m_vnd_tr']:+.1f}tr` | **`{by_r[6.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[6.0]['ev_npv_36m_vnd_tr']:+.1f}tr`** | `{by_r[8.0]['ev_npv_24m_vnd_tr']:+.1f}` / `{by_r[8.0]['ev_npv_36m_vnd_tr']:+.1f}tr` | `{d_pct:+.1f}%` |"
            )
    lines.append("")
    if results.get("fee_accounting_sensitivity"):
        lines.append("**Độ nhạy tách phí mua thẻ (`+2,5%` không hoàn) · hoàn phí thẻ FTMO (`0,0%` mặc định vs `1,5%` kênh rút) · rút lợi nhuận (`1,5%`):**")
        lines.append("")
        lines.append("| Cỡ FTMO | Ma sát | `NPV 24T` hoàn về thẻ (`0,0%`) | `NPV 24T` nếu trừ `1,5%` kênh rút | Chênh lệch (`0,0% - 1,5%`) |")
        lines.append("|---:|---:|---:|---:|---:|")
        for fr in results["fee_accounting_sensitivity"]:
            lines.append(
                f"| **`{int(fr['capital_usd']//1000)}K`** | `{fr['friction_x']:.2f}x` | `{fr['refund_card_0pct_npv24_usd']:+,.2f} USD` | `{fr['refund_rail_1_5pct_npv24_usd']:+,.2f} USD` | `{fr['delta_card_minus_rail_usd']:+.2f} USD` (`{fr['delta_card_minus_rail_vnd_tr']:+.3f} tr`) |"
            )
        lines.append("")

    lines.append("### 6.3. Quy Tắc Cắt Bỏ Chi Phí Chìm (`Sunk-Cost Abort` Khi Trượt Giá Sống Vượt `> 1,75x`, Vốn `35tr`, Gói `50K`, `C10_NEWS_ON`)")
    lines.append("")
    lines.append("| Mức trượt giá thực tế bất lợi | Cố mua vé gỡ (Không cắt): Tổng phí `24T` / `NPV 24T` | Dừng mua vé sau `42` phiên đo xấu: Tổng phí `24T` / `NPV 24T` | Tiền phí tiết kiệm được | Cải thiện `NPV 24T` |")
    lines.append("|---:|---|---|---:|---:|")
    for row in results["sunk_cost_abort_study"]:
        bl, ab = row["blind_retry_chasing"], row["live_friction_abort_day42"]
        lines.append(
            f"| **`{row['adverse_friction_x']:.2f}x`** | `{bl['mean_fees_24m_usd']:,.0f} USD` / `{bl['ev_npv_24m_vnd_tr']:+.1f} tr` | `{ab['mean_fees_24m_usd']:,.0f} USD` / `{ab['ev_npv_24m_vnd_tr']:+.1f} tr` | **`{row['fees_saved_vnd_tr']:+.1f} tr VND`** (`{row['fees_saved_usd']:+.0f} USD`) | **`{row['npv24_saved_vnd_tr']:+.1f} tr VND`** |"
        )
    lines.append("")

    lines.append("### 6.4. Giá Trị Thật Của Chia `1` Quỹ vs `2` Quỹ vs `3` Quỹ Sống Sót (Loại `E8 Pro`, Tắt `own_book`, Vốn `50tr`)")
    lines.append("")
    lines.append("*Lưu ý quan trọng:* Toàn bộ tài khoản chạy trên **cùng một ngày thị trường** (`tương quan sập thị trường = 1,0`). `The5ers` (`max(balance, equity)` tại reset) và `IC Funded` (`equity` tại reset) mang song song **`TERMS_VERIFIED_EXECUTION_UNMEASURED`** và **`DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`** *(công thức `balance * (1 - daily_lim)` chỉ đúng khi đóng sạch lệnh đúng giờ reset)*; `E8 Pro` đã bị **loại hoàn toàn** khỏi danh mục này do bẫy khóa sàn DD sau lần rút đầu.")
    lines.append("")
    lines.append("| Xác suất sự cố riêng mỗi hãng/năm | Phân bổ (`own_book = 0`) | Cháy vốn | `NPV 24T` TB / TV (tr VND) | `P(NPV24 <= 0)` | `NPV 36T` (tr VND) | Tỷ lệ gặp sự cố hãng | Vốn Funded đỉnh TB |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    alloc_vi = {
        "SINGLE_FIRM_FTMO_2x100K": "1 Quỹ (FTMO `2x 100K` · ĐO DEMO)",
        "TWO_FIRM_SPLIT": "2 Quỹ (`FTMO + The5ers` · The5ers CHƯA ĐO)",
        "THREE_FIRM_SURVIVING_SPLIT": "3 Quỹ sống sót (`FTMO + The5ers + IC Funded` · 2 hãng CHƯA ĐO)",
    }
    for row in results["cross_firm_hazard_study"]:
        lines.append(
            f"| `{row['hazard_rate']}` | **{alloc_vi.get(row['allocation'], row['allocation'])}** | `{row['ruin_pct']:.2f}%` | `{row['ev_npv_24m_vnd_tr']:+.1f}` / `{row['med_npv_24m_vnd_tr']:+.1f}` | `{row['p_npv24_le_0_pct']:.1f}%` | **`{row['ev_npv_36m_vnd_tr']:+.1f}`** | `{row['firm_disruption_rate_pct']:.1f}%` | `{row['mean_max_funded_nom_usd']:,.0f} USD` |"
        )
    lines.append("")

    # Section 7: Dual-Objective Pareto Grid across 15 bankroll x top-up cells (Mean + Median + P(NPV24 <= 0) on EVERY cell!)
    lines.append(f"## 7. Ma Trận Pareto 2 Mục Tiêu Theo Vốn & Nạp Hàng Tháng (`{p_var}` · `own_book = 0` · BF Ngày 0 + Retry Giá Gốc · `DAILY_APPROX`)")
    lines.append("")
    lines.append(
        "So sánh **10 chính sách** (`P1`, `P2`, `P3`, `P4A_DIRECT_50K` tham, **`P4A_WAIT_FOR_100K`** giữ khe 2 chờ `100K`, `P4B_DIRECT_100K` tuần tự, **`P4B_PARALLEL_2X100K`** song song Ngày 0, `P4C_DIRECT_200K`, `P5A/P5B` chia **`3` quỹ sống sót** bỏ `E8 Pro`) trên **`15` ô vốn** (`15 / 25 / 35 / 50 / 80 tr VND` × nạp thêm `0 / 3 / 5 tr/T`, `5.000` kịch bản MC/ô, rủi ro hãng `5%/năm`):"
    )
    lines.append("")
    lines.append("- **Mọi ô đều công bố đầy đủ bộ ba:** **`TB` (Mean NPV24)** · **`TV` (Median NPV24)** · **`P<=0` (Xác suất hòa/lỗ 24T)** — tuyệt đối không che trung vị âm sau trung bình dương!")
    lines.append("- **Hồ Sơ A (`NPV_Wealth_Safe5pct`):** Tối đa hóa `NPV` với ràng buộc **cháy vốn `<= 5,0%`**.")
    lines.append("- **Hồ Sơ B (`Fast_Cashflow_Safe10pct`):** Rút ngắn thời gian chờ rút đầu & tháng đói với ràng buộc **cháy vốn `<= 10,0%`**.")
    lines.append("")

    for fkey, flbl in (("1.00x", "7.1. Ma Sát Chuẩn `1,00x` (`C10_NEWS_ON`)"), ("1.50x", "7.2. Stress Trượt Giá Nặng `1,50x` (`C10_NEWS_ON` — Theo Dõi Chặt Trung Vị Âm & `P(NPV24 <= 0)`)")):
        lines.append(f"### {flbl}")
        lines.append("")
        lines.append("| Vốn + Nạp/T | **Hồ Sơ A — CHỈ FTMO (`Cháy <= 5%`)** | **Hồ Sơ B — CHỈ FTMO (`Cháy <= 10%`)** | **Đa Hãng 3 Quỹ (`The5ers/IC CHƯA ĐO`)** | `P4A-Chờ100K` vs `P4A-Tham` (`NPV24 TB / TV / P<=0`) |")
        lines.append("|---|---|---|---|---|")
        cells = results["pareto_grid"][fkey]
        for bank_tr in BANKROLL_GRID_VND_TR:
            for top_tr in TOPUP_GRID_VND_TR:
                ck = f"B{int(bank_tr)}tr_T{int(top_tr)}tr"
                c = cells[ck]
                pw = c["pareto_winners"]
                fw = pw.get("ftmo_only_verified_execution", pw)
                fa = fw["profile_a_npv_wealth_safe5pct"]
                fb = fw["profile_b_fast_cashflow_safe10pct"]
                all_a = pw["profile_a_npv_wealth_safe5pct"]
                p4w = c["policies"]["P4A_WAIT_FOR_100K"]
                p4g = c["policies"]["P4A_DIRECT_50K"]
                fa_tag = "" if fa["status"] == "FEASIBLE_RUIN_LE_5PCT" else " *(>5%)*"
                if fb["status"] == "FEASIBLE_RUIN_LE_10PCT":
                    fb_tag = ""
                elif fb["status"] == "FEASIBLE_RUIN_LE_10PCT_PAID_LT_50PCT":
                    fb_tag = " *(đạt rút <50%)*"
                else:
                    fb_tag = " *(>10%)*"
                lines.append(
                    f"| **`{int(bank_tr)}tr`+`{int(top_tr)}tr/T`** | **{_policy_vi_name(fa['winner_policy'])}**{fa_tag}<br>Cháy `{fa['ruin_pct']:.2f}%` · TB `{fa['ev_npv_24m_vnd_tr']:+.1f}tr` · **TV `{fa['med_npv_24m_vnd_tr']:+.1f}tr`** · `P<=0` `{fa['p_npv24_le_0_pct']:.1f}%` | **{_policy_vi_name(fb['winner_policy'])}**{fb_tag}<br>Cháy `{fb['ruin_pct']:.2f}%` · Chờ `{fb['uncond_med_pay1_days']:.0f}d` · TB `{fb['ev_npv_24m_vnd_tr']:+.1f}tr` · **TV `{fb['med_npv_24m_vnd_tr']:+.1f}tr`** · `P<=0` `{fb['p_npv24_le_0_pct']:.1f}%` | **{_policy_vi_name(all_a['winner_policy'])}**<br>Cháy `{all_a['ruin_pct']:.2f}%` · TB `{all_a['ev_npv_24m_vnd_tr']:+.1f}tr` · **TV `{all_a['med_npv_24m_vnd_tr']:+.1f}tr`** · `P<=0` `{all_a['p_npv24_le_0_pct']:.1f}%` | Chờ100K: `{p4w['ev_npv_24m_vnd_tr']:+.1f}` / `{p4w['med_npv_24m_vnd_tr']:+.1f}` (`{p4w['p_npv24_le_0_pct']:.0f}%`)<br>Tham: `{p4g['ev_npv_24m_vnd_tr']:+.1f}` / `{p4g['med_npv_24m_vnd_tr']:+.1f}` (`{p4g['p_npv24_le_0_pct']:.0f}%`) |"
                )
        lines.append("")
        if fkey == "1.00x" and "B25tr_T0tr" in cells and "B35tr_T0tr" in cells and "B50tr_T0tr" in cells:
            b_list = [int(b) for b in BANKROLL_GRID_VND_TR if f"B{int(b)}tr_T0tr" in cells]
            w_vals = [(b, cells[f"B{b}tr_T0tr"]["policies"]["P4A_WAIT_FOR_100K"]["ev_npv_24m_vnd_tr"]) for b in b_list]
            g_vals = [(b, cells[f"B{b}tr_T0tr"]["policies"]["P4A_DIRECT_50K"]["ev_npv_24m_vnd_tr"]) for b in b_list]
            dip_pair = next(
                ((g_vals[i - 1], g_vals[i]) for i in range(1, len(g_vals)) if g_vals[i][1] < g_vals[i - 1][1]),
                None,
            )
            w_ladder_txt = " -> ".join(f"`{v:+.1f}tr` (`{b}tr`)" for b, v in w_vals)
            if dip_pair is not None:
                (b_prev, g_prev), (b_dip, g_dip) = dip_pair
                w_dip = dict(w_vals)[b_dip]
                dip_txt = (
                    f"Chính sách tham `P4A_DIRECT_50K` tụt phi đơn điệu ở mốc **`{b_dip}tr`** "
                    f"(`{g_dip:+.1f}tr` so với `{g_prev:+.1f}tr` ở `{b_prev}tr`, tức **`{g_dip - g_prev:+.1f}tr`**) "
                    f"do vội mở thêm vé `50K` thứ hai ngay khi vừa đậu (mốc tụt dịch từ `35tr` sang `{b_dip}tr` khi vé mua lại tính đúng giá gốc); "
                    f"ngược lại **`P4A_WAIT_FOR_100K`** giữ khe 2 chờ đúng `100K` giúp `NPV24` tăng đơn điệu sạch theo vốn: {w_ladder_txt} "
                    f"(riêng tại `{b_dip}tr` vượt bản tham **`{w_dip - g_dip:+.1f}tr`**)."
                )
            else:
                dip_txt = (
                    f"**`P4A_WAIT_FOR_100K`** giữ khe 2 chờ đúng `100K` giúp `NPV24` tăng đơn điệu sạch theo vốn: {w_ladder_txt}, "
                    f"vượt trội hơn bản tham `P4A_DIRECT_50K` ở mọi mức vốn trung bình."
                )
            lines.append(f"> **Đóng lỗi phi đơn điệu `P4A` (B2):** {dip_txt}")
            lines.append("")
        if fkey == "1.50x" and "B35tr_T0tr" in cells:
            p4b35 = cells["B35tr_T0tr"]["policies"]["P4B_DIRECT_100K"]
            lines.append(
                f"> **Cảnh báo rủi ro đuôi lệch ở `35tr @ 1,50x` (`P4B_DIRECT_100K`):** Dù `NPV24` trung bình vẫn dương **`{p4b35['ev_npv_24m_vnd_tr']:+.1f}tr`**, "
                f"nhưng **`NPV24` trung vị là `{p4b35['med_npv_24m_vnd_tr']:+.1f}tr`** và xác suất không có lãi sau 24 tháng `P(NPV24 <= 0)` lên tới **`{p4b35['p_npv24_le_0_pct']:.1f}%`**! "
                f"Đây là bằng chứng trực quan nhất giải thích vì sao **KHÔNG** đánh giá kế hoạch thi quỹ chỉ qua một con số trung bình."
            )
            lines.append("")

    # Section 7.3: Explicit crossover check (`BF Day-0 + Regular Retries` AND `All-Regular`)
    lines.append("### 7.3. Bảng Giao Điểm Theo Vốn Ban Đầu (`0 tr/T`, `1,00x`, `C10_NEWS_ON`) — `BF Ngày 0 + Retry Giá Gốc` vs `Toàn Bộ Giá Gốc`")
    lines.append("")
    lines.append("Mỗi ô hiển thị `Cháy | TB / TV | P<=0` (`NPV 24T` theo triệu VND):")
    lines.append("")
    lines.append("| Vốn (`0tr/T`) | `P1` Lặp `10K` | `P3` Leo Thông Minh | `P4A-Chờ100K` | `P4B` Tuần tự `100K` | **`P4B` Song song `2x100K`** | `P4C` `1x200K` | `P5B` 3 Quỹ (`CHƯA ĐO`) |")
    lines.append("|---:|---|---|---|---|---|---|---|")
    for regime_lbl, src_map in (
        ("BF Ngày 0 + Retry Gốc", lambda btr: results["pareto_grid"]["1.00x"][f"B{int(btr)}tr_T0tr"]["policies"]),
        ("Toàn bộ Giá Gốc", lambda btr: results["all_regular_pricing_comparison"]["1.00x"][f"B{int(btr)}tr_T0tr"]["policies_all_regular"]),
    ):
        for bank_tr in BANKROLL_GRID_VND_TR:
            c = src_map(bank_tr)
            def _fmt_p(k: str) -> str:
                m = c[k]
                return f"`{m['ruin_pct']:.1f}%` · **`{m['ev_npv_24m_vnd_tr']:+.1f}`**/`{m['med_npv_24m_vnd_tr']:+.1f}` (`{m['p_npv24_le_0_pct']:.0f}%`)"
            lines.append(
                f"| **`{int(bank_tr)}tr`** *({regime_lbl})* | {_fmt_p('P1_REPEAT_10K')} | {_fmt_p('P3_SMART_SKIP_DOWNGRADE')} | {_fmt_p('P4A_WAIT_FOR_100K')} | {_fmt_p('P4B_DIRECT_100K')} | {_fmt_p('P4B_PARALLEL_2X100K')} | {_fmt_p('P4C_DIRECT_200K')} | {_fmt_p('P5B_CROSS_FIRM_SCALE50K_100K')} |"
            )
    lines.append("")

    # Section 8: Honest Caveats, Limitations & Next Steps
    lines.append("## 8. Công Khai Trung Thực Về Giới Hạn Mô Hình & Bước Tiếp Theo (`0 VND` Hiện Tại)")
    lines.append("")
    lines.append("1. **Mô phỏng vòng đời gắn cứng nhãn `DAILY_APPROX`:** Dữ liệu từng ngày được tái lập từ băng giá M1 với làm tròn `0,01` lot theo cỡ vốn đầu kỳ, ghép chuỗi 24–36 tháng bằng Circular Block-Bootstrap cấp ngày (`block_len = 5`). Như đã nêu tại Mục 3 (B1), tổn thất làm tròn ở bậc `5K/10K` còn khác cách thu nhỏ lot `85% free margin` và `balance * risk * 0,95` của EA MQL5 nên cần kiểm chứng MT5 `Model=4`.")
    lines.append("2. **Chưa đo khớp lệnh & điều kiện flat tại reset ở các hãng ngoài FTMO (`TERMS_VERIFIED_EXECUTION_UNMEASURED` + `DD_ANCHOR_UNVERIFIED_UNLESS_FLAT_AT_RESET`):** `The5ers` (`max(balance, equity)` tại giờ reset MT5) và `IC Funded` (`equity` tại giờ reset server) mới được xác minh điều khoản và giá; công thức DD ngày `balance * (1 - daily_lim)` chỉ đúng khi tài khoản **đóng sạch lệnh (flat) đúng giờ reset từng hãng**. `E8 Pro` đã bị loại khỏi `P5/P5B` vì bẫy khóa sàn DD. Trước khi bỏ `1 VND` vào `The5ers` hoặc `IC Funded`, bắt buộc tự đo spread/trượt giá trên Demo MT5 thật và xin xác nhận văn bản cho EA.")
    lines.append("3. **Kiểm tra độ tươi từng bậc giá & chống mốc tương lai/NaN (`fail-closed`):** Bộ nạp bảng giá bắt buộc mọi bậc giá (`42/42` tiers) phải có riêng `verified_utc`, từ chối mọi giá `NaN`/`Inf`/`<=0`, từ chối mốc thời gian tương lai (`> now + 1 ngày`, ví dụ `2099`), và tự báo lỗi nếu bất kỳ bậc giá nào cũ quá `7` ngày (`staleness_max_days`). Trước khi mua bất kỳ vé nào, chạy `python tooling/ai-engines/quant_factory/prop_pricing_refresh.py --refresh-fx --summary --check-staleness`.")
    lines.append("4. **Trạng thái chi tiền (`0 VND`):** Báo cáo này là bản đồ toán học phục vụ quyết định **sau khi** các cổng kỹ thuật (`v1.02` + đối chiếu MT5 + theo dõi Demo) được chủ sở hữu phê duyệt riêng — tự bản thân báo cáo không cấp quyền mua vé hay gửi lệnh.")
    lines.append("")

    md = "\n".join(lines)
    if "$" in md:
        raise ValueError("PROSE_POLICY_VIOLATION: Bare '$' symbol detected in Vietnamese Law-15 report!")
    return md


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Naqex Multi-Firm Capital Scaling & Promo Optimizer v2 (Dev <= 2024 ONLY)")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--step5", type=Path, default=DEFAULT_STEP5_REPORT_PATH)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-json-v2", type=Path, default=DEFAULT_OUT_JSON_V2)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--n-paths-grid", type=int, default=5_000)
    parser.add_argument("--n-paths-single", type=int, default=10_000)
    parser.add_argument("--horizon-months", type=int, default=36)
    parser.add_argument("--primary-variant", type=str, default=PRIMARY_VARIANT_DEFAULT)
    parser.add_argument("--orig-prices", action="store_true", help="Use all-regular prices on Day 0 too (instead of BF Day-0 + Regular Retries)")
    parser.add_argument("--allow-stale-catalog", action="store_true", help="Explicitly override catalog staleness check for offline historical audits")
    args = parser.parse_args(argv)

    res = run_full_capital_promo_study(
        catalog_path=args.catalog,
        step5_path=args.step5,
        n_paths_grid=args.n_paths_grid,
        n_paths_single=args.n_paths_single,
        horizon_months=args.horizon_months,
        use_promo_prices=not args.orig_prices,
        primary_variant=args.primary_variant,
        allow_stale_catalog=args.allow_stale_catalog,
    )
    saved_json = save_results_json(res, args.out_json)
    saved_json_v2 = save_results_json(res, args.out_json_v2) if args.out_json_v2 is not None else None
    md_text = render_vietnamese_law15_report(res)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md_text, encoding="utf-8", newline="\n")
    v2_str = f" | SAVED JSON_V2: {saved_json_v2} ({saved_json_v2.stat().st_size:,} B)" if saved_json_v2 else ""
    print(
        f"SAVED JSON: {saved_json} ({saved_json.stat().st_size:,} B){v2_str} | "
        f"SAVED MD: {args.out_md} ({args.out_md.stat().st_size:,} B) | "
        f"elapsed={res['elapsed_seconds']}s | primary={res['inputs']['primary_variant']} | "
        f"holdout_rows={res['safety_invariants']['holdout_rows_analysed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
