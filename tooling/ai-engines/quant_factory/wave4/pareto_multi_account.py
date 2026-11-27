"""Wave 4 (`W4-G06` & `W4-G07`): Shared-Path Multi-Account & 81-Case Pareto Simulation Kernel.

Strictly offline Dev-only simulation module (`ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`,
`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `holdout_rows_analysed = 0`).

Reuses & composes:
  - `quant_factory.capital_optimizer.policy_kernel` (`_init_slot`, `_pack_templates_for_numba`)
  - `quant_factory.capital_optimizer.simulator` (`make_block_bootstrap_indices`, `make_firm_hazard_days`)
  - `quant_factory.capital_optimizer.lot_sizing` (`assert_strict_pre_holdout_days`, `floor_lot_step`)
  - `quant_factory.capital_optimizer.summaries` (`wilson_upper_95`)
  - `quant_factory.treasury_ledger` (`BucketPolicy`, `PropAccountRecord`, `TreasuryEvent`, `TreasuryLedger`)
  - `quant_core.schemas` (`FxRatesConfig`, `SSOTFirmsCatalog`, `SSOTRiskProfiles`)
  - `quant_core.holdout_guard` (`enforce_pre_holdout_dates`)
  - `configs/ssot/firms_catalog.json`, `configs/ssot/fx_rates.json`, `configs/ssot/risk_profiles.json`

Core guarantees:
  1. Exact 81-case Pareto grid (`9` VND bankroll tiers x `3` concurrency modes x `3` after-payout policies).
  2. Shared Market Path (`rho ~ 1.0` for concurrent accounts running the same bot): ALL active slots step
     through the EXACT SAME circular-block-bootstrapped Dev market day index `src = idx_matrix[b, d]`.
  3. Per-SKU `0.01`-lot floor rounding fidelity (`5K/10K/25K/50K/100K/200K`) — NEVER linearly scales `100K`
     EV down to `5K/10K`.
  4. FTMO contract mechanics: `$400K` max active base Funded cap (`$200K`/Challenge), Scaling Plan `+25%`
     every `4` months up to `$2M` (`80% -> 90%` split), P1 fee refund on Payout #1, VN `+2.5%` card FX buy
     fee & `-1.5%` payout withdrawal fee, ZERO double-counting of Funded notional as liquid cash net worth.
  5. Full Law 13–15 metrics with `XẤP XỈ CẤP NGÀY` (`APPROX_DAILY_RESOLUTION`) label, `Pass+Fail+Pending==100%`
     at `3m/6m/12m/24m/36m`, `BOT_AUTO_KILL` vs `FIRM_HARD_BREACH`, 12m Funded blowup + Wilson 95% UB,
     and Pareto frontier extraction per bankroll tier and overall.
  6. ZERO bare Python `assert` statements (`[ARCH-02]`), safe under `python -O`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
from numba import njit
from quant_core.holdout_guard import enforce_pre_holdout_dates
from quant_core.schemas import FirmTierContract, FxRatesConfig, SSOTFirmsCatalog, SSOTRiskProfiles

from quant_factory.capital_optimizer.constants import (
    BLOCK_LEN,
    CALENDAR_DAYS_PER_TRADING_DAY,
    DEFAULT_SEED,
    ROOT,
    TRADING_DAYS_PER_MONTH,
    TRADING_DAYS_PER_YEAR,
)
from quant_factory.capital_optimizer.lot_sizing import assert_strict_pre_holdout_days, floor_lot_step
from quant_factory.capital_optimizer.policy_kernel import _init_slot, _pack_templates_for_numba
from quant_factory.capital_optimizer.simulator import make_block_bootstrap_indices, make_firm_hazard_days
from quant_factory.capital_optimizer.summaries import wilson_upper_95
from quant_factory.treasury_ledger import BucketPolicy, PropAccountRecord, TreasuryEvent, TreasuryLedger
from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE, ORDER_SEND_CAPABLE

# ---------------------------------------------------------------------------
# Constants, Enums & Canonical SSOT Paths
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave4-pareto-multi-account-v1"
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
RESOLUTION_LABEL_VI: str = "XẤP XỈ CẤP NGÀY"
RESOLUTION_TAG: str = "APPROX_DAILY_RESOLUTION"
EVIDENCE_STAGE: str = "BACKTEST_DEV_SEALED_LE_2024"

DEFAULT_SSOT_DIR: Path = ROOT / "tooling" / "ai-engines" / "configs" / "ssot"
DEFAULT_FIRMS_CATALOG_PATH: Path = DEFAULT_SSOT_DIR / "firms_catalog.json"
DEFAULT_FX_RATES_PATH: Path = DEFAULT_SSOT_DIR / "fx_rates.json"
DEFAULT_RISK_PROFILES_PATH: Path = DEFAULT_SSOT_DIR / "risk_profiles.json"

# Exact 9 VND bankroll tiers (in millions of VND)
BANKROLL_TIERS_M_VND: tuple[int, ...] = (10, 15, 25, 40, 60, 100, 150, 250, 500)

# FTMO official allocation & scaling caps
FTMO_MAX_ACTIVE_FUNDED_USD: float = 400_000.0
FTMO_MAX_SINGLE_CHALLENGE_USD: float = 200_000.0
FTMO_MAX_SCALED_FUNDED_USD: float = 2_000_000.0
FTMO_SCALING_INTERVAL_TRADING_DAYS: int = 84  # 4 trading months (4 x 21)
FTMO_SCALING_MIN_PROFIT_FRAC: float = 0.10  # >= 10% over 4 months
FTMO_SCALING_MIN_PAYOUTS: int = 2
FTMO_SCALING_STEP_FRAC: float = 0.25  # +25% of original base allocation

DEFAULT_FTMO_LADDER_CONTRACTS: tuple[str, ...] = (
    "ftmo_standard_10k",
    "ftmo_standard_25k",
    "ftmo_standard_50k",
    "ftmo_standard_100k",
    "ftmo_standard_200k",
)

ALL_SKU_AUDIT_CAPITALS_USD: tuple[float, ...] = (
    5_000.0,
    10_000.0,
    25_000.0,
    50_000.0,
    100_000.0,
    200_000.0,
)

HORIZON_MONTHS: tuple[int, ...] = (3, 6, 12, 24, 36)
DEFAULT_HORIZON_DAYS: int = 756  # 36 trading months
DEFAULT_EVAL_FAIL_COOLDOWN_DAYS: int = 5  # Guard E1: cooldown after Eval breach
DEFAULT_FUNDED_DD_FREEZE_FRAC: float = 0.035  # Guard E2: freeze new buys when any Funded >= 3.5% DD
DEFAULT_MAX_SLOTS: int = 12


class ConcurrencyMode(StrEnum):
    CONSERVATIVE_1_TICKET = "CONSERVATIVE_1_TICKET"
    GATED_STAGGER = "GATED_STAGGER"
    AGGRESSIVE_PARALLEL = "AGGRESSIVE_PARALLEL"


class AllocationPolicy(StrEnum):
    P1_RECOUP_FIRST = "P1_RECOUP_FIRST"
    P2_BALANCED_40_40_20 = "P2_BALANCED_40_40_20"
    P3_SCALE_80_20 = "P3_SCALE_80_20"


CONCURRENCY_MODES: tuple[ConcurrencyMode, ...] = (
    ConcurrencyMode.CONSERVATIVE_1_TICKET,
    ConcurrencyMode.GATED_STAGGER,
    ConcurrencyMode.AGGRESSIVE_PARALLEL,
)

ALLOCATION_POLICIES: tuple[AllocationPolicy, ...] = (
    AllocationPolicy.P1_RECOUP_FIRST,
    AllocationPolicy.P2_BALANCED_40_40_20,
    AllocationPolicy.P3_SCALE_80_20,
)

_CONCURRENCY_CODE: dict[ConcurrencyMode, int] = {
    ConcurrencyMode.CONSERVATIVE_1_TICKET: 0,
    ConcurrencyMode.GATED_STAGGER: 1,
    ConcurrencyMode.AGGRESSIVE_PARALLEL: 2,
}

_ALLOCATION_CODE: dict[AllocationPolicy, int] = {
    AllocationPolicy.P1_RECOUP_FIRST: 0,
    AllocationPolicy.P2_BALANCED_40_40_20: 1,
    AllocationPolicy.P3_SCALE_80_20: 2,
}


# ---------------------------------------------------------------------------
# Strict Fail-Closed Validators (Bug Pattern #3: reject bool, NaN, Inf)
# ---------------------------------------------------------------------------


def _require_finite_float(
    value: Any,
    name: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    strict_min: bool = False,
) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"INVALID_NUMERIC_INPUT: {name} must be a finite real number (got {value!r})")
    fv = float(value)
    if not math.isfinite(fv):
        raise ValueError(f"NON_FINITE_INPUT: {name} must be finite (got {value!r})")
    if min_val is not None:
        if strict_min and fv <= min_val:
            raise ValueError(f"RANGE_ERROR: {name} must be > {min_val}, got {fv}")
        if (not strict_min) and fv < min_val:
            raise ValueError(f"RANGE_ERROR: {name} must be >= {min_val}, got {fv}")
    if max_val is not None and fv > max_val:
        raise ValueError(f"RANGE_ERROR: {name} must be <= {max_val}, got {fv}")
    return fv


def _require_strict_int(
    value: Any,
    name: str,
    *,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"INVALID_INT_INPUT: {name} must be a strict int (got {value!r})")
    iv = int(value)
    if min_val is not None and iv < min_val:
        raise ValueError(f"RANGE_ERROR: {name} must be >= {min_val}, got {iv}")
    if max_val is not None and iv > max_val:
        raise ValueError(f"RANGE_ERROR: {name} must be <= {max_val}, got {iv}")
    return iv


# ---------------------------------------------------------------------------
# Typed Specs & TreasuryLedger BucketPolicy Integration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AllocationPolicySpec:
    """After-payout 3-bucket allocation policy integrated with `treasury_ledger.BucketPolicy`."""

    policy: AllocationPolicy
    recoup_initial_first: bool
    cash_recoup_pct: float  # Protected cash / House Money reserve
    upgrade_scale_pct: float  # Upgrade / add challenge reserve (capped; overflow -> Own-Book)
    own_book_pct: float  # Own-Book equity seed
    reserve_cap_tickets: float  # Max challenge reserve multiple of top ladder ticket before overflow

    def to_treasury_bucket_policy(self, reference_ticket_usd: float) -> BucketPolicy:
        """Construct and validate a `treasury_ledger.BucketPolicy` matching this policy."""
        ref = _require_finite_float(reference_ticket_usd, "reference_ticket_usd", min_val=0.0, strict_min=True)
        bp = BucketPolicy(
            reserve_pct=self.upgrade_scale_pct,
            own_book_pct=self.own_book_pct,
            ops_tax_pct=self.cash_recoup_pct,
            reserve_cap_tickets=self.reserve_cap_tickets,
            reference_ticket_usd=ref,
        )
        bp.validate()
        return bp


ALLOCATION_POLICY_SPECS: dict[AllocationPolicy, AllocationPolicySpec] = {
    AllocationPolicy.P1_RECOUP_FIRST: AllocationPolicySpec(
        policy=AllocationPolicy.P1_RECOUP_FIRST,
        recoup_initial_first=True,
        cash_recoup_pct=0.00,  # 100% recoups initial bankroll first; then 50% upgrade / 50% own-book
        upgrade_scale_pct=0.50,
        own_book_pct=0.50,
        reserve_cap_tickets=3.0,
    ),
    AllocationPolicy.P2_BALANCED_40_40_20: AllocationPolicySpec(
        policy=AllocationPolicy.P2_BALANCED_40_40_20,
        recoup_initial_first=False,
        cash_recoup_pct=0.40,
        upgrade_scale_pct=0.40,
        own_book_pct=0.20,
        reserve_cap_tickets=3.0,
    ),
    AllocationPolicy.P3_SCALE_80_20: AllocationPolicySpec(
        policy=AllocationPolicy.P3_SCALE_80_20,
        recoup_initial_first=False,
        cash_recoup_pct=0.10,  # 20% Cash/Own-Book split evenly (10% safe cash + 10% Own-Book)
        upgrade_scale_pct=0.80,  # 80% Upgrade/Add Challenge; overflow above cap spills to Own-Book
        own_book_pct=0.10,
        reserve_cap_tickets=2.5,
    ),
}


@dataclass(frozen=True)
class ParetoCaseConfig:
    """Single cell in the exact 81-case (`9 x 3 x 3`) Pareto simulation matrix."""

    case_id: str
    bankroll_m_vnd: int
    bankroll_vnd: float
    bankroll_usd: float
    concurrency_mode: ConcurrencyMode
    allocation_policy: AllocationPolicy
    usd_vnd_rate: float


def build_81_case_configs(
    *,
    usd_vnd_rate: float,
    bankroll_tiers_m_vnd: tuple[int, ...] = BANKROLL_TIERS_M_VND,
    concurrency_modes: tuple[ConcurrencyMode, ...] = CONCURRENCY_MODES,
    allocation_policies: tuple[AllocationPolicy, ...] = ALLOCATION_POLICIES,
) -> list[ParetoCaseConfig]:
    """Generate the canonical `9 x 3 x 3 = 81` Pareto case grid with exact VND & USD bankrolls."""
    fx = _require_finite_float(usd_vnd_rate, "usd_vnd_rate", min_val=0.0, strict_min=True)
    configs: list[ParetoCaseConfig] = []
    for tier_m in bankroll_tiers_m_vnd:
        tm = _require_strict_int(tier_m, "bankroll_m_vnd", min_val=1)
        vnd_amt = float(tm) * 1_000_000.0
        usd_amt = vnd_amt / fx
        for cmode in concurrency_modes:
            cm = ConcurrencyMode(cmode)
            for apol in allocation_policies:
                ap = AllocationPolicy(apol)
                cid = f"B{tm}M__{cm.value}__{ap.value}"
                configs.append(
                    ParetoCaseConfig(
                        case_id=cid,
                        bankroll_m_vnd=tm,
                        bankroll_vnd=vnd_amt,
                        bankroll_usd=usd_amt,
                        concurrency_mode=cm,
                        allocation_policy=ap,
                        usd_vnd_rate=fx,
                    )
                )
    return configs


def build_treasury_ledger_projection(
    *,
    policy: AllocationPolicy,
    usd_vnd_rate: float,
    reference_ticket_usd: float,
    total_fees_usd: float,
    total_gross_payouts_usd: float,
    total_cash_refunds_usd: float,
    active_funded_nominal_usd: float,
    weighted_split_frac: float = 0.80,
) -> dict[str, Any]:
    """Project summary economics through `treasury_ledger.TreasuryLedger` using validated `BucketPolicy`."""
    spec = ALLOCATION_POLICY_SPECS[AllocationPolicy(policy)]
    bp = spec.to_treasury_bucket_policy(reference_ticket_usd=max(1.0, reference_ticket_usd))
    ledger = TreasuryLedger(
        pod_name=f"Naqex Wave4 Pareto ({spec.policy.value})",
        usd_vnd_rate=usd_vnd_rate,
        policy=bp,
    )
    if active_funded_nominal_usd > 0.0:
        ledger.add_account(
            PropAccountRecord(
                account_id="FLEET_FUNDED_AGG",
                firm="FTMO",
                phase="FUNDED",
                nominal_usd=float(active_funded_nominal_usd),
                ticket_fee_usd=float(reference_ticket_usd),
                split_pct=float(weighted_split_frac),
                status="ACTIVE",
            )
        )
    if total_fees_usd > 0.0:
        ledger.add_event(
            TreasuryEvent(
                date="2024-01-02",
                event_type="CHALLENGE_FEE",
                amount_usd=float(total_fees_usd),
                firm="FTMO",
                note="Simulated total challenge fees (incl. VN +2.5% card FX)",
            )
        )
    if total_cash_refunds_usd > 0.0:
        ledger.add_event(
            TreasuryEvent(
                date="2024-06-01",
                event_type="FEE_REFUND",
                amount_usd=float(total_cash_refunds_usd),
                firm="FTMO",
                is_hub_credit=False,
                note="P1 fee refund on Payout #1",
            )
        )
    if total_gross_payouts_usd > 0.0:
        ledger.add_event(
            TreasuryEvent(
                date="2024-12-30",
                event_type="PROP_PAYOUT",
                amount_usd=float(total_gross_payouts_usd),
                firm="FTMO",
                split_pct=float(weighted_split_frac),
                note="Simulated prop payouts",
            )
        )
    return ledger.compute_summary()


# ---------------------------------------------------------------------------
# Read-Only SSOT Loaders (NEVER mutates configs/ssot/*.json)
# ---------------------------------------------------------------------------


def load_ssot_bundle(
    *,
    firms_catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH,
    fx_rates_path: Path = DEFAULT_FX_RATES_PATH,
    risk_profiles_path: Path = DEFAULT_RISK_PROFILES_PATH,
) -> tuple[SSOTFirmsCatalog, FxRatesConfig, SSOTRiskProfiles, dict[str, str]]:
    """Load & Pydantic-validate immutable SSOT configs + compute SHA-256 provenance hashes."""
    firms_raw = firms_catalog_path.read_bytes()
    fx_raw = fx_rates_path.read_bytes()
    risk_raw = risk_profiles_path.read_bytes()

    firms = SSOTFirmsCatalog.model_validate(json.loads(firms_raw.decode("utf-8")))
    fx = FxRatesConfig.model_validate(json.loads(fx_raw.decode("utf-8")))
    risk = SSOTRiskProfiles.model_validate(json.loads(risk_raw.decode("utf-8")))

    hashes = {
        "firms_catalog_sha256": hashlib.sha256(firms_raw).hexdigest(),
        "fx_rates_sha256": hashlib.sha256(fx_raw).hexdigest(),
        "risk_profiles_sha256": hashlib.sha256(risk_raw).hexdigest(),
    }
    return firms, fx, risk, hashes


def _contract_execution_tag(contract: FirmTierContract) -> str:
    """Enforce explicit `TERMS_VERIFIED_EXECUTION_UNMEASURED` tag for The5ers / unmeasured firms."""
    if contract.firm_id.lower() == "the5ers":
        return "TERMS_VERIFIED_EXECUTION_UNMEASURED"
    return str(contract.execution_status)


def _refund_milestone_code(milestone: str) -> int:
    s = str(milestone).upper()
    if "THIRD" in s:
        return 3
    if "SECOND" in s:
        return 2
    if "NONE" in s:
        return 0
    return 1


def _daily_dd_anchor_from_ssot(mode: str) -> str:
    m = str(mode).upper()
    if "MIDNIGHT_BALANCE_OVER_INITIAL" in m:
        return "initial_balance"
    return "prev_day_balance"


def _cal_days_to_trading_days(cal_days: int) -> int:
    if cal_days <= 1:
        return 1
    return max(1, int(round(float(cal_days) * TRADING_DAYS_PER_YEAR / 365.2425)))


# ---------------------------------------------------------------------------
# Per-SKU Exact 0.01-Lot Stage Array Builder (Zero Linear EV Scaling!)
# ---------------------------------------------------------------------------


def build_per_sku_stage_arrays_from_trades(
    *,
    dev_days: list[str] | tuple[str, ...],
    trades: list[dict[str, Any]],
    capital_usd: float,
    risk_profile: dict[str, Any] | None = None,
    vol_step: float = 0.01,
    vol_min: float = 0.01,
    vol_max: float = 1000.0,
) -> tuple[tuple[np.ndarray, ...], dict[str, Any]]:
    """Build exact 28-array stage tuple at a specific SKU capital using per-trade `0.01`-lot flooring.

    NEVER linearly scales `100K` EV down to `5K/10K`: every trade's lot size is floored independently via
    `floor_lot_step(budget_usd / stop_risk_with_cost_usd)` at `capital_usd`, dropping `< 0.01`-lot trades.
    Enforces strict Dev Holdout seal (`<= 2024-12-31`, `holdout_rows_analysed = 0`) safe under `python -O`.
    """
    cap = _require_finite_float(capital_usd, "capital_usd", min_val=0.0, strict_min=True)
    vstep = _require_finite_float(vol_step, "vol_step", min_val=0.0, strict_min=True)
    vmin = _require_finite_float(vol_min, "vol_min", min_val=0.0, strict_min=True)
    vmax = _require_finite_float(vol_max, "vol_max", min_val=vmin)

    if not dev_days:
        raise ValueError("EMPTY_DEV_DAYS: dev_days must contain at least 1 trading day <= 2024-12-31")
    ordered_days = sorted({str(d) for d in dev_days})
    enforce_pre_holdout_dates(ordered_days, context="wave4.pareto.dev_days", cutoff_day=HOLDOUT_CUTOFF_DAY)
    assert_strict_pre_holdout_days(ordered_days)

    day_to_idx = {d: i for i, d in enumerate(ordered_days)}
    n_days = len(ordered_days)

    # Validate ALL trade dates strictly pre-Holdout (fail-closed under python -O!)
    if trades:
        trade_days = [str(tr["day"]) for tr in trades]
        enforce_pre_holdout_dates(trade_days, context="wave4.pareto.trades", cutoff_day=HOLDOUT_CUTOFF_DAY)
        assert_strict_pre_holdout_days(trade_days)

    # Group validated trades by day index
    trades_by_day: list[list[tuple[float, float, float, float, float]]] = [[] for _ in range(n_days)]
    for tr in trades:
        dk = str(tr["day"])
        if dk not in day_to_idx:
            raise ValueError(f"TRADE_DAY_NOT_IN_DEV_DAYS: {dk}")
        br = _require_finite_float(tr["base_risk_frac"], "base_risk_frac", min_val=0.0, max_val=1.0, strict_min=True)
        sc = _require_finite_float(
            tr["stop_risk_with_cost_usd"], "stop_risk_with_cost_usd", min_val=0.0, strict_min=True
        )
        net1 = _require_finite_float(tr["net_usd_per_lot"], "net_usd_per_lot")
        dd1 = _require_finite_float(
            tr.get("intraday_dd_usd_per_lot", max(0.0, -net1) + 0.15 * sc),
            "intraday_dd_usd_per_lot",
            min_val=0.0,
        )
        up1 = _require_finite_float(
            tr.get("intraday_up_usd_per_lot", max(0.0, net1) + 0.10 * sc),
            "intraday_up_usd_per_lot",
            min_val=0.0,
        )
        trades_by_day[day_to_idx[dk]].append((br, sc, net1, dd1, up1))

    rp = risk_profile or {}
    p1_mult = _require_finite_float(rp.get("p1_mult", 4.00), "p1_mult", min_val=0.0, strict_min=True)
    p1l_mult = _require_finite_float(rp.get("p1_lock_mult", 2.50), "p1_lock_mult", min_val=0.0, strict_min=True)
    p2_mult = _require_finite_float(rp.get("p2_mult", 3.50), "p2_mult", min_val=0.0, strict_min=True)
    p2l_mult = _require_finite_float(rp.get("p2_lock_mult", 1.75), "p2_lock_mult", min_val=0.0, strict_min=True)
    fn_mult = _require_finite_float(rp.get("funded_mult", 1.00), "funded_mult", min_val=0.0, strict_min=True)
    amb_mult = _require_finite_float(rp.get("amber_mult", 0.65), "amber_mult", min_val=0.0, strict_min=True)
    red_mult = _require_finite_float(rp.get("red_mult", 0.40), "red_mult", min_val=0.0, strict_min=True)

    def _replay_stage(mult: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
        nets = np.zeros(n_days, dtype=np.float64)
        dds = np.zeros(n_days, dtype=np.float64)
        ups = np.zeros(n_days, dtype=np.float64)
        flgs = np.zeros(n_days, dtype=np.int8)

        total_sig = 0
        sized_cnt = 0
        min_lot_rej = 0
        ideal_r_sum = 0.0
        actual_r_sum = 0.0
        wins_sum = 0.0
        wins_cnt = 0
        loss_sum = 0.0
        loss_cnt = 0
        r_sum = 0.0
        cur_loss = 0
        max_loss = 0
        bal = cap
        peak = cap
        max_dd = 0.0

        for di in range(n_days):
            day_tr = trades_by_day[di]
            if not day_tr:
                continue
            d_net = 0.0
            d_dd = 0.0
            d_up = 0.0
            any_sized = False
            for br, sc, net1, dd1, up1 in day_tr:
                total_sig += 1
                budget = cap * br * mult
                ideal_r_sum += budget
                lot = floor_lot_step(budget / sc, step=vstep, vol_min=vmin, vol_max=vmax)
                if lot <= 0.0:
                    min_lot_rej += 1
                    continue
                any_sized = True
                sized_cnt += 1
                actual_r_sum += lot * sc
                pnl = lot * net1
                d_net += pnl
                d_dd += lot * dd1
                d_up += lot * up1
                if budget > 1e-12:
                    r_sum += pnl / budget
                if pnl > 0.0:
                    wins_sum += pnl
                    wins_cnt += 1
                    cur_loss = 0
                elif pnl < 0.0:
                    loss_sum += -pnl
                    loss_cnt += 1
                    cur_loss += 1
                    if cur_loss > max_loss:
                        max_loss = cur_loss

            if any_sized:
                # Ensure intraday DD is at least closing loss, intraday upside at least closing gain
                if -d_net > d_dd:
                    d_dd = -d_net
                if d_net > d_up:
                    d_up = d_net
                nets[di] = d_net
                dds[di] = d_dd
                ups[di] = d_up
                flgs[di] = 1
                bal += d_net
                if bal > peak:
                    peak = bal
                if (peak - (bal - d_net - d_dd)) > max_dd:
                    max_dd = peak - (bal - d_net - d_dd)

        yrs = max(1.0 / 12.0, n_days / float(TRADING_DAYS_PER_YEAR))
        tot_net = float(np.sum(nets))
        ann_pct = 100.0 * (tot_net / yrs) / cap
        max_dd_pct = 100.0 * max_dd / cap
        calmar = (ann_pct / max_dd_pct) if max_dd_pct > 1e-9 else 0.0
        dret = nets / cap
        sd = float(np.std(dret, ddof=1)) if n_days > 1 else 0.0
        sharpe = (float(np.mean(dret)) / sd * math.sqrt(TRADING_DAYS_PER_YEAR)) if sd > 1e-12 else 0.0
        pf = (wins_sum / loss_sum) if loss_sum > 1e-9 else (99.0 if wins_sum > 0.0 else 0.0)
        wr = (100.0 * wins_cnt / max(1, wins_cnt + loss_cnt)) if (wins_cnt + loss_cnt) > 0 else 0.0
        rr = ((wins_sum / wins_cnt) / (loss_sum / loss_cnt)) if (wins_cnt > 0 and loss_cnt > 0) else 0.0
        ev_r = (r_sum / sized_cnt) if sized_cnt > 0 else 0.0

        diag = {
            "capital_usd": cap,
            "mult": mult,
            "holdout_rows_analysed": 0,
            "total_signals": total_sig,
            "sized_trades": sized_cnt,
            "min_lot_rejected": min_lot_rej,
            "min_lot_reject_pct": round(100.0 * min_lot_rej / max(1, total_sig), 3),
            "mean_risk_utilization_pct": round(100.0 * actual_r_sum / max(1e-9, ideal_r_sum), 2),
            "total_net_usd": round(tot_net, 2),
            "ev_pct_of_capital": round(100.0 * tot_net / cap, 4),
            "ann_return_pct": round(ann_pct, 3),
            "max_dd_pct": round(max_dd_pct, 3),
            "calmar": round(calmar, 3),
            "sharpe": round(sharpe, 3),
            "winrate_pct": round(wr, 2),
            "avg_rr": round(rr, 3),
            "ev_per_trade_r": round(ev_r, 4),
            "profit_factor": round(pf, 3),
            "max_loss_streak_trades": max_loss,
        }
        return nets, dds, ups, flgs, diag

    n_p1, d_p1, u_p1, f_p1, _ = _replay_stage(p1_mult)
    n_p1l, d_p1l, u_p1l, f_p1l, _ = _replay_stage(p1l_mult)
    n_p2, d_p2, u_p2, f_p2, _ = _replay_stage(p2_mult)
    n_p2l, d_p2l, u_p2l, f_p2l, _ = _replay_stage(p2l_mult)
    n_fn, d_fn, u_fn, f_fn, fn_diag = _replay_stage(fn_mult)
    n_amb, d_amb, u_amb, f_amb, _ = _replay_stage(fn_mult * amb_mult)
    n_red, d_red, u_red, f_red, _ = _replay_stage(fn_mult * red_mult)

    stage_tuple = (
        n_p1, d_p1, u_p1, f_p1,
        n_p1l, d_p1l, u_p1l, f_p1l,
        n_p2, d_p2, u_p2, f_p2,
        n_p2l, d_p2l, u_p2l, f_p2l,
        n_fn, d_fn, u_fn, f_fn,
        n_amb, d_amb, u_amb, f_amb,
        n_red, d_red, u_red, f_red,
    )
    return stage_tuple, fn_diag


def audit_per_sku_lot_floor_sensitivity(
    *,
    dev_days: list[str] | tuple[str, ...],
    trades: list[dict[str, Any]],
    capitals_usd: tuple[float, ...] = ALL_SKU_AUDIT_CAPITALS_USD,
    funded_mult: float = 1.0,
) -> dict[str, Any]:
    """Audit exact per-SKU `0.01`-lot floor sensitivity vs naive `100K` linear scaling across all SKUs."""
    rows: dict[str, dict[str, Any]] = {}
    for cap in capitals_usd:
        _, diag = build_per_sku_stage_arrays_from_trades(
            dev_days=dev_days,
            trades=trades,
            capital_usd=cap,
            risk_profile={"funded_mult": funded_mult},
        )
        label = f"{int(round(cap / 1000.0))}K"
        rows[label] = diag

    ref_ev_pct = rows.get("100K", {}).get("ev_pct_of_capital", 0.0)
    for _lbl, r in rows.items():
        if abs(ref_ev_pct) > 1e-9:
            linear_overstatement_pct = 100.0 * (ref_ev_pct - r["ev_pct_of_capital"]) / abs(ref_ev_pct)
        else:
            linear_overstatement_pct = 0.0
        r["linear_from_100k_overstatement_pct"] = round(linear_overstatement_pct, 3)

    return {
        "holdout_rows_analysed": 0,
        "funded_mult": float(funded_mult),
        "reference_sku": "100K",
        "skus": rows,
    }


def build_ssot_templates(
    *,
    firms_catalog: SSOTFirmsCatalog,
    risk_profiles: SSOTRiskProfiles,
    contract_ids: tuple[str, ...] = DEFAULT_FTMO_LADDER_CONTRACTS,
    dev_days: list[str] | tuple[str, ...],
    trades: list[dict[str, Any]],
    profile_id: str | None = None,
    use_promo_day0: bool = False,
    funded_mult_override: float | None = 1.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build packed-ready template dicts directly from immutable SSOT configs + exact per-SKU `0.01`-lot arrays."""
    pid = profile_id or risk_profiles.primary_profile_id
    if pid not in risk_profiles.profiles:
        raise ValueError(f"UNKNOWN_RISK_PROFILE: {pid!r}")
    rp = risk_profiles.profiles[pid]
    p1 = rp.phases["p1"]
    p2 = rp.phases["p2"]
    fn = rp.phases["funded"]

    fn_mult = (
        _require_finite_float(funded_mult_override, "funded_mult_override", min_val=0.0, strict_min=True)
        if funded_mult_override is not None
        else float(fn.base_phase_mult)
    )
    rp_dict = {
        "p1_mult": float(p1.base_phase_mult),
        "p1_lock_mult": float(p1.profit_lock_mult),
        "p2_mult": float(p2.base_phase_mult),
        "p2_lock_mult": float(p2.profit_lock_mult),
        "funded_mult": fn_mult,
        "amber_mult": float(rp.amber_mult),
        "red_mult": float(rp.red_mult),
    }

    firms_seen: dict[str, int] = {}
    templates: list[dict[str, Any]] = []
    sku_diags: dict[str, dict[str, Any]] = {}

    for cid in contract_ids:
        if cid not in firms_catalog.contracts:
            raise ValueError(f"UNKNOWN_SSOT_CONTRACT: {cid!r}")
        c = firms_catalog.contracts[cid]
        if not c.available_vn:
            raise ValueError(f"CONTRACT_UNAVAILABLE_VN: {cid!r} ({c.unavailable_reason_vn})")
        if c.fee_orig_usd is None or c.fee_orig_usd <= 0.0:
            raise ValueError(f"MISSING_FEE_ORIG_USD: {cid!r}")

        fid = c.firm_id.upper()
        if fid not in firms_seen:
            firms_seen[fid] = len(firms_seen)
        fidx = firms_seen[fid]

        st_arrs, fn_diag = build_per_sku_stage_arrays_from_trades(
            dev_days=dev_days,
            trades=trades,
            capital_usd=float(c.capital_usd),
            risk_profile=rp_dict,
        )
        sku_diags[cid] = fn_diag

        fee_orig = float(c.fee_orig_usd)
        fee_day0 = float(c.fee_promo_usd) if (use_promo_day0 and c.fee_promo_usd is not None) else fee_orig
        exec_tag = _contract_execution_tag(c)
        is_ftmo = c.firm_id.lower() == "ftmo"

        templates.append(
            {
                "contract_id": cid,
                "firm_idx": fidx,
                "firm_id": fid,
                "program_id": c.program_id,
                "display_name": c.display_name,
                "execution_status": exec_tag,
                "steps": int(c.steps),
                "capital_usd": float(c.capital_usd),
                "fee_day0_usd": fee_day0,
                "fee_regular_usd": fee_orig,
                "fee_refund_pct": float(c.fee_refund_external_cash_frac),
                "fee_refund_hub_credit_frac": float(c.fee_refund_hub_credit_frac),
                "card_fx_fee_frac": float(c.card_fx_fee_frac),
                "payout_withdrawal_fee_pct": float(c.withdrawal_fee_frac),
                "withdrawal_fee_pct": float(c.withdrawal_fee_frac),
                "refund_withdrawal_fee_pct": 0.0 if is_ftmo else float(c.withdrawal_fee_frac),
                "p1_target_pct": float(c.p1_target_frac),
                "p2_target_pct": float(c.p2_target_frac),
                "dd_daily_pct": float(c.daily_loss_limit_frac),
                "dd_max_pct": float(c.static_loss_limit_frac),
                "dd_type": str(c.dd_type),
                "daily_dd_anchor": _daily_dd_anchor_from_ssot(c.daily_dd_anchor_mode),
                "best_day_cap_pct": 0.0,
                "min_trading_days": int(c.min_trading_days),
                "min_profitable_days": int(c.min_profitable_days),
                "min_profitable_day_pct": float(c.profitable_day_threshold_frac),
                "profit_split_pct": float(c.payout_split_frac),
                "profit_split_max_pct": float(c.payout_split_max_frac),
                "payout_cycle_trading_days": _cal_days_to_trading_days(int(c.payout_cycle_cal_days)),
                "min_payout_usd": float(c.min_payout_usd),
                "p1_lock_trigger": float(p1.profit_lock_trigger_of_target_frac),
                "p2_lock_trigger": float(p2.profit_lock_trigger_of_target_frac),
                "amber_dd": float(rp.amber_dd_frac),
                "red_dd": float(rp.red_dd_frac),
                "p1_ea_stop": float(p1.kill_daily_dd_frac),
                "p2_ea_stop": float(p2.kill_daily_dd_frac),
                "fn_ea_stop": float(fn.kill_daily_dd_frac),
                "p1_ea_static_stop": float(p1.kill_static_dd_frac),
                "p2_ea_static_stop": float(p2.kill_static_dd_frac),
                "fn_ea_static_stop": float(fn.kill_static_dd_frac),
                "refund_payout_milestone": _refund_milestone_code(c.fee_refund_milestone),
                "payout_buffer_retention_pct": 0.0,
                "locks_at_initial_after_first_payout": False,
                "min_payout_profit_pct": 0.0,
                "daily_profit_cap_pct": 0.0,
                "funded_first_payout_min_prof_days": 0,
                "funded_first_payout_prof_pct": 0.0,
                "stage_arrays": st_arrs,
            }
        )

    exec_statuses = sorted({str(t["execution_status"]) for t in templates})
    fleet_exec_status = (
        "TERMS_VERIFIED_EXECUTION_UNMEASURED"
        if "TERMS_VERIFIED_EXECUTION_UNMEASURED" in exec_statuses
        else "MEASURED_DEMO_EXECUTION"
    )
    meta = {
        "profile_id": pid,
        "funded_mult": fn_mult,
        "use_promo_day0": bool(use_promo_day0),
        "pricing_regime": "MODEL_ASSUMPTION_PROMO_DAY0" if use_promo_day0 else "ALL_REGULAR_SSOT",
        "execution_status": fleet_exec_status,
        "contract_execution_statuses": {t["contract_id"]: t["execution_status"] for t in templates},
        "sku_funded_diagnostics": sku_diags,
        "n_firms": len(firms_seen),
        "firm_index_map": firms_seen,
    }
    return templates, meta


# ---------------------------------------------------------------------------
# Numba-JIT Shared-Path Multi-Account Fleet Simulator
# ---------------------------------------------------------------------------


@njit(cache=True, nogil=True)
def _pick_ladder_rung(
    cash_available: float,
    ladder_tpls: np.ndarray,
    tpl_cap: np.ndarray,
    tpl_fee_day0_usd: np.ndarray,
    tpl_fee_regular_usd: np.ndarray,
    tpl_card_fx_frac: np.ndarray,
    tpl_firm_id: np.ndarray,
    firm_dead: np.ndarray,
    firm_active_base_funded: np.ndarray,
    firm_active_eval_pipe: np.ndarray,
    firm_max_funded_cap: np.ndarray,
    firm_max_single_challenge: np.ndarray,
    day_idx: int,
    reserve_mult: float,
    allow_fallback_to_min: bool,
) -> int:
    """Pick the highest feasible ladder rung respecting cash reserve, FTMO 400K cap & 200K/challenge cap."""
    n_ladder = len(ladder_tpls)
    best_rung = -1
    min_feasible_rung = -1

    for i in range(n_ladder):
        tid = ladder_tpls[i]
        fid = tpl_firm_id[tid]
        if firm_dead[fid] == 1:
            continue
        cap = tpl_cap[tid]
        if cap > firm_max_single_challenge[fid] + 1e-6:
            continue
        if firm_active_base_funded[fid] + firm_active_eval_pipe[fid] + cap > firm_max_funded_cap[fid] + 1e-6:
            continue
        base_fee = tpl_fee_day0_usd[tid] if day_idx == 0 else tpl_fee_regular_usd[tid]
        ef = base_fee * (1.0 + tpl_card_fx_frac[tid])
        if cash_available >= ef - 1e-9:
            if min_feasible_rung < 0:
                min_feasible_rung = i
            if cash_available >= ef * reserve_mult - 1e-9:
                best_rung = i

    if best_rung >= 0:
        return best_rung
    if allow_fallback_to_min:
        return min_feasible_rung
    return -1


@njit(cache=True, nogil=True)
def _simulate_wave4_pareto_fleet_numba(
    idx_matrix: np.ndarray,
    hazard_days: np.ndarray,
    tpl_n_p1: np.ndarray, tpl_d_p1: np.ndarray, tpl_u_p1: np.ndarray, tpl_f_p1: np.ndarray,
    tpl_n_p1l: np.ndarray, tpl_d_p1l: np.ndarray, tpl_u_p1l: np.ndarray, tpl_f_p1l: np.ndarray,
    tpl_n_p2: np.ndarray, tpl_d_p2: np.ndarray, tpl_u_p2: np.ndarray, tpl_f_p2: np.ndarray,
    tpl_n_p2l: np.ndarray, tpl_d_p2l: np.ndarray, tpl_u_p2l: np.ndarray, tpl_f_p2l: np.ndarray,
    tpl_n_fn: np.ndarray, tpl_d_fn: np.ndarray, tpl_u_fn: np.ndarray, tpl_f_fn: np.ndarray,
    tpl_n_amb: np.ndarray, tpl_d_amb: np.ndarray, tpl_u_amb: np.ndarray, tpl_f_amb: np.ndarray,
    tpl_n_red: np.ndarray, tpl_d_red: np.ndarray, tpl_u_red: np.ndarray, tpl_f_red: np.ndarray,
    tpl_firm_id: np.ndarray,
    tpl_steps: np.ndarray,
    tpl_cap: np.ndarray,
    tpl_fee_day0_usd: np.ndarray,
    tpl_fee_regular_usd: np.ndarray,
    tpl_refund_pct: np.ndarray,
    tpl_wd_fee_pct: np.ndarray,
    tpl_refund_wd_fee_pct: np.ndarray,
    tpl_p1_target: np.ndarray,
    tpl_p2_target: np.ndarray,
    tpl_daily_lim: np.ndarray,
    tpl_max_dd_lim: np.ndarray,
    tpl_dd_type: np.ndarray,
    tpl_daily_dd_anchor: np.ndarray,
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
    # Wave 4 extensions
    tpl_card_fx_frac: np.ndarray,
    tpl_split_max: np.ndarray,
    tpl_p1_ea_static_stop: np.ndarray,
    tpl_p2_ea_static_stop: np.ndarray,
    tpl_fn_ea_static_stop: np.ndarray,
    firm_max_funded_cap: np.ndarray,
    firm_max_single_challenge: np.ndarray,
    firm_max_scaled_cap: np.ndarray,
    ladder_tpls: np.ndarray,
    concurrency_code: int,  # 0=CONSERVATIVE_1_TICKET, 1=GATED_STAGGER, 2=AGGRESSIVE_PARALLEL
    alloc_code: int,  # 0=P1_RECOUP_FIRST, 1=P2_BALANCED_40_40_20, 2=P3_SCALE_80_20
    init_bankroll_usd: float,
    max_slots: int,
    eval_fail_cooldown_days: int,
    funded_dd_freeze_frac: float,
    enable_scaling_plan: bool,
    own_book_daily_ret: float,
    reserve_cap_tickets: float,
    recoup_cash_pct: float,
    upgrade_scale_pct: float,
    own_book_pct: float,
) -> tuple[np.ndarray, ...]:
    """Shared-Path Multi-Account Fleet Simulator (every active slot steps through exact `idx_matrix[b, d]`)."""
    n_paths, horizon = idx_matrix.shape
    n_ladder = len(ladder_tpls)
    n_firms = hazard_days.shape[1]

    # Precompute min/max ladder ticket effective fees & check if any firm hazard exists
    min_fee_day0 = 1e18
    min_fee_reg = 1e18
    top_fee_reg = 0.0
    min_rung_cap = 1e18
    for i in range(n_ladder):
        tid = ladder_tpls[i]
        ef0 = tpl_fee_day0_usd[tid] * (1.0 + tpl_card_fx_frac[tid])
        efr = tpl_fee_regular_usd[tid] * (1.0 + tpl_card_fx_frac[tid])
        if ef0 < min_fee_day0:
            min_fee_day0 = ef0
        if efr < min_fee_reg:
            min_fee_reg = efr
        if efr > top_fee_reg:
            top_fee_reg = efr
        if tpl_cap[tid] < min_rung_cap:
            min_rung_cap = tpl_cap[tid]
    reserve_cap_usd = max(min_fee_reg * 2.0, top_fee_reg * reserve_cap_tickets)

    has_any_hazard = False
    for b0 in range(n_paths):
        for f0 in range(n_firms):
            if hazard_days[b0, f0] >= 0:
                has_any_hazard = True
                break
        if has_any_hazard:
            break

    # Outputs per path
    net_24m = np.zeros(n_paths, dtype=np.float64)
    net_36m = np.zeros(n_paths, dtype=np.float64)
    wealth_24m = np.zeros(n_paths, dtype=np.float64)
    wealth_36m = np.zeros(n_paths, dtype=np.float64)
    own_book_36m = np.zeros(n_paths, dtype=np.float64)
    recoup_cash_36m = np.zeros(n_paths, dtype=np.float64)
    challenge_cash_36m = np.zeros(n_paths, dtype=np.float64)
    fees_24m = np.zeros(n_paths, dtype=np.float64)
    fees_36m = np.zeros(n_paths, dtype=np.float64)
    payouts_36m = np.zeros(n_paths, dtype=np.float64)
    refunds_36m = np.zeros(n_paths, dtype=np.float64)
    gross_payouts_36m = np.zeros(n_paths, dtype=np.float64)
    accounting_err_36m = np.zeros(n_paths, dtype=np.float64)

    ruined_ever = np.zeros(n_paths, dtype=np.int8)
    ruined_24m = np.zeros(n_paths, dtype=np.int8)
    first_ruin_day = np.full(n_paths, -1, dtype=np.int32)
    first_funded_day = np.full(n_paths, -1, dtype=np.int32)
    first_funded_breach_day = np.full(n_paths, -1, dtype=np.int32)
    first_ticket_pass_day = np.full(n_paths, -1, dtype=np.int32)
    first_ticket_fail_day = np.full(n_paths, -1, dtype=np.int32)
    pay1_day = np.full(n_paths, -1, dtype=np.int32)

    bot_kill_events = np.zeros(n_paths, dtype=np.int32)
    firm_breach_events = np.zeros(n_paths, dtype=np.int32)
    eval_breach_events = np.zeros(n_paths, dtype=np.int32)
    funded_breach_events = np.zeros(n_paths, dtype=np.int32)
    firm_breach_daily_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_maxdd_any = np.zeros(n_paths, dtype=np.int8)
    simult_fail_any = np.zeros(n_paths, dtype=np.int8)

    funded_dry_tot = np.zeros(n_paths, dtype=np.int32)
    funded_dry_zero = np.zeros(n_paths, dtype=np.int32)
    funded_max_dry_streak = np.zeros(n_paths, dtype=np.int32)

    max_base_funded_usd = np.zeros(n_paths, dtype=np.float64)
    max_scaled_funded_usd = np.zeros(n_paths, dtype=np.float64)
    scaling_upgrades_cnt = np.zeros(n_paths, dtype=np.int32)
    e1_blocks_cnt = np.zeros(n_paths, dtype=np.int32)
    e2_blocks_cnt = np.zeros(n_paths, dtype=np.int32)
    e4_blocks_cnt = np.zeros(n_paths, dtype=np.int32)
    all_fn_entries = np.zeros(n_paths, dtype=np.int32)
    all_fn_breach_12m = np.zeros(n_paths, dtype=np.int32)
    all_fn_censored_12m = np.zeros(n_paths, dtype=np.int32)

    # Reusable per-slot state arrays (L1 cache resident)
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

    # Precompute reciprocal P1/P2 targets so inner loop has zero float divisions
    n_tpl = len(tpl_cap)
    tpl_inv_p1_target = np.empty(n_tpl, dtype=np.float64)
    tpl_inv_p2_target = np.empty(n_tpl, dtype=np.float64)
    for ti in range(n_tpl):
        tpl_inv_p1_target[ti] = 1.0 / (tpl_p1_target[ti] if tpl_p1_target[ti] > 1e-6 else 1e-6)
        tpl_inv_p2_target[ti] = 1.0 / (tpl_p2_target[ti] if tpl_p2_target[ti] > 1e-6 else 1e-6)

    # Wave 4 per-slot extensions
    s_base_cap = np.zeros(max_slots, dtype=np.float64)
    s_cur_cap = np.zeros(max_slots, dtype=np.float64)
    s_inv_cur_cap = np.zeros(max_slots, dtype=np.float64)
    s_scale_mult = np.ones(max_slots, dtype=np.float64)
    s_cur_split = np.zeros(max_slots, dtype=np.float64)
    s_scale_days = np.zeros(max_slots, dtype=np.int32)
    s_scale_prof = np.zeros(max_slots, dtype=np.float64)
    s_scale_pays = np.zeros(max_slots, dtype=np.int32)
    s_fn_enter_d = np.full(max_slots, -1, dtype=np.int32)
    s_fn_12m_done = np.zeros(max_slots, dtype=np.int8)
    s_is_first_ticket = np.zeros(max_slots, dtype=np.int8)
    s_is_first_funded = np.zeros(max_slots, dtype=np.int8)

    firm_dead = np.zeros(n_firms, dtype=np.int8)
    firm_base_fn = np.zeros(n_firms, dtype=np.float64)
    firm_scaled_fn = np.zeros(n_firms, dtype=np.float64)
    firm_eval_pipe = np.zeros(n_firms, dtype=np.float64)

    # Concurrency mode parameters
    if concurrency_code == 0:  # CONSERVATIVE_1_TICKET
        max_conc_evals = 1
        first_res_mult = 3.0
        add_res_mult = 3.0
    elif concurrency_code == 1:  # GATED_STAGGER
        max_conc_evals = 2
        first_res_mult = 2.0
        add_res_mult = 2.0
    else:  # AGGRESSIVE_PARALLEL
        max_conc_evals = 3
        first_res_mult = 2.0
        add_res_mult = 1.25

    prev_used_hi = max_slots
    for b in range(n_paths):
        challenge_cash = init_bankroll_usd
        recoup_cash = 0.0
        own_book = 0.0
        recouped_so_far = 0.0

        tot_fees = 0.0
        tot_payouts = 0.0
        tot_refunds = 0.0
        tot_gross_payouts = 0.0
        tot_ob_pnl = 0.0

        for s in range(prev_used_hi):
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
            s_base_cap[s] = 0.0
            s_cur_cap[s] = 0.0
            s_inv_cur_cap[s] = 0.0
            s_scale_mult[s] = 1.0
            s_cur_split[s] = 0.80
            s_scale_days[s] = 0
            s_scale_prof[s] = 0.0
            s_scale_pays[s] = 0
            s_fn_enter_d[s] = -1
            s_fn_12m_done[s] = 0
            s_is_first_ticket[s] = 0
            s_is_first_funded[s] = 0

        for fi in range(n_firms):
            firm_dead[fi] = 0
            firm_base_fn[fi] = 0.0
            firm_scaled_fn[fi] = 0.0
            firm_eval_pipe[fi] = 0.0

        first_ticket_launched = False
        f_tk_pass = -1
        f_tk_fail = -1
        f_fn_day = -1
        f_fn_br_day = -1
        f_pay1 = -1
        f_ruin_d = -1
        had_ruin = 0
        had_ruin_24 = 0
        recorded_24 = False

        bk_ev = 0
        fb_ev = 0
        eb_ev = 0
        fnb_ev = 0
        fb_d_any = 0
        fb_m_any = 0
        sim_fail = 0

        eval_cooldown_until = -1
        e1_blk = 0
        e2_blk = 0
        e4_blk = 0
        scale_up_cnt = 0

        fn_m_days = 0
        fn_m_paid = 0
        cur_dry = 0
        best_dry = 0
        tot_fm = 0
        zero_fm = 0

        best_base_fn = 0.0
        best_scaled_fn = 0.0
        p_fn_ent = 0
        p_fn_br12 = 0
        p_fn_cens12 = 0
        used_hi = 0
        max_used_hi = 0

        # Fused fleet state counters maintained across days (avoids 2nd slot scan!)
        active_total = 0
        active_evals = 0
        active_funded = 0
        has_s2_or_s5 = False
        any_funded_in_dd_freeze = False

        for d in range(horizon):
            # 1. Firm-level exogenous disruption hazard (skipped in O(1) when 0%/yr)
            if has_any_hazard:
                haz_hit = False
                for fi in range(n_firms):
                    if firm_dead[fi] == 0 and hazard_days[b, fi] == d:
                        firm_dead[fi] = 1
                        haz_hit = True
                        for s in range(used_hi):
                            if s_stage[s] > 0 and tpl_firm_id[s_tpl[s]] == fi:
                                s_stage[s] = 0
                                s_tpl[s] = -1
                                s_bal[s] = 0.0
                                s_base_cap[s] = 0.0
                                s_cur_cap[s] = 0.0
                if haz_hit:
                    active_total = 0
                    active_evals = 0
                    active_funded = 0
                    has_s2_or_s5 = False
                    any_funded_in_dd_freeze = False
                    for fi in range(n_firms):
                        firm_base_fn[fi] = 0.0
                        firm_scaled_fn[fi] = 0.0
                        firm_eval_pipe[fi] = 0.0
                    for s in range(used_hi):
                        st0 = s_stage[s]
                        if st0 <= 0:
                            continue
                        active_total += 1
                        fid0 = tpl_firm_id[s_tpl[s]]
                        if st0 == 3:
                            active_funded += 1
                            has_s2_or_s5 = True
                            firm_base_fn[fid0] += s_base_cap[s]
                            firm_scaled_fn[fid0] += s_cur_cap[s]
                            if (s_cur_cap[s] - s_bal[s]) * s_inv_cur_cap[s] >= funded_dd_freeze_frac - 1e-12:
                                any_funded_in_dd_freeze = True
                        else:
                            active_evals += 1
                            firm_eval_pipe[fid0] += s_base_cap[s]
                            if st0 == 2:
                                has_s2_or_s5 = True

            # 2. Fleet Admission Engine (CONSERVATIVE_1_TICKET / GATED_STAGGER / AGGRESSIVE_PARALLEL)
            min_fee_now = min_fee_day0 if d == 0 else min_fee_reg
            in_e1_cooldown = d < eval_cooldown_until
            can_try_buy = (active_evals < max_conc_evals) and (challenge_cash >= min_fee_now - 1e-9)
            if can_try_buy and active_total > 0:
                if concurrency_code == 0 and (
                    active_evals > 0
                    or active_funded == 0
                    or challenge_cash < min_fee_now * add_res_mult - 1e-9
                ):
                    can_try_buy = False
                elif concurrency_code == 1 and (
                    (not has_s2_or_s5) or challenge_cash < min_fee_now * add_res_mult - 1e-9
                ):
                    can_try_buy = False
                elif concurrency_code == 2 and active_evals > 0 and challenge_cash < min_fee_now * add_res_mult - 1e-9:
                    can_try_buy = False

            if in_e1_cooldown and active_evals < max_conc_evals and challenge_cash >= min_fee_now - 1e-9:
                e1_blk += 1
            elif any_funded_in_dd_freeze and active_evals < max_conc_evals and challenge_cash >= min_fee_reg - 1e-9:
                e2_blk += 1
            elif can_try_buy:
                # O(1) single-firm E4 cap fast-skip when funded + pipeline already saturated
                e4_saturated = (
                    n_firms == 1
                    and (firm_base_fn[0] + firm_eval_pipe[0] + min_rung_cap > firm_max_funded_cap[0] + 1e-6)
                )
                if e4_saturated:
                    chk_mult = first_res_mult if active_total == 0 else add_res_mult
                    if challenge_cash >= min_fee_now * chk_mult - 1e-9:
                        e4_blk += 1
                else:
                    for s in range(max_slots):
                        if s_stage[s] != 0:
                            continue
                        if active_evals >= max_conc_evals:
                            break

                        # Enforce per-mode concurrency gate
                        allow_open = False
                        res_mult = first_res_mult
                        allow_fb_min = False

                        if active_total == 0:
                            allow_open = True
                            res_mult = first_res_mult
                            allow_fb_min = True
                        elif concurrency_code == 0:
                            # CONSERVATIVE_1_TICKET: max 1 sequential eval; upgrade when >=1 Funded + 3x reserve
                            if active_evals == 0 and active_funded >= 1:
                                allow_open = True
                                res_mult = add_res_mult
                                allow_fb_min = False
                        elif concurrency_code == 1:
                            # GATED_STAGGER: open ticket #2 only at S2 (P2) or S5 (Funded) AND cash >= 2x fee
                            if has_s2_or_s5:
                                allow_open = True
                                res_mult = add_res_mult
                                allow_fb_min = False
                        else:
                            # AGGRESSIVE_PARALLEL: open 2-3 challenges concurrently while cash & guards permit
                            allow_open = True
                            res_mult = first_res_mult if active_evals == 0 else add_res_mult
                            allow_fb_min = active_evals == 0

                        if not allow_open:
                            break

                        rung = _pick_ladder_rung(
                            challenge_cash,
                            ladder_tpls,
                            tpl_cap,
                            tpl_fee_day0_usd,
                            tpl_fee_regular_usd,
                            tpl_card_fx_frac,
                            tpl_firm_id,
                            firm_dead,
                            firm_base_fn,
                            firm_eval_pipe,
                            firm_max_funded_cap,
                            firm_max_single_challenge,
                            d,
                            res_mult,
                            allow_fb_min,
                        )
                        if rung < 0:
                            if challenge_cash >= min_fee_now * res_mult - 1e-9:
                                e4_blk += 1
                            break

                        tid = ladder_tpls[rung]
                        fid = tpl_firm_id[tid]
                        base_fee = tpl_fee_day0_usd[tid] if d == 0 else tpl_fee_regular_usd[tid]
                        ef = base_fee * (1.0 + tpl_card_fx_frac[tid])
                        if challenge_cash < ef - 1e-9:
                            break

                        challenge_cash -= ef
                        tot_fees += ef
                        cap = tpl_cap[tid]
                        _init_slot(
                            s_tpl, s_stage, s_bal, s_hwm, s_tdays, s_pdays,
                            s_cycd, s_maxg, s_ref, s_pcnt, s_fnpdays, s_paid_fee,
                            s, tid, tpl_steps[tid], cap, base_fee,
                        )
                        if s + 1 > used_hi:
                            used_hi = s + 1
                        if used_hi > max_used_hi:
                            max_used_hi = used_hi
                        s_base_cap[s] = cap
                        s_cur_cap[s] = cap
                        s_inv_cur_cap[s] = 1.0 / cap
                        s_scale_mult[s] = 1.0
                        s_cur_split[s] = tpl_split[tid]
                        s_scale_days[s] = 0
                        s_scale_prof[s] = 0.0
                        s_scale_pays[s] = 0
                        s_fn_enter_d[s] = d + 1 if tpl_steps[tid] == 0 else -1
                        s_fn_12m_done[s] = 0
                        if not first_ticket_launched:
                            first_ticket_launched = True
                            s_is_first_ticket[s] = 1
                            if tpl_steps[tid] == 0 and f_tk_pass < 0:
                                f_tk_pass = d + 1
                        else:
                            s_is_first_ticket[s] = 0
                        if tpl_steps[tid] == 0:
                            p_fn_ent += 1
                            if f_fn_day < 0:
                                f_fn_day = d + 1
                                s_is_first_funded[s] = 1
                            else:
                                s_is_first_funded[s] = 0
                            active_funded += 1
                            has_s2_or_s5 = True
                            firm_base_fn[fid] += cap
                            firm_scaled_fn[fid] += cap
                        else:
                            s_is_first_funded[s] = 0
                            active_evals += 1
                            firm_eval_pipe[fid] += cap
                        active_total += 1

            # 3. Check true bankroll ruin & early-exit absorbing state (zero active slots, cannot re-enter)
            if active_total == 0:
                total_liq_now = challenge_cash + recoup_cash + own_book
                if (not in_e1_cooldown) and total_liq_now < min_fee_now - 1e-9:
                    had_ruin = 1
                    if f_ruin_d < 0:
                        f_ruin_d = d + 1
                    if d < 504:
                        had_ruin_24 = 1
                if (not in_e1_cooldown) and challenge_cash < min_fee_reg - 1e-9 and (
                    own_book_daily_ret == 0.0 or own_book <= 0.0
                ):
                    break

            # 4. SHARED MARKET PATH STEP: ALL active accounts use the EXACT SAME `src = idx_matrix[b, d]`!
            src = idx_matrix[b, d]
            fails_today = 0
            any_funded_today = 0
            paid_today = 0
            tot_base_fn_today = 0.0
            tot_scaled_fn_today = 0.0

            next_active_total = 0
            next_active_evals = 0
            next_active_funded = 0
            next_has_s2_or_s5 = False
            next_any_funded_dd = False
            for fi in range(n_firms):
                firm_base_fn[fi] = 0.0
                firm_scaled_fn[fi] = 0.0
                firm_eval_pipe[fi] = 0.0

            for s in range(used_hi):
                st = s_stage[s]
                if st <= 0:
                    continue
                tid = s_tpl[s]
                fid = tpl_firm_id[tid]
                base_cap = s_base_cap[s]
                cur_cap = s_cur_cap[s]
                inv_cur_cap = s_inv_cur_cap[s]
                scale_mult = s_scale_mult[s]

                if st == 3:
                    any_funded_today = 1
                    tot_base_fn_today += base_cap
                    tot_scaled_fn_today += cur_cap

                eq_pct = (s_bal[s] - cur_cap) * inv_cur_cap
                if eq_pct <= -tpl_red_dd[tid]:
                    net_raw, dd_raw, up_raw, flg = (
                        tpl_n_red[tid, src], tpl_d_red[tid, src], tpl_u_red[tid, src], tpl_f_red[tid, src],
                    )
                    ea_daily_pct = (
                        tpl_fn_ea_stop[tid] if st == 3 else (tpl_p2_ea_stop[tid] if st == 2 else tpl_p1_ea_stop[tid])
                    )
                    ea_static_pct = (
                        tpl_fn_ea_static_stop[tid]
                        if st == 3
                        else (tpl_p2_ea_static_stop[tid] if st == 2 else tpl_p1_ea_static_stop[tid])
                    )
                elif eq_pct <= -tpl_amber_dd[tid]:
                    net_raw, dd_raw, up_raw, flg = (
                        tpl_n_amb[tid, src], tpl_d_amb[tid, src], tpl_u_amb[tid, src], tpl_f_amb[tid, src],
                    )
                    ea_daily_pct = (
                        tpl_fn_ea_stop[tid] if st == 3 else (tpl_p2_ea_stop[tid] if st == 2 else tpl_p1_ea_stop[tid])
                    )
                    ea_static_pct = (
                        tpl_fn_ea_static_stop[tid]
                        if st == 3
                        else (tpl_p2_ea_static_stop[tid] if st == 2 else tpl_p1_ea_static_stop[tid])
                    )
                elif st == 1:
                    prog = eq_pct * tpl_inv_p1_target[tid]
                    if tpl_p1_lock_trig[tid] > 0.0 and prog >= tpl_p1_lock_trig[tid]:
                        net_raw, dd_raw, up_raw, flg = (
                            tpl_n_p1l[tid, src], tpl_d_p1l[tid, src], tpl_u_p1l[tid, src], tpl_f_p1l[tid, src],
                        )
                    else:
                        net_raw, dd_raw, up_raw, flg = (
                            tpl_n_p1[tid, src], tpl_d_p1[tid, src], tpl_u_p1[tid, src], tpl_f_p1[tid, src],
                        )
                    ea_daily_pct = tpl_p1_ea_stop[tid]
                    ea_static_pct = tpl_p1_ea_static_stop[tid]
                elif st == 2:
                    prog = eq_pct * tpl_inv_p2_target[tid]
                    if tpl_p2_lock_trig[tid] > 0.0 and prog >= tpl_p2_lock_trig[tid]:
                        net_raw, dd_raw, up_raw, flg = (
                            tpl_n_p2l[tid, src], tpl_d_p2l[tid, src], tpl_u_p2l[tid, src], tpl_f_p2l[tid, src],
                        )
                    else:
                        net_raw, dd_raw, up_raw, flg = (
                            tpl_n_p2[tid, src], tpl_d_p2[tid, src], tpl_u_p2[tid, src], tpl_f_p2[tid, src],
                        )
                    ea_daily_pct = tpl_p2_ea_stop[tid]
                    ea_static_pct = tpl_p2_ea_static_stop[tid]
                else:
                    net_raw, dd_raw, up_raw, flg = (
                        tpl_n_fn[tid, src], tpl_d_fn[tid, src], tpl_u_fn[tid, src], tpl_f_fn[tid, src],
                    )
                    ea_daily_pct = tpl_fn_ea_stop[tid]
                    ea_static_pct = tpl_fn_ea_static_stop[tid]

                # Scale UP only when FTMO Scaling Plan grew this slot above its base SKU capital (scale_mult >= 1.0)
                net = net_raw * scale_mult
                dd = dd_raw * scale_mult
                up = up_raw * scale_mult

                # Firm hard DD floors (checked BEFORE EA stop — Bug A invariant!)
                dd_t = tpl_dd_type[tid]
                if dd_t == 2:
                    if s_bal[s] + up > s_hwm[s]:
                        s_hwm[s] = s_bal[s] + up
                    max_floor = s_hwm[s] * (1.0 - tpl_max_dd_lim[tid])
                elif dd_t == 1:
                    max_floor = s_hwm[s] * (1.0 - tpl_max_dd_lim[tid])
                else:
                    if tpl_lock_init_p1[tid] == 1 and st == 3 and s_pcnt[s] >= 1:
                        max_floor = cur_cap
                    else:
                        max_floor = cur_cap * (1.0 - tpl_max_dd_lim[tid])

                if tpl_daily_dd_anchor[tid] == 1:
                    daily_floor = s_bal[s] * (1.0 - tpl_daily_lim[tid])
                else:
                    daily_floor = s_bal[s] - cur_cap * tpl_daily_lim[tid]

                day_min = s_bal[s] - dd
                d_hit = day_min < daily_floor - 1e-9
                m_hit = day_min < max_floor - 1e-9

                # Separate BOT_AUTO_KILL (EA internal brake) vs FIRM_HARD_BREACH (Law 13)
                ea_daily_cut = cur_cap * ea_daily_pct if ea_daily_pct > 0.0 else 1e18
                ea_static_floor = cur_cap * (1.0 - ea_static_pct) if ea_static_pct > 0.0 else -1e18
                if (not d_hit) and (not m_hit):
                    daily_kill = dd > ea_daily_cut
                    static_kill = (s_bal[s] > ea_static_floor + 1e-9) and (day_min < ea_static_floor - 1e-9)
                    if daily_kill or static_kill:
                        bk_ev += 1
                        dd_eff = dd
                        if daily_kill:
                            cand_d = ea_daily_cut + cur_cap * 0.0020
                            if cand_d < dd_eff:
                                dd_eff = cand_d
                        if static_kill:
                            cand_s = (s_bal[s] - ea_static_floor) + cur_cap * 0.0020
                            if cand_s < 0.0:
                                cand_s = 0.0
                            if cand_s < dd_eff:
                                dd_eff = cand_s
                        net = min(net, -dd_eff)
                        day_min_eff = s_bal[s] - dd_eff
                        d_hit = day_min_eff < daily_floor - 1e-9
                        m_hit = day_min_eff < max_floor - 1e-9

                if d_hit or m_hit:
                    fails_today += 1
                    fb_ev += 1
                    if d_hit:
                        fb_d_any = 1
                    if m_hit:
                        fb_m_any = 1
                    if st < 3:
                        eb_ev += 1
                        # Guard E1: activate cooldown after Eval breach
                        if eval_fail_cooldown_days > 0:
                            cd_target = d + 1 + eval_fail_cooldown_days
                            if cd_target > eval_cooldown_until:
                                eval_cooldown_until = cd_target
                        if s_is_first_ticket[s] == 1 and f_tk_fail < 0 and f_tk_pass < 0:
                            f_tk_fail = d + 1
                    else:
                        fnb_ev += 1
                        if s_is_first_funded[s] == 1 and f_fn_br_day < 0:
                            f_fn_br_day = d + 1
                        if s_fn_12m_done[s] == 0 and s_fn_enter_d[s] >= 0:
                            if (d + 1 - s_fn_enter_d[s]) <= 252:
                                p_fn_br12 += 1
                            s_fn_12m_done[s] = 1
                    s_stage[s] = 0
                    s_tpl[s] = -1
                    s_bal[s] = 0.0
                    s_paid_fee[s] = 0.0
                    s_base_cap[s] = 0.0
                    s_cur_cap[s] = 0.0
                    s_is_first_ticket[s] = 0
                    s_is_first_funded[s] = 0
                    continue

                # Apply day PnL
                if tpl_daily_prof_cap_pct[tid] > 0.0 and net > cur_cap * tpl_daily_prof_cap_pct[tid]:
                    net = cur_cap * tpl_daily_prof_cap_pct[tid]
                s_bal[s] += net
                if dd_t == 1 and s_bal[s] > s_hwm[s]:
                    s_hwm[s] = s_bal[s]
                if net > s_maxg[s]:
                    s_maxg[s] = net
                if flg != 0:
                    s_tdays[s] += 1
                if tpl_min_prof_pct[tid] > 0.0 and net >= cur_cap * tpl_min_prof_pct[tid] - 1e-9:
                    s_pdays[s] += 1

                # Phase transitions (S1 -> S2/S3 -> S4/S5 -> S6/S7)
                if st == 1:
                    ok_t = s_bal[s] >= cur_cap * (1.0 + tpl_p1_target[tid]) - 1e-9
                    ok_d = (s_tdays[s] >= tpl_min_days[tid]) and (s_pdays[s] >= tpl_min_prof_days[tid])
                    ok_c = True
                    if tpl_best_day_cap[tid] > 0.0:
                        pr = s_bal[s] - cur_cap
                        if pr <= 0.0 or s_maxg[s] > tpl_best_day_cap[tid] * pr + 1e-9:
                            ok_c = False
                    if ok_t and ok_d and ok_c:
                        if tpl_steps[tid] == 1:
                            # Guard E4 check at Funded graduation
                            cur_f_base = 0.0
                            for s2 in range(used_hi):
                                if s_stage[s2] == 3 and tpl_firm_id[s_tpl[s2]] == fid:
                                    cur_f_base += s_base_cap[s2]
                            if cur_f_base + base_cap <= firm_max_funded_cap[fid] + 1e-6:
                                s_stage[s] = 3
                                s_bal[s] = cur_cap
                                s_hwm[s] = cur_cap
                                s_tdays[s] = 0
                                s_pdays[s] = 0
                                s_cycd[s] = 0
                                s_maxg[s] = 0.0
                                s_fn_enter_d[s] = d + 1
                                s_fn_12m_done[s] = 0
                                p_fn_ent += 1
                                if s_is_first_ticket[s] == 1 and f_tk_pass < 0:
                                    f_tk_pass = d + 1
                                if f_fn_day < 0:
                                    f_fn_day = d + 1
                                    s_is_first_funded[s] = 1
                        else:
                            s_stage[s] = 2
                            s_bal[s] = cur_cap
                            s_hwm[s] = cur_cap
                            s_tdays[s] = 0
                            s_pdays[s] = 0
                            s_maxg[s] = 0.0
                elif st == 2:
                    ok_t = s_bal[s] >= cur_cap * (1.0 + tpl_p2_target[tid]) - 1e-9
                    ok_d = (s_tdays[s] >= tpl_min_days[tid]) and (s_pdays[s] >= tpl_min_prof_days[tid])
                    if ok_t and ok_d:
                        cur_f_base = 0.0
                        for s2 in range(used_hi):
                            if s_stage[s2] == 3 and tpl_firm_id[s_tpl[s2]] == fid:
                                cur_f_base += s_base_cap[s2]
                        if cur_f_base + base_cap <= firm_max_funded_cap[fid] + 1e-6:
                            s_stage[s] = 3
                            s_bal[s] = cur_cap
                            s_hwm[s] = cur_cap
                            s_tdays[s] = 0
                            s_pdays[s] = 0
                            s_cycd[s] = 0
                            s_maxg[s] = 0.0
                            s_scale_days[s] = 0
                            s_scale_prof[s] = 0.0
                            s_scale_pays[s] = 0
                            s_fn_enter_d[s] = d + 1
                            s_fn_12m_done[s] = 0
                            p_fn_ent += 1
                            if s_is_first_ticket[s] == 1 and f_tk_pass < 0:
                                f_tk_pass = d + 1
                            if f_fn_day < 0:
                                f_fn_day = d + 1
                                s_is_first_funded[s] = 1
                elif st == 3:
                    s_cycd[s] += 1
                    s_scale_days[s] += 1
                    s_scale_prof[s] += net
                    if s_fn_12m_done[s] == 0 and s_fn_enter_d[s] >= 0 and (d + 1 - s_fn_enter_d[s]) >= 252:
                        s_fn_12m_done[s] = 1
                    if tpl_fn_p1_prof_pct[tid] > 0.0 and net >= cur_cap * tpl_fn_p1_prof_pct[tid] - 1e-9:
                        s_fnpdays[s] += 1

                    # S6 Payout Audit & Harvest + S7 After-Payout 3-Bucket Allocator
                    if s_cycd[s] >= tpl_payout_cycle[tid]:
                        prof = s_bal[s] - cur_cap
                        ok_c = True
                        if tpl_best_day_cap[tid] > 0.0 and prof > 0.0:
                            if s_maxg[s] > tpl_best_day_cap[tid] * prof + 1e-9:
                                ok_c = False
                        if s_pcnt[s] == 0 and tpl_fn_p1_prof_days[tid] > 0:
                            if s_fnpdays[s] < tpl_fn_p1_prof_days[tid]:
                                ok_c = False
                        if tpl_min_pay_prof_pct[tid] > 0.0 and prof < cur_cap * tpl_min_pay_prof_pct[tid] - 1e-9:
                            ok_c = False
                        if prof > 1e-6 and ok_c:
                            buf_ret = tpl_buf_ret_pct[tid]
                            gross_share = prof * (1.0 - buf_ret) * s_cur_split[s]
                            if gross_share >= tpl_min_payout[tid] - 1e-9:
                                s_pcnt[s] += 1
                                s_scale_pays[s] += 1
                                tot_gross_payouts += prof * (1.0 - buf_ret)
                                net_payout_in = gross_share * (1.0 - tpl_wd_fee_pct[tid])
                                tot_payouts += net_payout_in
                                refund_in = 0.0
                                if (
                                    s_ref[s] == 0
                                    and tpl_refund_pct[tid] > 0.0
                                    and tpl_refund_milestone[tid] > 0
                                    and s_pcnt[s] >= tpl_refund_milestone[tid]
                                ):
                                    refund_in = (
                                        s_paid_fee[s]
                                        * tpl_refund_pct[tid]
                                        * (1.0 - tpl_refund_wd_fee_pct[tid])
                                    )
                                    tot_refunds += refund_in
                                    s_ref[s] = 1

                                total_in = net_payout_in + refund_in
                                paid_today = 1
                                if f_pay1 < 0:
                                    f_pay1 = d + 1

                                # S7 After-Payout Allocation (P1 / P2 / P3)
                                if alloc_code == 0:
                                    # P1_RECOUP_FIRST: 100% recoups initial bankroll; then 50% Upgrade / 50% Own-Book
                                    shortfall = init_bankroll_usd - recouped_so_far
                                    if shortfall < 0.0:
                                        shortfall = 0.0
                                    to_recoup = total_in if total_in <= shortfall else shortfall
                                    recoup_cash += to_recoup
                                    recouped_so_far += to_recoup
                                    rem = total_in - to_recoup
                                    if rem > 0.0:
                                        to_up = rem * upgrade_scale_pct
                                        to_ob = rem * own_book_pct
                                        room = reserve_cap_usd - challenge_cash
                                        if room < 0.0:
                                            room = 0.0
                                        add_ch = to_up if to_up <= room else room
                                        challenge_cash += add_ch
                                        own_book += to_ob + (to_up - add_ch)
                                else:
                                    # P2_BALANCED_40_40_20 or P3_SCALE_80_20
                                    to_rec = total_in * recoup_cash_pct
                                    to_up = total_in * upgrade_scale_pct
                                    to_ob = total_in * own_book_pct
                                    recoup_cash += to_rec
                                    recouped_so_far += to_rec
                                    room = reserve_cap_usd - challenge_cash
                                    if room < 0.0:
                                        room = 0.0
                                    add_ch = to_up if to_up <= room else room
                                    challenge_cash += add_ch
                                    own_book += to_ob + (to_up - add_ch)

                                s_bal[s] = cur_cap + prof * buf_ret
                                s_hwm[s] = s_bal[s]
                                s_maxg[s] = 0.0
                        s_cycd[s] = 0

                    # FTMO Scaling Plan (+25% every 4m = 84d, >=10% prof, >=2 payouts, up to $2M, 80%->90%)
                    if enable_scaling_plan and s_scale_days[s] >= FTMO_SCALING_INTERVAL_TRADING_DAYS:
                        if (
                            s_scale_prof[s] >= cur_cap * FTMO_SCALING_MIN_PROFIT_FRAC - 1e-9
                            and s_scale_pays[s] >= FTMO_SCALING_MIN_PAYOUTS
                            and s_bal[s] >= cur_cap - 1e-9
                        ):
                            cur_firm_scaled = 0.0
                            for s2 in range(used_hi):
                                if s_stage[s2] == 3 and tpl_firm_id[s_tpl[s2]] == fid:
                                    cur_firm_scaled += s_cur_cap[s2]
                            add_cap = base_cap * FTMO_SCALING_STEP_FRAC
                            max_room = firm_max_scaled_cap[fid] - cur_firm_scaled
                            if max_room < 0.0:
                                max_room = 0.0
                            if add_cap > max_room:
                                add_cap = max_room
                            if add_cap > 1e-6:
                                new_cap = cur_cap + add_cap
                                s_cur_cap[s] = new_cap
                                s_inv_cur_cap[s] = 1.0 / new_cap
                                s_scale_mult[s] = new_cap / base_cap
                                s_bal[s] = s_bal[s] + add_cap
                                if s_hwm[s] + add_cap > s_bal[s]:
                                    s_hwm[s] = s_hwm[s] + add_cap
                                else:
                                    s_hwm[s] = s_bal[s]
                                s_cur_split[s] = tpl_split_max[tid]
                                scale_up_cnt += 1
                        s_scale_days[s] = 0
                        s_scale_prof[s] = 0.0
                        s_scale_pays[s] = 0

                # Update next-day fused fleet counters directly in the same single pass
                st_end = s_stage[s]
                if st_end > 0:
                    next_active_total += 1
                    if st_end == 3:
                        next_active_funded += 1
                        next_has_s2_or_s5 = True
                        firm_base_fn[fid] += s_base_cap[s]
                        firm_scaled_fn[fid] += s_cur_cap[s]
                        if (s_cur_cap[s] - s_bal[s]) * s_inv_cur_cap[s] >= funded_dd_freeze_frac - 1e-12:
                            next_any_funded_dd = True
                    else:
                        next_active_evals += 1
                        firm_eval_pipe[fid] += s_base_cap[s]
                        if st_end == 2:
                            next_has_s2_or_s5 = True

            active_total = next_active_total
            active_evals = next_active_evals
            active_funded = next_active_funded
            has_s2_or_s5 = next_has_s2_or_s5
            any_funded_in_dd_freeze = next_any_funded_dd
            while used_hi > 0 and s_stage[used_hi - 1] <= 0:
                used_hi -= 1

            if fails_today >= 2:
                sim_fail = 1
            if tot_base_fn_today > best_base_fn:
                best_base_fn = tot_base_fn_today
            if tot_scaled_fn_today > best_scaled_fn:
                best_scaled_fn = tot_scaled_fn_today

            # Funded dry-month / starved-month streak tracker
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

            # Conservative Own-Book compounding (default 0.0%)
            if own_book > 0.0 and own_book_daily_ret != 0.0:
                ob_gain = own_book * own_book_daily_ret
                own_book += ob_gain
                tot_ob_pnl += ob_gain

            if (not recorded_24) and (d + 1 == 504):
                w24 = challenge_cash + recoup_cash + own_book
                wealth_24m[b] = w24
                net_24m[b] = w24 - init_bankroll_usd
                fees_24m[b] = tot_fees
                recorded_24 = True

        prev_used_hi = max_used_hi
        # Count remaining active Funded slots censored (< 252 trading days observed)
        for s in range(used_hi):
            if s_stage[s] == 3 and s_fn_12m_done[s] == 0 and s_fn_enter_d[s] >= 0:
                if (horizon - s_fn_enter_d[s]) < 252:
                    p_fn_cens12 += 1

        w_end = challenge_cash + recoup_cash + own_book
        if not recorded_24:
            wealth_24m[b] = w_end
            net_24m[b] = w_end - init_bankroll_usd
            fees_24m[b] = tot_fees

        wealth_36m[b] = w_end
        net_36m[b] = w_end - init_bankroll_usd
        own_book_36m[b] = own_book
        recoup_cash_36m[b] = recoup_cash
        challenge_cash_36m[b] = challenge_cash
        fees_36m[b] = tot_fees
        payouts_36m[b] = tot_payouts
        refunds_36m[b] = tot_refunds
        gross_payouts_36m[b] = tot_gross_payouts

        # Exact cash conservation check (strictly excludes Funded notional!)
        expected_w = init_bankroll_usd - tot_fees + tot_payouts + tot_refunds + tot_ob_pnl
        accounting_err_36m[b] = abs(w_end - expected_w)

        ruined_ever[b] = had_ruin
        ruined_24m[b] = had_ruin_24
        first_ruin_day[b] = f_ruin_d
        first_funded_day[b] = f_fn_day
        first_funded_breach_day[b] = f_fn_br_day
        first_ticket_pass_day[b] = f_tk_pass
        first_ticket_fail_day[b] = f_tk_fail
        pay1_day[b] = f_pay1

        bot_kill_events[b] = bk_ev
        firm_breach_events[b] = fb_ev
        eval_breach_events[b] = eb_ev
        funded_breach_events[b] = fnb_ev
        firm_breach_daily_any[b] = fb_d_any
        firm_breach_maxdd_any[b] = fb_m_any
        simult_fail_any[b] = sim_fail

        funded_dry_tot[b] = tot_fm
        funded_dry_zero[b] = zero_fm
        funded_max_dry_streak[b] = best_dry

        max_base_funded_usd[b] = best_base_fn
        max_scaled_funded_usd[b] = best_scaled_fn
        scaling_upgrades_cnt[b] = scale_up_cnt
        e1_blocks_cnt[b] = e1_blk
        e2_blocks_cnt[b] = e2_blk
        e4_blocks_cnt[b] = e4_blk
        all_fn_entries[b] = p_fn_ent
        all_fn_breach_12m[b] = p_fn_br12
        all_fn_censored_12m[b] = p_fn_cens12

    return (
        net_24m,
        net_36m,
        wealth_24m,
        wealth_36m,
        own_book_36m,
        recoup_cash_36m,
        challenge_cash_36m,
        fees_24m,
        fees_36m,
        payouts_36m,
        refunds_36m,
        gross_payouts_36m,
        accounting_err_36m,
        ruined_ever,
        ruined_24m,
        first_ruin_day,
        first_funded_day,
        first_funded_breach_day,
        first_ticket_pass_day,
        first_ticket_fail_day,
        pay1_day,
        bot_kill_events,
        firm_breach_events,
        eval_breach_events,
        funded_breach_events,
        firm_breach_daily_any,
        firm_breach_maxdd_any,
        simult_fail_any,
        funded_dry_tot,
        funded_dry_zero,
        funded_max_dry_streak,
        max_base_funded_usd,
        max_scaled_funded_usd,
        scaling_upgrades_cnt,
        e1_blocks_cnt,
        e2_blocks_cnt,
        e4_blocks_cnt,
        all_fn_entries,
        all_fn_breach_12m,
        all_fn_censored_12m,
    )


# ---------------------------------------------------------------------------
# Shared-Path Correlation Proof Helper (Shared vs Independent Negative Mutation)
# ---------------------------------------------------------------------------


def measure_shared_path_daily_correlation(
    *,
    daily_net_acct_a: np.ndarray,
    daily_net_acct_b: np.ndarray,
    n_paths: int = 200,
    horizon_days: int = 252,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
    shared_path: bool = True,
) -> dict[str, Any]:
    """Measure daily PnL correlation between 2 parallel accounts running the same bot.

    - `shared_path=True` (production invariant): both accounts step on identical `idx_a == idx_b` -> `rho > 0.95`.
    - `shared_path=False` (negative mutation test hook ONLY): independent bootstrap draws -> `rho ~ 0.0`.
    """
    a = np.asarray(daily_net_acct_a, dtype=np.float64)
    b = np.asarray(daily_net_acct_b, dtype=np.float64)
    if a.ndim != 1 or b.ndim != 1 or len(a) != len(b) or len(a) < 5:
        raise ValueError("daily_net arrays must be 1-D of equal length >= 5")
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise ValueError("NON_FINITE_INPUT: daily_net arrays contain NaN/Inf")

    idx_a = make_block_bootstrap_indices(len(a), horizon=horizon_days, n_paths=n_paths, block_len=block_len, seed=seed)
    idx_b = (
        idx_a
        if shared_path
        else make_block_bootstrap_indices(
            len(b), horizon=horizon_days, n_paths=n_paths, block_len=block_len, seed=seed + 99991
        )
    )

    pnl_a = a[idx_a]
    pnl_b = b[idx_b]
    corrs: list[float] = []
    for i in range(n_paths):
        xa = pnl_a[i]
        xb = pnl_b[i]
        sa = float(np.std(xa))
        sb = float(np.std(xb))
        if sa > 1e-12 and sb > 1e-12:
            corrs.append(float(np.corrcoef(xa, xb)[0, 1]))
    mean_rho = float(np.mean(corrs)) if corrs else 0.0
    min_rho = float(np.min(corrs)) if corrs else 0.0
    max_rho = float(np.max(corrs)) if corrs else 0.0
    return {
        "shared_path": bool(shared_path),
        "n_paths": int(n_paths),
        "horizon_days": int(horizon_days),
        "mean_daily_pnl_rho": round(mean_rho, 6),
        "min_daily_pnl_rho": round(min_rho, 6),
        "max_daily_pnl_rho": round(max_rho, 6),
    }


def trace_two_parallel_accounts_shared_path(
    *,
    template_a: dict[str, Any],
    template_b: dict[str, Any],
    n_paths: int = 100,
    horizon_days: int = 252,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
    shared_path: bool = True,
) -> dict[str, Any]:
    """Trace two concurrent accounts (A & B) stepping through Funded/Amber/Red dynamics.

    Proves end-to-end inside account equity/brake state mechanics that:
      - `shared_path=True` (production invariant): both accounts share `src = idx[b, d]` -> `rho > 0.95`.
      - `shared_path=False` (negative mutation test ONLY): independent draws -> `rho ~ 0.0`.
    """
    st_a = template_a["stage_arrays"]
    st_b = template_b["stage_arrays"]
    n_obs = len(st_a[16])
    if len(st_b[16]) != n_obs or n_obs < 5:
        raise ValueError("Template stage_arrays must have equal length >= 5")

    idx_a = make_block_bootstrap_indices(n_obs, horizon=horizon_days, n_paths=n_paths, block_len=block_len, seed=seed)
    idx_b = (
        idx_a
        if shared_path
        else make_block_bootstrap_indices(
            n_obs, horizon=horizon_days, n_paths=n_paths, block_len=block_len, seed=seed + 77773
        )
    )

    cap_a = float(template_a["capital_usd"])
    cap_b = float(template_b["capital_usd"])
    amb_a, red_a = float(template_a["amber_dd"]), float(template_a["red_dd"])
    amb_b, red_b = float(template_b["amber_dd"]), float(template_b["red_dd"])

    corrs: list[float] = []
    for p in range(n_paths):
        bal_a, bal_b = cap_a, cap_b
        dp_a = np.zeros(horizon_days, dtype=np.float64)
        dp_b = np.zeros(horizon_days, dtype=np.float64)
        for d in range(horizon_days):
            sa = int(idx_a[p, d])
            sb = int(idx_b[p, d])
            eq_a = (bal_a - cap_a) / cap_a
            eq_b = (bal_b - cap_b) / cap_b
            na = float(st_a[24][sa] if eq_a <= -red_a else (st_a[20][sa] if eq_a <= -amb_a else st_a[16][sa]))
            nb = float(st_b[24][sb] if eq_b <= -red_b else (st_b[20][sb] if eq_b <= -amb_b else st_b[16][sb]))
            bal_a += na
            bal_b += nb
            dp_a[d] = na / cap_a
            dp_b[d] = nb / cap_b
        if float(np.std(dp_a)) > 1e-12 and float(np.std(dp_b)) > 1e-12:
            corrs.append(float(np.corrcoef(dp_a, dp_b)[0, 1]))

    mean_rho = float(np.mean(corrs)) if corrs else 0.0
    return {
        "shared_path": bool(shared_path),
        "acct_a": str(template_a.get("contract_id", "A")),
        "acct_b": str(template_b.get("contract_id", "B")),
        "n_paths": int(n_paths),
        "horizon_days": int(horizon_days),
        "mean_daily_pnl_rho": round(mean_rho, 6),
        "min_daily_pnl_rho": round(float(np.min(corrs)) if corrs else 0.0, 6),
    }


# ---------------------------------------------------------------------------
# Law 13–15 Balanced Summarizer & Pareto Frontier Extractor
# ---------------------------------------------------------------------------


def _exact_partition_pcts(n_pass: int, n_fail: int, n_total: int) -> dict[str, float]:
    """Return rounded `pass_pct`, `fail_pct`, `pending_pct` guaranteed to sum to exact `100.0`."""
    if n_total <= 0:
        return {"pass_pct": 0.0, "fail_pct": 0.0, "pending_pct": 100.0, "sum_pct": 100.0}
    p = round(100.0 * n_pass / n_total, 2)
    f = round(100.0 * n_fail / n_total, 2)
    w = round(100.0 - p - f, 2)
    if w < 0.0 and w > -0.05:
        w = 0.0
        f = round(100.0 - p, 2)
    return {
        "pass_pct": p,
        "fail_pct": f,
        "pending_pct": w,
        "sum_pct": round(p + f + w, 2),
    }


def _classify_law15_prop_tier(
    *,
    ev_per_fee: float,
    funded_12m_blowup_pct: float,
    p_ruin_pct: float,
    uncond_med_pay1_days: float,
) -> dict[str, str]:
    """Tier-1 (Single CFD Prop Bot) Law-15 `Xấu -> Đủ dùng -> Tốt -> Top 1%` positioning."""
    if ev_per_fee <= 0.0 or funded_12m_blowup_pct > 5.0 or p_ruin_pct >= 25.0:
        tier = "XAU"
        tier_vi = "Xấu"
        gap = "Cần đưa EV/phí > +1x, cháy Funded 12T < 5% và giảm xác suất cháy quỹ vé."
    elif ev_per_fee < 3.0 or funded_12m_blowup_pct >= 1.0 or p_ruin_pct >= 5.0:
        tier = "DU_DUNG"
        tier_vi = "Đủ dùng"
        gap = "Để lên Tốt/Top 1%: EV/phí >= +3x..+5x, cháy Funded 12T < 1% và ruin < 1%."
    elif ev_per_fee >= 5.0 and funded_12m_blowup_pct < 1.0 and p_ruin_pct < 1.0 and uncond_med_pay1_days <= 120.0:
        tier = "TOP_1_PCT"
        tier_vi = "Top 1% thực tế (Tầng 1 CFD Prop)"
        gap = "Đạt chuẩn Top 1% mô phỏng Dev; cần xác nhận bằng bằng chứng Demo/Live thực tế."
    else:
        tier = "TOT"
        tier_vi = "Tốt"
        gap = "Cần rút ngắn thời gian tới Payout #1 (2-4 tháng) và nâng EV/phí >= +5x với ruin < 1%."
    return {
        "domain_tier": "TIER_1_SINGLE_CFD_PROP_BOT",
        "grade_code": tier,
        "grade_vi": tier_vi,
        "gap_to_top_1_pct_vi": gap,
    }


def summarize_pareto_case(
    case_cfg: ParetoCaseConfig,
    raw_res: tuple[np.ndarray, ...],
    *,
    horizon_days: int,
    execution_status: str,
    pricing_regime: str,
    reference_ticket_usd: float,
    strategy_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute complete Law 13–15 balanced metrics for one case of the 81-case Pareto grid."""
    (
        net_24m,
        net_36m,
        wealth_24m,
        wealth_36m,
        own_book_36m,
        recoup_cash_36m,
        challenge_cash_36m,
        fees_24m,
        fees_36m,
        payouts_36m,
        refunds_36m,
        gross_payouts_36m,
        accounting_err_36m,
        ruined_ever,
        ruined_24m,
        first_ruin_day,
        first_funded_day,
        first_funded_breach_day,
        first_ticket_pass_day,
        first_ticket_fail_day,
        pay1_day,
        bot_kill_events,
        firm_breach_events,
        eval_breach_events,
        funded_breach_events,
        firm_breach_daily_any,
        firm_breach_maxdd_any,
        simult_fail_any,
        funded_dry_tot,
        funded_dry_zero,
        funded_max_dry_streak,
        max_base_funded_usd,
        max_scaled_funded_usd,
        scaling_upgrades_cnt,
        e1_blocks_cnt,
        e2_blocks_cnt,
        e4_blocks_cnt,
        all_fn_entries,
        all_fn_breach_12m,
        all_fn_censored_12m,
    ) = raw_res

    n = len(net_36m)
    fx = case_cfg.usd_vnd_rate

    # 1. Exact Pass / Fail / Pending partitions (sum == 100.0%) at 3m/6m/12m/24m/36m
    fleet_horizons: dict[str, dict[str, float]] = {}
    first_ticket_horizons: dict[str, dict[str, float]] = {}
    for m in HORIZON_MONTHS:
        cutoff = m * TRADING_DAYS_PER_MONTH
        if cutoff > horizon_days:
            continue
        f_passed = (first_funded_day >= 0) & (first_funded_day <= cutoff)
        f_failed = (~f_passed) & (first_ruin_day > 0) & (first_ruin_day <= cutoff)
        fleet_horizons[f"{m}m"] = _exact_partition_pcts(int(np.sum(f_passed)), int(np.sum(f_failed)), n)

        t_passed = (first_ticket_pass_day >= 0) & (first_ticket_pass_day <= cutoff)
        t_failed = (~t_passed) & (first_ticket_fail_day > 0) & (first_ticket_fail_day <= cutoff)
        first_ticket_horizons[f"{m}m"] = _exact_partition_pcts(int(np.sum(t_passed)), int(np.sum(t_failed)), n)

    # 2. 12m Funded blowup rate + Wilson 95% UB (path-level independent cohort + fleet total disclosure)
    entered_mask = first_funded_day >= 0
    n_paths_entered = int(np.sum(entered_mask))
    if n_paths_entered > 0:
        fn_ent_d = first_funded_day[entered_mask]
        fn_br_d = first_funded_breach_day[entered_mask]
        br_12m_mask = (fn_br_d > 0) & ((fn_br_d - fn_ent_d) <= TRADING_DAYS_PER_YEAR)
        full_12m_mask = (fn_ent_d + TRADING_DAYS_PER_YEAR) <= horizon_days
        n_br_12m = int(np.sum(br_12m_mask))
        n_cens_12m = int(np.sum(~full_12m_mask))
        n_full_12m = int(np.sum(full_12m_mask))
        fn_blowup_12m_pct = 100.0 * n_br_12m / n_paths_entered
        fn_blowup_uncens_pct = (
            (100.0 * int(np.sum(br_12m_mask & full_12m_mask)) / n_full_12m) if n_full_12m > 0 else 0.0
        )
        wilson_ub_pct = 100.0 * wilson_upper_95(n_br_12m, n_paths_entered)
    else:
        n_br_12m = 0
        n_cens_12m = 0
        n_full_12m = 0
        fn_blowup_12m_pct = 0.0
        fn_blowup_uncens_pct = 0.0
        wilson_ub_pct = 100.0

    # 3. Calendar days to Payout #1 (unconditional with 365d & 730d censoring)
    paid_mask = pay1_day > 0
    cal_pay1 = np.where(paid_mask, pay1_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    uncond_cap365 = np.minimum(cal_pay1, 365.0)
    uncond_cap730 = np.minimum(cal_pay1, 730.0)
    uncond_med_365 = float(np.median(uncond_cap365))
    uncond_med_730 = float(np.median(uncond_cap730))
    cond_med_pay1 = float(np.median(cal_pay1[paid_mask])) if np.any(paid_mask) else -1.0

    # 4. Starved-month streak metrics
    tot_fm_sum = int(np.sum(funded_dry_tot))
    dry_fm_sum = int(np.sum(funded_dry_zero))
    dry_months_pct = (100.0 * dry_fm_sum / tot_fm_sum) if tot_fm_sum > 0 else 100.0
    streak_sub = funded_max_dry_streak[funded_dry_tot > 0]
    starved_p50 = int(np.median(streak_sub)) if len(streak_sub) > 0 else 0
    starved_p95 = int(np.quantile(streak_sub, 0.95)) if len(streak_sub) > 0 else 0
    starved_max = int(np.max(streak_sub)) if len(streak_sub) > 0 else 0

    # 5. Distribution stats for 24m & 36m Net Profit (USD & VND)
    def _dist_stats(arr_usd: np.ndarray) -> tuple[dict[str, float], dict[str, float]]:
        q_usd = {
            "mean": round(float(np.mean(arr_usd)), 2),
            "median": round(float(np.median(arr_usd)), 2),
            "p10": round(float(np.quantile(arr_usd, 0.10)), 2),
            "p90": round(float(np.quantile(arr_usd, 0.90)), 2),
        }
        q_vnd = {k: round(v * fx, 0) for k, v in q_usd.items()}
        return q_usd, q_vnd

    n24_usd, n24_vnd = _dist_stats(net_24m)
    n36_usd, n36_vnd = _dist_stats(net_36m)

    mean_fees_24m_usd = float(np.mean(fees_24m))
    mean_fees_36m_usd = float(np.mean(fees_36m))
    mean_fees_24m_vnd = mean_fees_24m_usd * fx
    mean_fees_36m_vnd = mean_fees_36m_usd * fx
    ev_per_1_vnd_fee_24m = (float(np.mean(net_24m)) * fx) / max(1.0, mean_fees_24m_vnd)
    ev_per_1_vnd_fee_36m = (float(np.mean(net_36m)) * fx) / max(1.0, mean_fees_36m_vnd)

    p_ruin_pct = round(100.0 * float(np.mean(ruined_ever > 0)), 2)
    p_ruin_24m_pct = round(100.0 * float(np.mean(ruined_24m > 0)), 2)
    p_net_le_0_24m_pct = round(100.0 * float(np.mean(net_24m <= 0.0)), 2)
    p_net_le_0_36m_pct = round(100.0 * float(np.mean(net_36m <= 0.0)), 2)

    # TreasuryLedger projection for mean path
    treasury_proj = build_treasury_ledger_projection(
        policy=case_cfg.allocation_policy,
        usd_vnd_rate=fx,
        reference_ticket_usd=reference_ticket_usd,
        total_fees_usd=mean_fees_36m_usd,
        total_gross_payouts_usd=float(np.mean(gross_payouts_36m)),
        total_cash_refunds_usd=float(np.mean(refunds_36m)),
        active_funded_nominal_usd=float(np.mean(max_base_funded_usd)),
    )

    law15_grade = _classify_law15_prop_tier(
        ev_per_fee=ev_per_1_vnd_fee_36m,
        funded_12m_blowup_pct=fn_blowup_12m_pct,
        p_ruin_pct=p_ruin_pct,
        uncond_med_pay1_days=uncond_med_730,
    )

    return {
        "case_id": case_cfg.case_id,
        "resolution_label_vi": RESOLUTION_LABEL_VI,
        "resolution_tag": RESOLUTION_TAG,
        "evidence_stage": EVIDENCE_STAGE,
        "execution_status": execution_status,
        "pricing_regime": pricing_regime,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": 0,
        "n_paths": n,
        "horizon_days": int(horizon_days),
        "bankroll_m_vnd": case_cfg.bankroll_m_vnd,
        "bankroll_vnd": round(case_cfg.bankroll_vnd, 0),
        "bankroll_usd": round(case_cfg.bankroll_usd, 2),
        "usd_vnd_rate": fx,
        "concurrency_mode": case_cfg.concurrency_mode.value,
        "allocation_policy": case_cfg.allocation_policy.value,
        # Monthly Pass + Fail + Pending == 100.0%
        "monthly_pass_fail_pending": fleet_horizons,
        "first_ticket_pass_fail_pending": first_ticket_horizons,
        # Separate BOT_AUTO_KILL vs FIRM_HARD_BREACH
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_events > 0)), 2),
        "mean_bot_auto_kill_events": round(float(np.mean(bot_kill_events)), 3),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_events > 0)), 2),
        "mean_firm_hard_breach_events": round(float(np.mean(firm_breach_events)), 3),
        "eval_hard_breach_pct": round(100.0 * float(np.mean(eval_breach_events > 0)), 2),
        "funded_hard_breach_pct": round(100.0 * float(np.mean(funded_breach_events > 0)), 2),
        "firm_hard_breach_daily_pct": round(100.0 * float(np.mean(firm_breach_daily_any > 0)), 2),
        "firm_hard_breach_maxdd_pct": round(100.0 * float(np.mean(firm_breach_maxdd_any > 0)), 2),
        "simultaneous_fail_pct": round(100.0 * float(np.mean(simult_fail_any > 0)), 2),
        # 12m Funded blowup + Wilson 95% UB
        "funded_12m_blowup": {
            "n_paths_entered_funded": n_paths_entered,
            "n_paths_full_12m_observed": n_full_12m,
            "n_paths_censored_lt_12m": n_cens_12m,
            "n_paths_breached_within_12m": n_br_12m,
            "blowup_12m_pct": round(fn_blowup_12m_pct, 2),
            "blowup_12m_uncensored_pct": round(fn_blowup_uncens_pct, 2),
            "wilson_95_ub_pct": round(wilson_ub_pct, 2),
            "fleet_total_funded_entries": int(np.sum(all_fn_entries)),
            "fleet_total_funded_breaches_12m": int(np.sum(all_fn_breach_12m)),
            "fleet_total_funded_censored_12m": int(np.sum(all_fn_censored_12m)),
            "note_n299": "Cần >= 299 quan sát độc lập không cháy để chứng minh cận trên Wilson 95% < 1%.",
        },
        # 24m & 36m Net Profit (USD & VND) — strictly liquid cash/own-book net of initial bankroll!
        "net_profit_24m_usd": n24_usd,
        "net_profit_24m_vnd": n24_vnd,
        "net_profit_36m_usd": n36_usd,
        "net_profit_36m_vnd": n36_vnd,
        "median_24m_net_usd": n24_usd["median"],
        "median_24m_net_vnd": n24_vnd["median"],
        "median_36m_net_usd": n36_usd["median"],
        "median_36m_net_vnd": n36_vnd["median"],
        "mean_36m_net_usd": n36_usd["mean"],
        "mean_36m_net_vnd": n36_vnd["mean"],
        "mean_wealth_36m_usd": round(float(np.mean(wealth_36m)), 2),
        "mean_own_book_36m_usd": round(float(np.mean(own_book_36m)), 2),
        "mean_recoup_cash_36m_usd": round(float(np.mean(recoup_cash_36m)), 2),
        "mean_challenge_cash_36m_usd": round(float(np.mean(challenge_cash_36m)), 2),
        "max_cash_accounting_err_usd": float(np.max(accounting_err_36m)),
        # Risk, Fee Efficiency & Cashflow Timing
        "p_net_le_0_24m_pct": p_net_le_0_24m_pct,
        "p_net_le_0_36m_pct": p_net_le_0_36m_pct,
        "p_bankroll_ruin_24m_pct": p_ruin_24m_pct,
        "p_bankroll_ruin_pct": p_ruin_pct,
        "mean_total_fees_24m_usd": round(mean_fees_24m_usd, 2),
        "mean_total_fees_36m_usd": round(mean_fees_36m_usd, 2),
        "mean_total_fees_36m_vnd": round(mean_fees_36m_vnd, 0),
        "mean_total_payouts_36m_usd": round(float(np.mean(payouts_36m)), 2),
        "mean_total_refunds_36m_usd": round(float(np.mean(refunds_36m)), 2),
        "ev_per_1_vnd_fee_24m": round(ev_per_1_vnd_fee_24m, 3),
        "ev_per_1_vnd_fee_36m": round(ev_per_1_vnd_fee_36m, 3),
        "paid_any_pct": round(100.0 * float(np.mean(paid_mask)), 2),
        "cond_med_pay1_cal_days": round(cond_med_pay1, 1),
        "uncond_med_pay1_cal_days_cap365": round(uncond_med_365, 1),
        "uncond_med_pay1_cal_days_cap730": round(uncond_med_730, 1),
        "funded_dry_months_pct": round(dry_months_pct, 2),
        "longest_starved_month_streak_p50": starved_p50,
        "longest_starved_month_streak_p95": starved_p95,
        "longest_starved_month_streak_max": starved_max,
        # Fleet Allocation Caps & Guards Telemetry (strictly separated from liquid net worth!)
        "max_active_base_funded_usd": round(float(np.max(max_base_funded_usd)), 2),
        "mean_max_base_funded_usd": round(float(np.mean(max_base_funded_usd)), 2),
        "max_active_scaled_funded_usd": round(float(np.max(max_scaled_funded_usd)), 2),
        "mean_scaling_upgrades": round(float(np.mean(scaling_upgrades_cnt)), 3),
        "fleet_guards_blocks": {
            "e1_eval_cooldown_mean": round(float(np.mean(e1_blocks_cnt)), 2),
            "e2_funded_dd_freeze_mean": round(float(np.mean(e2_blocks_cnt)), 2),
            "e4_funded_cap_mean": round(float(np.mean(e4_blocks_cnt)), 2),
        },
        "treasury_ledger_projection": {
            "crossover_phase": treasury_proj["crossover"]["recommended_phase"],
            "crossover_progress_pct": treasury_proj["crossover"]["crossover_progress_pct"],
            "bucket_policy": asdict(
                ALLOCATION_POLICY_SPECS[case_cfg.allocation_policy].to_treasury_bucket_policy(
                    max(1.0, reference_ticket_usd)
                )
            ),
        },
        "law15_position": law15_grade,
        "strategy_quality": strategy_quality or {},
        "is_pareto_in_tier": False,
        "is_pareto_overall": False,
    }


def extract_pareto_frontier(
    cases: list[dict[str, Any]],
    *,
    eps: float = 1e-9,
) -> list[dict[str, Any]]:
    """Extract non-dominated cases on `(median_36m_net_vnd MAX, p_bankroll_ruin_pct MIN, p_net_le_0_36m_pct MIN)`."""
    n = len(cases)
    frontier: list[dict[str, Any]] = []
    for i in range(n):
        ci = cases[i]
        net_i = float(ci["median_36m_net_vnd"])
        ruin_i = float(ci["p_bankroll_ruin_pct"])
        neg_i = float(ci["p_net_le_0_36m_pct"])
        dominated = False
        for j in range(n):
            if i == j:
                continue
            cj = cases[j]
            net_j = float(cj["median_36m_net_vnd"])
            ruin_j = float(cj["p_bankroll_ruin_pct"])
            neg_j = float(cj["p_net_le_0_36m_pct"])
            ge_net = net_j >= net_i - eps
            le_ruin = ruin_j <= ruin_i + eps
            le_neg = neg_j <= neg_i + eps
            strict_better = (net_j > net_i + eps) or (ruin_j < ruin_i - eps) or (neg_j < neg_i - eps)
            if ge_net and le_ruin and le_neg and strict_better:
                dominated = True
                break
        if not dominated:
            frontier.append(ci)
    frontier.sort(
        key=lambda c: (
            float(c["p_bankroll_ruin_pct"]),
            float(c["p_net_le_0_36m_pct"]),
            -float(c["median_36m_net_vnd"]),
            str(c["case_id"]),
        )
    )
    return frontier


# ---------------------------------------------------------------------------
# Public 81-Case Shared-Path Pareto Grid Runner
# ---------------------------------------------------------------------------


def run_pareto_81_grid(
    *,
    dev_days: list[str] | tuple[str, ...],
    trades: list[dict[str, Any]],
    n_paths: int = 200,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
    contract_ids: tuple[str, ...] = DEFAULT_FTMO_LADDER_CONTRACTS,
    bankroll_tiers_m_vnd: tuple[int, ...] = BANKROLL_TIERS_M_VND,
    concurrency_modes: tuple[ConcurrencyMode, ...] = CONCURRENCY_MODES,
    allocation_policies: tuple[AllocationPolicy, ...] = ALLOCATION_POLICIES,
    profile_id: str | None = None,
    use_promo_day0: bool = False,
    funded_mult_override: float | None = 1.0,
    annual_firm_hazard_rate: float = 0.0,
    eval_fail_cooldown_days: int = DEFAULT_EVAL_FAIL_COOLDOWN_DAYS,
    funded_dd_freeze_frac: float = DEFAULT_FUNDED_DD_FREEZE_FRAC,
    enable_scaling_plan: bool = True,
    own_book_daily_ret: float = 0.0,
    max_slots: int = DEFAULT_MAX_SLOTS,
    firms_catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH,
    fx_rates_path: Path = DEFAULT_FX_RATES_PATH,
    risk_profiles_path: Path = DEFAULT_RISK_PROFILES_PATH,
) -> dict[str, Any]:
    """Run the complete Shared-Path Multi-Account 81-Case Pareto Grid on Dev-only (`<= 2024-12-31`) data."""
    t0 = time.perf_counter()
    np_int = _require_strict_int(n_paths, "n_paths", min_val=1)
    h_days = _require_strict_int(horizon_days, "horizon_days", min_val=21)
    bl_int = _require_strict_int(block_len, "block_len", min_val=1)
    seed_int = _require_strict_int(seed, "seed", min_val=0)
    mslots = _require_strict_int(max_slots, "max_slots", min_val=1, max_val=64)
    cd_days = _require_strict_int(eval_fail_cooldown_days, "eval_fail_cooldown_days", min_val=0)
    dd_frz = _require_finite_float(funded_dd_freeze_frac, "funded_dd_freeze_frac", min_val=0.0, max_val=1.0)
    haz = _require_finite_float(annual_firm_hazard_rate, "annual_firm_hazard_rate", min_val=0.0, max_val=1.0)
    ob_ret = _require_finite_float(own_book_daily_ret, "own_book_daily_ret", min_val=-0.10, max_val=0.10)

    if ORDER_SEND_CAPABLE:
        raise RuntimeError("SAFETY_VIOLATION: ORDER_SEND_CAPABLE must be False")

    firms_cat, fx_cfg, risk_cfg, ssot_hashes = load_ssot_bundle(
        firms_catalog_path=firms_catalog_path,
        fx_rates_path=fx_rates_path,
        risk_profiles_path=risk_profiles_path,
    )
    usd_vnd = float(fx_cfg.usd_vnd)

    templates, tpl_meta = build_ssot_templates(
        firms_catalog=firms_cat,
        risk_profiles=risk_cfg,
        contract_ids=contract_ids,
        dev_days=dev_days,
        trades=trades,
        profile_id=profile_id,
        use_promo_day0=use_promo_day0,
        funded_mult_override=funded_mult_override,
    )

    # Sort ladder ascending by capital_usd for clean upgrade progression
    ladder_order = sorted(range(len(templates)), key=lambda idx: (templates[idx]["capital_usd"], idx))
    ladder_tpls = np.ascontiguousarray(ladder_order, dtype=np.int32)
    packed = _pack_templates_for_numba(templates)

    # Wave 4 extension arrays
    tpl_card_fx = np.ascontiguousarray([float(t["card_fx_fee_frac"]) for t in templates], dtype=np.float64)
    tpl_split_max = np.ascontiguousarray([float(t["profit_split_max_pct"]) for t in templates], dtype=np.float64)
    tpl_p1_st = np.ascontiguousarray([float(t["p1_ea_static_stop"]) for t in templates], dtype=np.float64)
    tpl_p2_st = np.ascontiguousarray([float(t["p2_ea_static_stop"]) for t in templates], dtype=np.float64)
    tpl_fn_st = np.ascontiguousarray([float(t["fn_ea_static_stop"]) for t in templates], dtype=np.float64)

    n_firms = max(1, int(tpl_meta["n_firms"]))
    firm_max_funded = np.full(n_firms, FTMO_MAX_ACTIVE_FUNDED_USD, dtype=np.float64)
    firm_max_single = np.full(n_firms, FTMO_MAX_SINGLE_CHALLENGE_USD, dtype=np.float64)
    firm_max_scaled = np.full(n_firms, FTMO_MAX_SCALED_FUNDED_USD, dtype=np.float64)

    n_obs = len(templates[0]["stage_arrays"][0])
    idx_matrix = make_block_bootstrap_indices(n_obs, horizon=h_days, n_paths=np_int, block_len=bl_int, seed=seed_int)
    hazard_days = make_firm_hazard_days(np_int, n_firms, haz, horizon=h_days, seed=seed_int + 777)

    configs = build_81_case_configs(
        usd_vnd_rate=usd_vnd,
        bankroll_tiers_m_vnd=bankroll_tiers_m_vnd,
        concurrency_modes=concurrency_modes,
        allocation_policies=allocation_policies,
    )

    ref_ticket_usd = float(templates[ladder_order[0]]["fee_regular_usd"]) * (
        1.0 + float(templates[ladder_order[0]]["card_fx_fee_frac"])
    )
    # Reference strategy quality from largest SKU in ladder (or 100K if present)
    ref_cid = (
        "ftmo_standard_100k"
        if "ftmo_standard_100k" in tpl_meta["sku_funded_diagnostics"]
        else templates[-1]["contract_id"]
    )
    ref_strategy_quality = tpl_meta["sku_funded_diagnostics"][ref_cid]

    exec_status_str = str(tpl_meta["execution_status"])
    pricing_regime_str = str(tpl_meta["pricing_regime"])
    enable_scaling_flag = bool(enable_scaling_plan)

    def _run_one_case(cfg: ParetoCaseConfig) -> dict[str, Any]:
        spec = ALLOCATION_POLICY_SPECS[cfg.allocation_policy]
        raw_res = _simulate_wave4_pareto_fleet_numba(
            idx_matrix,
            hazard_days,
            *packed,
            tpl_card_fx,
            tpl_split_max,
            tpl_p1_st,
            tpl_p2_st,
            tpl_fn_st,
            firm_max_funded,
            firm_max_single,
            firm_max_scaled,
            ladder_tpls,
            _CONCURRENCY_CODE[cfg.concurrency_mode],
            _ALLOCATION_CODE[cfg.allocation_policy],
            cfg.bankroll_usd,
            mslots,
            cd_days,
            dd_frz,
            enable_scaling_flag,
            ob_ret,
            spec.reserve_cap_tickets,
            spec.cash_recoup_pct,
            spec.upgrade_scale_pct,
            spec.own_book_pct,
        )
        return summarize_pareto_case(
            cfg,
            raw_res,
            horizon_days=h_days,
            execution_status=exec_status_str,
            pricing_regime=pricing_regime_str,
            reference_ticket_usd=ref_ticket_usd,
            strategy_quality=ref_strategy_quality,
        )

    t_sim_start = time.perf_counter()
    max_workers = min(len(configs), max(1, min(4, os.cpu_count() or 1)))
    if max_workers > 1 and len(configs) >= 4 and np_int >= 16:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            cases_out = list(pool.map(_run_one_case, configs))
    else:
        cases_out = [_run_one_case(cfg) for cfg in configs]
    sim_elapsed_s = time.perf_counter() - t_sim_start

    # Extract Pareto frontiers per bankroll tier and overall
    pareto_by_tier: dict[str, list[str]] = {}
    for tm in bankroll_tiers_m_vnd:
        tier_cases = [c for c in cases_out if c["bankroll_m_vnd"] == tm]
        tier_front = extract_pareto_frontier(tier_cases)
        tier_ids = {c["case_id"] for c in tier_front}
        for c in tier_cases:
            c["is_pareto_in_tier"] = c["case_id"] in tier_ids
        pareto_by_tier[f"{tm}M_VND"] = [c["case_id"] for c in tier_front]

    overall_front = extract_pareto_frontier(cases_out)
    overall_ids = {c["case_id"] for c in overall_front}
    for c in cases_out:
        c["is_pareto_overall"] = c["case_id"] in overall_ids

    # Shared-path daily correlation proof on top-rung Funded daily PnL
    top_tpl = templates[ladder_order[-1]]
    fn_nets = top_tpl["stage_arrays"][16]  # Funded net_usd array
    shared_corr = measure_shared_path_daily_correlation(
        daily_net_acct_a=fn_nets,
        daily_net_acct_b=fn_nets,
        n_paths=min(np_int, 200),
        horizon_days=min(h_days, 252),
        block_len=bl_int,
        seed=seed_int,
        shared_path=True,
    )

    total_elapsed_s = time.perf_counter() - t0
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_rows_analysed": 0,
            "shared_market_path_enforced": True,
            "ftmo_max_active_funded_usd": FTMO_MAX_ACTIVE_FUNDED_USD,
            "ftmo_max_single_challenge_usd": FTMO_MAX_SINGLE_CHALLENGE_USD,
            "ftmo_max_scaled_funded_usd": FTMO_MAX_SCALED_FUNDED_USD,
        },
        "resolution_label_vi": RESOLUTION_LABEL_VI,
        "resolution_tag": RESOLUTION_TAG,
        "evidence_stage": EVIDENCE_STAGE,
        "execution_status": tpl_meta["execution_status"],
        "pricing_regime": tpl_meta["pricing_regime"],
        "ssot_provenance": {
            **ssot_hashes,
            "usd_vnd_rate": usd_vnd,
            "fx_verified_utc": fx_cfg.verified_utc.isoformat(),
            "firms_catalog_updated_utc": firms_cat.updated_utc.isoformat(),
            "profile_id": tpl_meta["profile_id"],
            "contract_ids": list(contract_ids),
        },
        "grid_shape": {
            "n_bankroll_tiers": len(bankroll_tiers_m_vnd),
            "n_concurrency_modes": len(concurrency_modes),
            "n_allocation_policies": len(allocation_policies),
            "total_cases": len(cases_out),
            "n_paths": np_int,
            "horizon_days": h_days,
            "block_len": bl_int,
            "seed": seed_int,
        },
        "runtime_benchmark": {
            "sim_elapsed_sec": round(sim_elapsed_s, 4),
            "total_elapsed_sec": round(total_elapsed_s, 4),
        },
        "shared_path_correlation_proof": shared_corr,
        "sku_funded_diagnostics": tpl_meta["sku_funded_diagnostics"],
        "pareto_frontier_by_bankroll_tier": pareto_by_tier,
        "pareto_frontier_overall_ids": [c["case_id"] for c in overall_front],
        "cases": cases_out,
    }


def make_synthetic_dev_trade_fixture(
    *,
    n_days: int = 504,
    seed: int = DEFAULT_SEED,
    edge_r: float = 0.14,
    stop_risk_1lot_usd: float = 320.0,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Deterministic Dev-only (`2022–2024`, strictly `<= 2024-12-31`) trade fixture for offline smoke/unit runs."""
    nd = _require_strict_int(n_days, "n_days", min_val=21, max_val=1500)
    rng = np.random.default_rng(_require_strict_int(seed, "seed", min_val=0))
    stop_1lot = _require_finite_float(stop_risk_1lot_usd, "stop_risk_1lot_usd", min_val=1.0)
    edge = _require_finite_float(edge_r, "edge_r", min_val=-2.0, max_val=2.0)

    # Strictly generate business-like dates ending on 2024-12-31 going backward (0 Holdout rows!)
    from datetime import date, timedelta

    cur = date(2024, 12, 31)
    days_rev: list[str] = []
    while len(days_rev) < nd:
        if cur.weekday() < 5:
            days_rev.append(cur.isoformat())
        cur -= timedelta(days=1)
    dev_days = list(reversed(days_rev))
    enforce_pre_holdout_dates(dev_days, context="wave4.pareto.synthetic_fixture", cutoff_day=HOLDOUT_CUTOFF_DAY)

    # Mix of small-risk and medium-risk engines mirroring PORT_7E (0.1606% .. 0.75%) so 5K/10K hit 0.01-lot floor!
    engine_risks = (0.001606, 0.005894, 0.0075, 0.0050, 0.0050)
    trades: list[dict[str, Any]] = []
    for dk in dev_days:
        n_tr = int(rng.choice([0, 1, 1, 2], p=[0.25, 0.35, 0.25, 0.15]))
        for _ in range(n_tr):
            br = float(engine_risks[int(rng.integers(0, len(engine_risks)))])
            win = bool(rng.random() < 0.54)
            r_mult = float(rng.uniform(0.95, 1.55) + edge) if win else -float(rng.uniform(0.75, 1.05))
            sc = stop_1lot * float(rng.uniform(0.75, 1.45))
            net_1lot = r_mult * sc
            dd_1lot = (abs(net_1lot) if net_1lot < 0.0 else 0.0) + float(rng.uniform(0.05, 0.25)) * sc
            up_1lot = (net_1lot if net_1lot > 0.0 else 0.0) + float(rng.uniform(0.05, 0.25)) * sc
            trades.append(
                {
                    "day": dk,
                    "base_risk_frac": br,
                    "stop_risk_with_cost_usd": round(sc, 4),
                    "net_usd_per_lot": round(net_1lot, 4),
                    "intraday_dd_usd_per_lot": round(dd_1lot, 4),
                    "intraday_up_usd_per_lot": round(up_1lot, 4),
                }
            )
    return dev_days, trades


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 4 Shared-Path Multi-Account 81-Case Pareto Kernel CLI")
    ap.add_argument("--n-paths", type=int, default=200, help="Bootstrap shared paths (default: 200)")
    ap.add_argument("--horizon-days", type=int, default=DEFAULT_HORIZON_DAYS, help="Trading days (default: 756 = 36m)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG seed")
    ap.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    args = ap.parse_args(argv)

    dev_days, trades = make_synthetic_dev_trade_fixture(n_days=504, seed=args.seed)
    result = run_pareto_81_grid(
        dev_days=dev_days,
        trades=trades,
        n_paths=args.n_paths,
        horizon_days=args.horizon_days,
        seed=args.seed,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    summary = {
        "schema_version": result["schema_version"],
        "total_cases": result["grid_shape"]["total_cases"],
        "n_paths": result["grid_shape"]["n_paths"],
        "sim_elapsed_sec": result["runtime_benchmark"]["sim_elapsed_sec"],
        "shared_path_rho": result["shared_path_correlation_proof"]["mean_daily_pnl_rho"],
        "pareto_overall_count": len(result["pareto_frontier_overall_ids"]),
        "holdout_rows_analysed": result["hard_invariants"]["holdout_rows_analysed"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
