"""Wave 4 Own-Book Shadow Operations Engine (`W4-G08`) & OPS-4 Health Bridge.

Total Offensive #4 Wave 1A (`v4.8.1 FINAL`) offline read-only Own-Book shadow engine
composing verified Naqex sleeves strictly on pre-Holdout Dev data (`<= 2024-12-31`):
  1. `MACRO_ETF_SUPER_SLEEVE` (IBKR non-CEX): `SUPER_ETF_6ENG_EQW` via
     `quant_factory.ownbook_etf_super_sleeve` (4 Lab #4 + `L7_B1` + `L7_C3`)
     filtered strictly `<= 2024-12-31` BEFORE any signal or return calculation.
  2. `CRYPTO_SPOT` (CEX): causal Crypto Spot sleeve filtered strictly `<= 2024-12-31`.
  3. `CRYPTO_FUNDING_CARRY` (CEX): causal Delta-Neutral Spot Long + 1x Perp Short carry
     via `quant_lab.funding_carry_v2` (2.0x equity buffer, mark-price margin stress)
     filtered strictly `<= 2024-12-31`.
  4. `CASH_TBILL_BUFFER` (IBKR non-CEX): Cash & T-Bill buffer (`SGOV/BIL`) using real
     `BIL.parquet` Dev returns `<= 2024-12-31`.

HARD SAFETY & HOLDOUT INVARIANTS (`[ARCH-02]`, `W4-G08`):
  - Strictly offline & read-only:
      `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `SPEND_VND = 0`.
  - Holdout 2025+ strictly sealed (`-O`-safe, ZERO bare `assert` statements):
      * Every date series is checked with `quant_core.holdout_guard.enforce_pre_holdout_dates`
        plus an explicit `if max_date >= "2025-01-01": raise HoldoutLockError(...)`.
      * Local cache loaders drop rows `>= "2025-01-01"` at Parquet read time BEFORE any
        return, indicator, or weight array is constructed (`holdout_rows_analysed == 0`).
  - Hard CEX exposure cap `<= 25.0%` (`CRYPTO_SPOT + CRYPTO_FUNDING_CARRY <= 0.25`):
      fail-closed rejection (`ValueError`) on over-cap or poisoned (`NaN`/`Inf`/`bool`/negative)
      inputs, plus deterministic projection/clamp into `SGOV/BIL` when explicitly requested.
  - Funding Compression Alert (`annualized_funding < 3.0%`):
      auto-rotates 100% of `CRYPTO_FUNDING_CARRY` into `CASH_TBILL_BUFFER` (`SGOV/BIL`)
      and emits `FUNDING_COMPRESSION_ALERT`.
  - Executes all 4 Extreme Stress Tests (`STRESS_1..STRESS_4`) and emits an OPS-4
    compatible health snapshot (`GREEN` / `AMBER` / `RED`) with atomic SHA-256 receipt.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

QUANT_FACTORY_DIR: Final[Path] = Path(__file__).resolve().parents[1]
AI_ENGINES_DIR: Final[Path] = QUANT_FACTORY_DIR.parent
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
QUANT_LAB_SRC_DIR: Final[Path] = WORKSPACE_ROOT / "projects" / "quant-trading" / "src"

if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))
if QUANT_LAB_SRC_DIR.is_dir() and str(QUANT_LAB_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(QUANT_LAB_SRC_DIR))

from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
)
from quant_core.tca import canonical_payload_sha256, write_atomic_sha256_json  # noqa: E402

from quant_factory.crypto_causal_universe import CACHE_DIR as SPOT_CACHE_DIR  # noqa: E402
from quant_factory.data_store import assert_holdout_locked  # noqa: E402
from quant_factory.etf40_multifactor_vrp_lab import (  # noqa: E402
    ETF40_CACHE_DIR,
    ETF40_UNIVERSE,
    SIGNAL_ONLY_TICKERS,
    _safe_filename,
)
from quant_factory.funding_rate_carry import FUNDING_CACHE_DIR, _ms_to_date  # noqa: E402
from quant_factory.lab7_overnight_macro_rd_loop import simulate_etf_daily_or_overnight  # noqa: E402
from quant_factory.live_ops.daily_live_ops_pipeline import (  # noqa: E402
    TRAFFIC_ACTION_MATRIX,
    TRAFFIC_AMBER,
    TRAFFIC_GREEN,
    TRAFFIC_RED,
)
from quant_factory.ownbook_etf_super_sleeve import (  # noqa: E402
    SUPER_6_IDS,
    build_all_9_approved_engine_weights,
    compute_ibkr_order_commission,
    simulate_ibkr_integer_shares,
)
from quant_factory.portfolio_allocator import (  # noqa: E402
    DEFAULT_RETURNS_DIR,
    align_sleeves_business_days,
    compute_series_metrics,
)
from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE  # noqa: E402
from quant_factory.wave4 import ORDER_SEND_CAPABLE as _WAVE4_ORDER_SEND_CAPABLE  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety, Holdout & Policy Constants
# ---------------------------------------------------------------------------
ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0
SPEND_VND: Final[int] = 0

HOLDOUT_CUTOFF_INCLUSIVE: Final[str] = HOLDOUT_CUTOFF_DATE  # "2024-12-31"
HOLDOUT_CUTOFF_EXCLUSIVE: Final[str] = HOLDOUT_CUTOFF_DAY  # "2025-01-01"
HOLDOUT_START_UTC_MS: Final[int] = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp() * 1000)

MAX_CEX_EXPOSURE_FRAC: Final[float] = 0.25
MAX_CEX_EXPOSURE_PCT: Final[float] = 25.0
FUNDING_COMPRESSION_THRESHOLD_ANN: Final[float] = 0.03
FUNDING_COMPRESSION_THRESHOLD_PCT: Final[float] = 3.0
FUNDING_COMPRESSION_ALERT_CODE: Final[str] = "FUNDING_COMPRESSION_ALERT"
CEX_CAP_CLAMPED_ALERT_CODE: Final[str] = "CEX_CAP_CLAMPED"
CEX_CAP_BREACH_ALERT_CODE: Final[str] = "CEX_CAP_BREACH"
TBILL_BUFFER_VEHICLE: Final[str] = "SGOV/BIL"

SLEEVE_MACRO_ETF: Final[str] = "MACRO_ETF_SUPER_SLEEVE"
SLEEVE_CRYPTO_SPOT: Final[str] = "CRYPTO_SPOT"
SLEEVE_CRYPTO_CARRY: Final[str] = "CRYPTO_FUNDING_CARRY"
SLEEVE_CASH_TBILL: Final[str] = "CASH_TBILL_BUFFER"

CANONICAL_OWNBOOK_SLEEVES: Final[tuple[str, ...]] = (
    SLEEVE_MACRO_ETF,
    SLEEVE_CRYPTO_SPOT,
    SLEEVE_CRYPTO_CARRY,
    SLEEVE_CASH_TBILL,
)
CEX_SLEEVE_IDS: Final[frozenset[str]] = frozenset(
    {
        SLEEVE_CRYPTO_SPOT,
        SLEEVE_CRYPTO_CARRY,
        "S2_CRYPTO_SPOT",
        "S3A_FUND_CARRY",
    }
)
NON_CEX_SLEEVE_IDS: Final[frozenset[str]] = frozenset(
    {
        SLEEVE_MACRO_ETF,
        SLEEVE_CASH_TBILL,
        "S3B_MACRO_ETF",
        "S4_ETF40_MULTIFACTOR",
    }
)

DEFAULT_OWNBOOK_WEIGHTS: Final[dict[str, float]] = {
    SLEEVE_MACRO_ETF: 0.60,
    SLEEVE_CRYPTO_SPOT: 0.10,
    SLEEVE_CRYPTO_CARRY: 0.15,
    SLEEVE_CASH_TBILL: 0.15,
}

STRESS_1_ID: Final[str] = "STRESS_1_CEX_CAP_25PCT_INSOLVENCY"
STRESS_2_ID: Final[str] = "STRESS_2_FUNDING_COMPRESSION_LT3PCT"
STRESS_3_ID: Final[str] = "STRESS_3_2022_SIMULTANEOUS_STOCK_BOND_CRASH"
STRESS_4_ID: Final[str] = "STRESS_4_CRYPTO_FLASH_CRASH_MINUS35PCT"
ALL_STRESS_IDS: Final[tuple[str, ...]] = (
    STRESS_1_ID,
    STRESS_2_ID,
    STRESS_3_ID,
    STRESS_4_ID,
)

SUMMARY_SCHEMA: Final[str] = "naqex-wave4-ownbook-shadow-ops-v1"
OPS4_HEALTH_SCHEMA: Final[str] = "naqex-ops4-ownbook-shadow-health-v1"
WORKER_RECEIPT_SCHEMA: Final[str] = "naqex-wave4-worker-receipt-v1"

DEFAULT_SUMMARY_PATH: Final[Path] = (
    WORKSPACE_ROOT / ".runtime" / "offensive4" / "frontier" / "ownbook_shadow_ops_summary.json"
)
DEFAULT_AUDIT_RECEIPT_PATH: Final[Path] = (
    WORKSPACE_ROOT / ".runtime" / "offensive4" / "audits" / "w4_m2b_ownops_receipt.json"
)
DEFAULT_DROPBOX_PATH: Final[Path] = WORKSPACE_ROOT / ".tmp" / "swarm_dropbox" / "w4-m2b-ownops.json"


# ---------------------------------------------------------------------------
# Strict -O-Safe Validators (ZERO bare `assert` statements)
# ---------------------------------------------------------------------------
def _enforce_readonly_runtime() -> None:
    if _WAVE4_ORDER_SEND_CAPABLE or ORDER_SEND_CAPABLE or ORDER_SEND_COUNT != 0:
        raise RuntimeError(
            "READONLY_INVARIANT_VIOLATION: ownbook_shadow_ops is strictly offline/read-only (OrderSend = 0)."
        )


def validate_finite_float(
    value: Any,
    name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    strictly_positive: bool = False,
) -> float:
    """Validate finite numeric scalar; rejects `None`, `bool`, `NaN`, `Inf`, and out-of-bounds values."""
    if value is None or isinstance(value, (bool, np.bool_)):
        raise ValueError(f"INVALID_NUMERIC [{name}]: boolean or None value {value!r} rejected.")
    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"INVALID_NUMERIC [{name}]: non-numeric type {type(value).__name__} ({value!r}) rejected.")
    fval = float(value)
    if not math.isfinite(fval):
        raise ValueError(f"INVALID_NUMERIC [{name}]: non-finite value {value!r} rejected.")
    if strictly_positive and fval <= 0.0:
        raise ValueError(f"INVALID_NUMERIC [{name}]: value {fval} must be strictly > 0.")
    if minimum is not None and fval < minimum - 1e-12:
        raise ValueError(f"INVALID_NUMERIC [{name}]: value {fval} < minimum {minimum}.")
    if maximum is not None and fval > maximum + 1e-12:
        raise ValueError(f"INVALID_NUMERIC [{name}]: value {fval} > maximum {maximum}.")
    return fval


def validate_positive_int(value: Any, name: str, *, minimum: int = 1) -> int:
    """Validate strict integer (rejecting `bool`, `float`, `None`, and values `< minimum`)."""
    if value is None or isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"INVALID_INT [{name}]: non-integer value {value!r} rejected.")
    ival = int(value)
    if ival < minimum:
        raise ValueError(f"INVALID_INT [{name}]: value {ival} < minimum {minimum}.")
    return ival


def validate_cutoff_date(cutoff_date: Any, *, context: str = "ownbook_shadow_ops.cutoff") -> str:
    """Validate inclusive Dev cutoff date is strictly `< 2025-01-01` (fail-closed under `python -O`)."""
    if not isinstance(cutoff_date, str):
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_date must be ISO string, got {cutoff_date!r}."
        )
    cleaned = cutoff_date.strip()
    enforce_pre_holdout_dates(
        cleaned,
        context=context,
        cutoff_day=HOLDOUT_CUTOFF_EXCLUSIVE,
        allow_empty=False,
    )
    if cleaned >= HOLDOUT_CUTOFF_EXCLUSIVE:
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_date={cleaned!r} >= {HOLDOUT_CUTOFF_EXCLUSIVE}."
        )
    return cleaned


def enforce_ownbook_pre_holdout(
    dates: Iterable[Any],
    *,
    context: str = "ownbook_shadow_ops",
    cutoff_exclusive: str = HOLDOUT_CUTOFF_EXCLUSIVE,
    allow_empty: bool = False,
) -> int:
    """Hard `-O`-safe `< 2025-01-01` Holdout seal; returns `0` (`holdout_rows_analysed == 0`)."""
    if not isinstance(cutoff_exclusive, str) or cutoff_exclusive.strip() > HOLDOUT_CUTOFF_EXCLUSIVE:
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: cannot relax cutoff_exclusive={cutoff_exclusive!r} "
            f"beyond {HOLDOUT_CUTOFF_EXCLUSIVE}."
        )
    if dates is None or isinstance(dates, (bool, int, float, np.number, bytes, bytearray)):
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid dates container {dates!r} ({type(dates).__name__})."
        )
    date_list = [dates] if isinstance(dates, str) else list(dates)
    enforce_pre_holdout_dates(
        date_list,
        context=context,
        cutoff_day=cutoff_exclusive.strip(),
        allow_empty=allow_empty,
    )
    if date_list:
        iso_strings = [str(d).strip()[:10] for d in date_list]
        max_date = max(iso_strings)
        if max_date >= cutoff_exclusive.strip():
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: max_date={max_date!r} >= {cutoff_exclusive.strip()}."
            )
    holdout_rows_analysed = 0
    enforce_holdout_zero_rows(holdout_rows_analysed, context=context)
    return holdout_rows_analysed


def validate_pre_holdout_return_map(
    series_map: Mapping[str, Any],
    *,
    context: str,
    cutoff_exclusive: str = HOLDOUT_CUTOFF_EXCLUSIVE,
) -> dict[str, float]:
    """Validate a `date -> daily_return` mapping is non-empty, strictly `< 2025-01-01`, and finite."""
    if not isinstance(series_map, Mapping) or len(series_map) == 0:
        raise ValueError(f"INVALID_RETURN_MAP [{context}]: must be a non-empty mapping.")
    keys = list(series_map.keys())
    enforce_ownbook_pre_holdout(keys, context=context, cutoff_exclusive=cutoff_exclusive, allow_empty=False)
    cleaned: dict[str, float] = {}
    for k, v in series_map.items():
        rv = validate_finite_float(v, f"{context}[{k}]", minimum=-1.0, maximum=10.0)
        cleaned[str(k).strip()] = rv
    return cleaned


# ---------------------------------------------------------------------------
# Hard CEX Cap (`<= 25.0%`) Validation, Clamping & Configuration
# ---------------------------------------------------------------------------
def validate_ownbook_allocation(
    weights: Mapping[str, Any],
    *,
    max_cex_exposure: float = MAX_CEX_EXPOSURE_FRAC,
    allow_clamp: bool = False,
    require_unit_sum: bool = True,
    cex_sleeves: frozenset[str] = CEX_SLEEVE_IDS,
    tbill_sleeve: str = SLEEVE_CASH_TBILL,
) -> dict[str, Any]:
    """Validate (and optionally clamp) Own-Book weights against the hard `<= 25.0%` CEX cap.

    Fail-closed invariants (`-O`-safe):
      - Rejects `None`, empty mappings, non-string/blank sleeve IDs, `bool`, `NaN`, `Inf`,
        negative weights, weights `> 1.0`, or `max_cex_exposure > 0.25`.
      - If combined CEX weight `> max_cex_exposure + 1e-12`:
          * `allow_clamp=False` (default): raises `ValueError("CEX_CAP_VIOLATION: ...")`.
          * `allow_clamp=True`: proportionally scales CEX sleeves down to `max_cex_exposure`
            and routes 100% of clamped excess to `tbill_sleeve` (`SGOV/BIL`), emitting
            `CEX_CAP_CLAMPED`.
    """
    if not isinstance(weights, Mapping) or len(weights) == 0:
        raise ValueError("INVALID_ALLOCATION: weights must be a non-empty mapping.")
    cap = validate_finite_float(max_cex_exposure, "max_cex_exposure", minimum=0.0, maximum=MAX_CEX_EXPOSURE_FRAC)
    if cap > MAX_CEX_EXPOSURE_FRAC + 1e-12:
        raise ValueError(
            f"CEX_CAP_POLICY_VIOLATION: max_cex_exposure={cap:.4f} "
            f"exceeds immutable ceiling {MAX_CEX_EXPOSURE_FRAC:.2f}."
        )
    if type(allow_clamp) is not bool:
        raise ValueError("INVALID_ALLOCATION: allow_clamp must be a strict bool.")
    if type(require_unit_sum) is not bool:
        raise ValueError("INVALID_ALLOCATION: require_unit_sum must be a strict bool.")

    clean: dict[str, float] = {}
    for raw_k, raw_v in weights.items():
        if not isinstance(raw_k, str) or not raw_k.strip():
            raise ValueError(f"INVALID_ALLOCATION: invalid sleeve key {raw_k!r}.")
        k = raw_k.strip()
        w = validate_finite_float(raw_v, f"weights[{k}]", minimum=0.0, maximum=1.0)
        clean[k] = w

    total_w = float(sum(clean.values()))
    if not math.isfinite(total_w) or total_w <= 0.0 or total_w > 1.0 + 1e-6:
        raise ValueError(f"INVALID_ALLOCATION: weight sum {total_w:.6f} must be in (0.0, 1.0].")
    if require_unit_sum and abs(total_w - 1.0) > 1e-6:
        raise ValueError(f"INVALID_ALLOCATION: weight sum {total_w:.6f} must equal 1.0 within 1e-6.")

    cex_keys = [k for k in clean if k in cex_sleeves]
    raw_cex = float(sum(clean[k] for k in cex_keys))
    was_clamped = False
    clamped_excess = 0.0
    alerts: list[str] = []

    if raw_cex > cap + 1e-12:
        if not allow_clamp:
            raise ValueError(
                f"CEX_CAP_VIOLATION: combined CEX exposure {raw_cex * 100.0:.2f}% exceeds hard cap "
                f"{cap * 100.0:.2f}% (sleeves={ {k: round(clean[k] * 100.0, 2) for k in cex_keys} })."
            )
        scale = cap / raw_cex if raw_cex > 0.0 else 0.0
        for k in cex_keys:
            clean[k] = clean[k] * scale
        clamped_excess = raw_cex - float(sum(clean[k] for k in cex_keys))
        clean[tbill_sleeve] = clean.get(tbill_sleeve, 0.0) + clamped_excess
        was_clamped = True
        alerts.append(CEX_CAP_CLAMPED_ALERT_CODE)

    final_cex = float(sum(clean[k] for k in clean if k in cex_sleeves))
    if final_cex > cap + 1e-9:
        raise ValueError(
            f"CEX_CAP_VIOLATION_POST_CHECK: final CEX exposure {final_cex * 100.0:.4f}% > {cap * 100.0:.2f}%."
        )
    final_sum = float(sum(clean.values()))
    if require_unit_sum and abs(final_sum - 1.0) > 1e-6:
        raise ValueError(f"INVALID_ALLOCATION_POST_CHECK: sum {final_sum:.6f} != 1.0.")

    return {
        "weights": {k: round(v, 8) for k, v in clean.items()},
        "raw_cex_exposure_frac": round(raw_cex, 8),
        "raw_cex_exposure_pct": round(raw_cex * 100.0, 4),
        "cex_exposure_frac": round(final_cex, 8),
        "cex_exposure_pct": round(final_cex * 100.0, 4),
        "non_cex_exposure_pct": round((final_sum - final_cex) * 100.0, 4),
        "max_cex_cap_pct": round(cap * 100.0, 2),
        "cex_cap_compliant": final_cex <= cap + 1e-9,
        "was_clamped": was_clamped,
        "clamped_excess_pct": round(clamped_excess * 100.0, 4),
        "alerts": alerts,
    }


@dataclass(frozen=True, slots=True)
class OwnBookConfig:
    """Immutable, fail-closed Own-Book Shadow Operations configuration."""

    target_weights: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_OWNBOOK_WEIGHTS))
    max_cex_exposure: float = MAX_CEX_EXPOSURE_FRAC
    funding_compression_threshold_ann: float = FUNDING_COMPRESSION_THRESHOLD_ANN
    carry_equity_buffer_mult: float = 2.0
    cutoff_date: str = HOLDOUT_CUTOFF_INCLUSIVE
    start_date: str = "2020-01-01"
    etf_cost_bps_oneway: float = 5.0
    carry_oneway_pair_cost_bps: float = 23.0
    ibkr_capital_usd: float = 50_000.0
    tbill_vehicle: str = TBILL_BUFFER_VEHICLE

    def __post_init__(self) -> None:
        _enforce_readonly_runtime()
        validate_cutoff_date(self.cutoff_date, context="OwnBookConfig.cutoff_date")
        validate_cutoff_date(self.start_date, context="OwnBookConfig.start_date")
        if self.start_date > self.cutoff_date:
            raise ValueError(f"INVALID_CONFIG: start_date={self.start_date} > cutoff_date={self.cutoff_date}.")
        cap = validate_finite_float(
            self.max_cex_exposure,
            "max_cex_exposure",
            minimum=0.0,
            maximum=MAX_CEX_EXPOSURE_FRAC,
        )
        validate_finite_float(
            self.funding_compression_threshold_ann,
            "funding_compression_threshold_ann",
            minimum=0.0,
            maximum=1.0,
        )
        validate_finite_float(self.carry_equity_buffer_mult, "carry_equity_buffer_mult", minimum=1.5, maximum=10.0)
        validate_finite_float(self.etf_cost_bps_oneway, "etf_cost_bps_oneway", minimum=0.0, maximum=250.0)
        validate_finite_float(self.carry_oneway_pair_cost_bps, "carry_oneway_pair_cost_bps", minimum=0.0, maximum=500.0)
        validate_finite_float(self.ibkr_capital_usd, "ibkr_capital_usd", strictly_positive=True)
        if not isinstance(self.tbill_vehicle, str) or not self.tbill_vehicle.strip():
            raise ValueError("INVALID_CONFIG: tbill_vehicle must be a non-empty string.")
        # Strictly fail-closed validation of target_weights against hard <= 25% CEX cap
        alloc = validate_ownbook_allocation(
            self.target_weights,
            max_cex_exposure=cap,
            allow_clamp=False,
            require_unit_sum=True,
        )
        for req_sleeve in CANONICAL_OWNBOOK_SLEEVES:
            if req_sleeve not in alloc["weights"]:
                raise ValueError(f"INVALID_CONFIG: target_weights missing canonical sleeve {req_sleeve!r}.")
        object.__setattr__(self, "target_weights", dict(alloc["weights"]))


# ---------------------------------------------------------------------------
# Funding Compression Alert (`< 3.0%` Ann) & Auto-Rotation into SGOV/BIL
# ---------------------------------------------------------------------------
def evaluate_funding_compression_step(
    weights: Mapping[str, float],
    annualized_funding_rate: float,
    *,
    threshold_ann: float = FUNDING_COMPRESSION_THRESHOLD_ANN,
    max_cex_exposure: float = MAX_CEX_EXPOSURE_FRAC,
    allow_clamp: bool = False,
    tbill_vehicle: str = TBILL_BUFFER_VEHICLE,
) -> dict[str, Any]:
    """Evaluate single-step funding compression and auto-rotate carry into `SGOV/BIL` when `< 3.0%`.

    Strictly fail-closed on non-finite / boolean funding inputs or CEX cap violations.
    """
    alloc = validate_ownbook_allocation(
        weights,
        max_cex_exposure=max_cex_exposure,
        allow_clamp=allow_clamp,
        require_unit_sum=True,
    )
    ann_f = validate_finite_float(annualized_funding_rate, "annualized_funding_rate", minimum=-10.0, maximum=50.0)
    thresh = validate_finite_float(threshold_ann, "threshold_ann", minimum=0.0, maximum=1.0)

    eff_w = dict(alloc["weights"])
    alerts = list(alloc["alerts"])
    carry_w = float(eff_w.get(SLEEVE_CRYPTO_CARRY, 0.0))
    compression_active = ann_f < thresh
    rotated_frac = 0.0

    if compression_active:
        if carry_w > 0.0:
            rotated_frac = carry_w
            eff_w[SLEEVE_CRYPTO_CARRY] = 0.0
            eff_w[SLEEVE_CASH_TBILL] = round(eff_w.get(SLEEVE_CASH_TBILL, 0.0) + rotated_frac, 8)
        alerts.append(FUNDING_COMPRESSION_ALERT_CODE)

    post_alloc = validate_ownbook_allocation(
        eff_w,
        max_cex_exposure=max_cex_exposure,
        allow_clamp=False,
        require_unit_sum=True,
    )
    return {
        "annualized_funding_rate": round(ann_f, 6),
        "annualized_funding_rate_pct": round(ann_f * 100.0, 2),
        "threshold_ann": round(thresh, 6),
        "threshold_pct": round(thresh * 100.0, 2),
        "funding_compression_active": compression_active,
        "rotated_carry_to_tbill_frac": round(rotated_frac, 8),
        "rotated_carry_to_tbill_pct": round(rotated_frac * 100.0, 2),
        "tbill_vehicle": tbill_vehicle,
        "target_weights": dict(alloc["weights"]),
        "effective_weights": dict(post_alloc["weights"]),
        "effective_cex_exposure_pct": post_alloc["cex_exposure_pct"],
        "cex_cap_compliant": post_alloc["cex_cap_compliant"],
        "was_clamped": alloc["was_clamped"],
        "alerts": alerts,
    }


def _compute_trailing_mean_funding_ann(
    dates: Sequence[str],
    daily_funding: np.ndarray,
    window: int = 7,
) -> dict[str, float]:
    """Strictly causal trailing `window`-day annualized funding rate (equal-weight across active coins)."""
    n_t = len(dates)
    out: dict[str, float] = {}
    if daily_funding.ndim == 1:
        arr = daily_funding[:, None]
    else:
        arr = daily_funding
    for t in range(n_t):
        lo = max(0, t - window + 1)
        win = arr[lo : t + 1]
        finite_vals = win[np.isfinite(win)]
        if finite_vals.size > 0:
            out[str(dates[t])] = float(np.mean(finite_vals)) * 365.0
        else:
            out[str(dates[t])] = 0.0
    return out


# ---------------------------------------------------------------------------
# Strict Pre-Holdout (`<= 2024-12-31`) Local-Cache Loaders
# ---------------------------------------------------------------------------
def load_etf_super_sleeve_dev_returns(
    *,
    cache_dir: Path = ETF40_CACHE_DIR,
    cutoff_date: str = HOLDOUT_CUTOFF_INCLUSIVE,
    cost_bps_oneway: float = 5.0,
    ibkr_capital_usd: float = 50_000.0,
) -> dict[str, Any]:
    """Load 40-ETF panel strictly `<= cutoff_date` (`< 2025-01-01`) and replay `SUPER_ETF_6ENG_EQW` + `BIL`."""
    _enforce_readonly_runtime()
    cut = validate_cutoff_date(cutoff_date, context="load_etf_super_sleeve_dev_returns")
    cost_bps = validate_finite_float(cost_bps_oneway, "cost_bps_oneway", minimum=0.0, maximum=250.0)
    cap_usd = validate_finite_float(ibkr_capital_usd, "ibkr_capital_usd", strictly_positive=True)

    spy_path = Path(cache_dir) / _safe_filename("SPY")
    if not spy_path.exists():
        raise FileNotFoundError(f"Missing SPY parquet in {cache_dir}")

    spy_dates_raw = pq.read_table(spy_path, columns=["date"])["date"].to_pylist()
    raw_holdout_excluded = sum(1 for d in spy_dates_raw if str(d) >= HOLDOUT_CUTOFF_EXCLUSIVE)
    nyse_dates = sorted({str(d) for d in spy_dates_raw if str(d) <= cut})
    holdout_rows = enforce_ownbook_pre_holdout(nyse_dates, context="etf40_dev_panel", allow_empty=False)

    d_map = {d: i for i, d in enumerate(nyse_dates)}
    tickers = list(ETF40_UNIVERSE)
    n_t, n_k = len(nyse_dates), len(tickers)
    adj_open = np.full((n_t, n_k), np.nan, dtype=np.float64)
    adj_close = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, tk in enumerate(tickers):
        p = Path(cache_dir) / _safe_filename(tk)
        if not p.exists():
            continue
        tbl = pq.read_table(p, columns=["date", "open", "close", "adjclose"])
        ds = tbl["date"].to_pylist()
        op = tbl["open"].to_numpy(zero_copy_only=False).astype(np.float64)
        cl = tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64)
        ac = tbl["adjclose"].to_numpy(zero_copy_only=False).astype(np.float64)
        for d_raw, o_v, c_v, ac_v in zip(ds, op, cl, ac, strict=False):
            d_s = str(d_raw)
            if d_s > cut or d_s >= HOLDOUT_CUTOFF_EXCLUSIVE:
                continue
            idx = d_map.get(d_s)
            if idx is None or not (math.isfinite(ac_v) and ac_v > 0.0):
                continue
            adj_close[idx, j] = ac_v
            if math.isfinite(o_v) and o_v > 0.0 and math.isfinite(c_v) and c_v > 0.0:
                adj_open[idx, j] = o_v * (ac_v / c_v)
            else:
                adj_open[idx, j] = ac_v

    r_cc = np.full((n_t, n_k), np.nan, dtype=np.float64)
    r_ov = np.full((n_t, n_k), np.nan, dtype=np.float64)
    r_id = np.full((n_t, n_k), np.nan, dtype=np.float64)

    ok_cc = np.isfinite(adj_close[1:]) & np.isfinite(adj_close[:-1]) & (adj_close[:-1] > 0.0)
    r_cc[1:] = np.where(ok_cc, adj_close[1:] / np.where(ok_cc, adj_close[:-1], 1.0) - 1.0, np.nan)

    ok_ov = np.isfinite(adj_open[1:]) & np.isfinite(adj_close[:-1]) & (adj_close[:-1] > 0.0)
    r_ov[1:] = np.where(ok_ov, adj_open[1:] / np.where(ok_ov, adj_close[:-1], 1.0) - 1.0, np.nan)

    ok_id = np.isfinite(adj_close) & np.isfinite(adj_open) & (adj_open > 0.0)
    r_id = np.where(ok_id, adj_close / np.where(ok_id, adj_open, 1.0) - 1.0, np.nan)

    tradable_mask = np.array([tk not in SIGNAL_ONLY_TICKERS for tk in tickers], dtype=bool)
    panel4 = {"dates": nyse_dates, "symbols": tickers, "adjclose": adj_close}
    panel7 = {
        "dates": nyse_dates,
        "tickers": tickers,
        "tradable_mask": tradable_mask,
        "adj_open": adj_open,
        "adj_close": adj_close,
        "r_cc": r_cc,
        "r_ov": r_ov,
        "r_id": r_id,
    }

    eng_w = build_all_9_approved_engine_weights(panel4, panel7)
    w_super_6 = sum(eng_w[s] for s in SUPER_6_IDS) / float(len(SUPER_6_IDS))
    sim_super_6 = simulate_etf_daily_or_overnight(panel7, w_super_6, mode="close_to_close", cost_bps_oneway=cost_bps)

    dev2020_indices = [i for i, d in enumerate(nyse_dates) if d >= "2020-01-01"]
    ibkr_start = dev2020_indices[0] if dev2020_indices else 252
    ibkr_lot_audit = simulate_ibkr_integer_shares(
        nyse_dates,
        adj_close,
        r_cc,
        w_super_6,
        initial_capital_usd=cap_usd,
        fractional_shares=False,
        start_idx=ibkr_start,
    )
    sample_comm_100sh = compute_ibkr_order_commission(100.0, 500.0)

    def _ticker_ret_map(sym: str) -> dict[str, float]:
        j = tickers.index(sym)
        return {
            nyse_dates[i]: float(r_cc[i, j]) if math.isfinite(float(r_cc[i, j])) else 0.0
            for i in range(n_t)
        }

    super6_ret_map = {nyse_dates[i]: float(sim_super_6["net_returns"][i]) for i in range(n_t)}
    return {
        "dates": nyse_dates,
        "max_date": nyse_dates[-1],
        "n_days": n_t,
        "holdout_rows_analysed": holdout_rows,
        "raw_holdout_rows_excluded": int(raw_holdout_excluded),
        "macro_etf_returns": super6_ret_map,
        "bil_returns": _ticker_ret_map("BIL"),
        "spy_returns": _ticker_ret_map("SPY"),
        "ief_returns": _ticker_ret_map("IEF"),
        "tlt_returns": _ticker_ret_map("TLT"),
        "ibkr_lot_audit_dev": ibkr_lot_audit,
        "ibkr_sample_100sh_comm_usd": round(float(sample_comm_100sh), 4),
    }


def load_crypto_carry_dev_series(
    *,
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT"),
    funding_dir: Path = FUNDING_CACHE_DIR,
    spot_cache_dir: Path = SPOT_CACHE_DIR,
    cutoff_date: str = HOLDOUT_CUTOFF_INCLUSIVE,
    equity_buffer_mult: float = 2.0,
) -> dict[str, Any]:
    """Load Crypto Funding Carry panel strictly `< 2025-01-01` and replay via `quant_lab.funding_carry_v2`."""
    _enforce_readonly_runtime()
    cut = validate_cutoff_date(cutoff_date, context="load_crypto_carry_dev_series")
    buf = validate_finite_float(equity_buffer_mult, "equity_buffer_mult", minimum=1.5, maximum=10.0)

    daily_fund_by_sym: dict[str, dict[str, float]] = {}
    perp_c_by_sym: dict[str, dict[str, float]] = {}
    perp_h_by_sym: dict[str, dict[str, float]] = {}
    spot_c_by_sym: dict[str, dict[str, float]] = {}
    spot_h_by_sym: dict[str, dict[str, float]] = {}
    tail_8h_rates: dict[str, list[float]] = {}
    loaded_syms: list[str] = []
    all_days: set[str] = set()
    raw_holdout_excluded = 0

    for sym in symbols:
        rp = Path(funding_dir) / "rates" / f"{sym}.parquet"
        kp = Path(funding_dir) / "perp_1d" / f"{sym}.parquet"
        sp = Path(spot_cache_dir) / "1d" / f"{sym}.parquet"
        if not rp.exists() or not kp.exists() or not sp.exists():
            continue

        rtbl = pq.read_table(rp, columns=["funding_time_ms", "funding_rate"])
        ft = rtbl["funding_time_ms"].to_numpy(zero_copy_only=False)
        fr = rtbl["funding_rate"].to_numpy(zero_copy_only=False)
        dsum: dict[str, float] = defaultdict(float)
        sym_8h_pre: list[float] = []
        for ts, rate in zip(ft, fr, strict=False):
            ts_i = int(ts)
            if ts_i >= HOLDOUT_START_UTC_MS:
                raw_holdout_excluded += 1
                continue
            dk = _ms_to_date(ts_i)
            if dk < "2020-01-01" or dk > cut or dk >= HOLDOUT_CUTOFF_EXCLUSIVE:
                continue
            rf = float(rate)
            if math.isfinite(rf):
                dsum[dk] += rf
                sym_8h_pre.append(rf)
                all_days.add(dk)

        if not dsum:
            continue
        loaded_syms.append(sym)
        daily_fund_by_sym[sym] = dict(dsum)
        tail_8h_rates[sym] = sym_8h_pre[-21:]

        ktbl = pq.read_table(kp, columns=["open_time_ms", "high", "close"])
        pc: dict[str, float] = {}
        ph: dict[str, float] = {}
        for ot, hv, cv in zip(
            ktbl["open_time_ms"].to_numpy(zero_copy_only=False),
            ktbl["high"].to_numpy(zero_copy_only=False),
            ktbl["close"].to_numpy(zero_copy_only=False),
            strict=False,
        ):
            ot_i = int(ot)
            if ot_i >= HOLDOUT_START_UTC_MS:
                continue
            dk = _ms_to_date(ot_i)
            if dk <= cut and dk < HOLDOUT_CUTOFF_EXCLUSIVE:
                if math.isfinite(float(cv)) and float(cv) > 0.0:
                    pc[dk] = float(cv)
                if math.isfinite(float(hv)) and float(hv) > 0.0:
                    ph[dk] = float(hv)
        perp_c_by_sym[sym] = pc
        perp_h_by_sym[sym] = ph

        stbl = pq.read_table(sp, columns=["open_time_ms", "high", "close"])
        sc: dict[str, float] = {}
        sh: dict[str, float] = {}
        for ot, hv, cv in zip(
            stbl["open_time_ms"].to_numpy(zero_copy_only=False),
            stbl["high"].to_numpy(zero_copy_only=False),
            stbl["close"].to_numpy(zero_copy_only=False),
            strict=False,
        ):
            ot_i = int(ot)
            if ot_i >= HOLDOUT_START_UTC_MS:
                continue
            dk = _ms_to_date(ot_i)
            if dk <= cut and dk < HOLDOUT_CUTOFF_EXCLUSIVE:
                if math.isfinite(float(cv)) and float(cv) > 0.0:
                    sc[dk] = float(cv)
                if math.isfinite(float(hv)) and float(hv) > 0.0:
                    sh[dk] = float(hv)
        spot_c_by_sym[sym] = sc
        spot_h_by_sym[sym] = sh

    if not loaded_syms or not all_days:
        raise FileNotFoundError(f"Missing pre-holdout crypto funding/spot parquets in {funding_dir} / {spot_cache_dir}")

    dates = sorted(all_days)
    holdout_rows = enforce_ownbook_pre_holdout(dates, context="crypto_carry_dev_panel", allow_empty=False)
    n_t, n_k = len(dates), len(loaded_syms)

    fund_arr = np.full((n_t, n_k), np.nan, dtype=np.float64)
    sc_arr = np.full((n_t, n_k), np.nan, dtype=np.float64)
    sh_arr = np.full((n_t, n_k), np.nan, dtype=np.float64)
    pc_arr = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ph_arr = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, sym in enumerate(loaded_syms):
        for i, dk in enumerate(dates):
            if dk in daily_fund_by_sym[sym]:
                fund_arr[i, j] = daily_fund_by_sym[sym][dk]
            if dk in spot_c_by_sym[sym]:
                sc_arr[i, j] = spot_c_by_sym[sym][dk]
            if dk in spot_h_by_sym[sym]:
                sh_arr[i, j] = spot_h_by_sym[sym][dk]
            if dk in perp_c_by_sym[sym]:
                pc_arr[i, j] = perp_c_by_sym[sym][dk]
            if dk in perp_h_by_sym[sym]:
                ph_arr[i, j] = perp_h_by_sym[sym][dk]

    dt_idx = pd.to_datetime(dates, utc=True)
    f_df = pd.DataFrame(fund_arr, index=dt_idx, columns=loaded_syms)
    sc_df = pd.DataFrame(sc_arr, index=dt_idx, columns=loaded_syms)
    sh_df = pd.DataFrame(sh_arr, index=dt_idx, columns=loaded_syms)
    pc_df = pd.DataFrame(pc_arr, index=dt_idx, columns=loaded_syms)
    ph_df = pd.DataFrame(ph_arr, index=dt_idx, columns=loaded_syms)

    # Directly compose `quant_lab.funding_carry_v2` lazily (requires updated projects/quant-trading checkout)
    try:
        from quant_lab.funding_carry_v2 import (
            FundingCarryConfig,
            carry_btc_eth_cons_weights,
            compute_carry_btc_eth_live_step,
            run_funding_carry_backtest,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FUNDING_CARRY_V2_UNAVAILABLE: `quant_lab.funding_carry_v2` is required for local-cache "
            "Dev Own-Book carry replay (update projects/quant-trading checkout)."
        ) from exc

    w_cons = carry_btc_eth_cons_weights(
        f_df,
        sc_df,
        pc_df,
        symbols=tuple(loaded_syms[:2]),  # type: ignore[arg-type]
        enter_ann=FUNDING_COMPRESSION_THRESHOLD_ANN,
        exit_ann=0.0,
        enforce_pre_holdout=True,
        holdout_cutoff=HOLDOUT_CUTOFF_EXCLUSIVE,
    )
    carry_bt = run_funding_carry_backtest(
        f_df,
        sc_df,
        pc_df,
        w_cons,
        perp_high=ph_df,
        spot_high=sh_df,
        config=FundingCarryConfig(equity_buffer_mult=buf, oneway_pair_cost_bps=20.0, basis_cross_slip_bps=3.0),
        enforce_pre_holdout=True,
        holdout_cutoff=HOLDOUT_CUTOFF_EXCLUSIVE,
    )
    enforce_holdout_zero_rows(carry_bt["holdout_rows_analysed"], context="funding_carry_v2_bt")
    if carry_bt["order_send_capable"]:
        raise RuntimeError("READONLY_INVARIANT_VIOLATION: funding_carry_v2 reported order_send_capable=True.")

    live_step = compute_carry_btc_eth_live_step(
        tail_8h_rates,
        prev_state={sym: True for sym in loaded_syms[:2]},
        symbols=tuple(loaded_syms[:2]),  # type: ignore[arg-type]
        equity_buffer_mult=buf,
        enter_ann=FUNDING_COMPRESSION_THRESHOLD_ANN,
        exit_ann=0.0,
    )

    ret_series = carry_bt["backtest"]["strategy_return"].to_numpy(dtype=np.float64)
    carry_ret_map = {dates[i]: float(ret_series[i]) for i in range(n_t)}
    funding_ann_map = _compute_trailing_mean_funding_ann(dates, fund_arr, window=7)

    return {
        "dates": dates,
        "max_date": dates[-1],
        "symbols": loaded_syms,
        "holdout_rows_analysed": holdout_rows,
        "raw_holdout_rows_excluded": int(raw_holdout_excluded),
        "carry_returns": carry_ret_map,
        "funding_ann_map": funding_ann_map,
        "latest_funding_ann": funding_ann_map[dates[-1]],
        "latest_live_step": live_step,
        "margin_stress": dict(carry_bt["margin_stress"]),
        "carry_metrics_dev": {
            "cagr_pct": round(float(carry_bt["metrics"]["cagr"]) * 100.0, 2),
            "max_dd_pct": round(abs(float(carry_bt["metrics"]["max_drawdown"])) * 100.0, 2),
            "sharpe": round(float(carry_bt["metrics"]["sharpe_zero_rate"]), 2),
            "calmar": round(float(carry_bt["metrics"]["calmar"]), 2),
        },
    }


def load_crypto_spot_dev_returns(
    *,
    returns_dir: Path = DEFAULT_RETURNS_DIR,
    cutoff_date: str = HOLDOUT_CUTOFF_INCLUSIVE,
) -> dict[str, Any]:
    """Load `sleeve2_crypto_spot.json` strictly filtered `<= cutoff_date` (`< 2025-01-01`)."""
    _enforce_readonly_runtime()
    cut = validate_cutoff_date(cutoff_date, context="load_crypto_spot_dev_returns")
    p = Path(returns_dir) / "sleeve2_crypto_spot.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing Crypto Spot return series: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    dr = raw.get("daily_returns") or {}
    raw_holdout_excluded = sum(1 for k in dr if str(k) >= HOLDOUT_CUTOFF_EXCLUSIVE)
    filtered: dict[str, float] = {}
    for k, v in dr.items():
        ks = str(k).strip()
        if ks > cut or ks >= HOLDOUT_CUTOFF_EXCLUSIVE:
            continue
        fv = validate_finite_float(v, f"sleeve2_crypto_spot[{ks}]", minimum=-1.0, maximum=10.0)
        filtered[ks] = fv

    dates = sorted(filtered.keys())
    holdout_rows = enforce_ownbook_pre_holdout(dates, context="crypto_spot_dev_returns", allow_empty=False)
    return {
        "dates": dates,
        "max_date": dates[-1],
        "n_days": len(dates),
        "holdout_rows_analysed": holdout_rows,
        "raw_holdout_rows_excluded": int(raw_holdout_excluded),
        "crypto_spot_returns": filtered,
        "strategy_name": str(raw.get("strategy_name", "CRYPTO_SPOT")),
    }


# ---------------------------------------------------------------------------
# Causal Own-Book Composite Simulator (with Funding Compression Auto-Rotation)
# ---------------------------------------------------------------------------
def simulate_ownbook_composite(
    *,
    macro_etf_returns: Mapping[str, float],
    crypto_spot_returns: Mapping[str, float],
    crypto_carry_returns: Mapping[str, float],
    tbill_returns: Mapping[str, float],
    funding_ann_map: Mapping[str, float],
    config: OwnBookConfig | None = None,
) -> dict[str, Any]:
    """Simulate causal Mon-Fri Own-Book composite strictly on `< 2025-01-01` data.

    Strictly causal (`t-1` -> `t`):
      - Trailing 7d annualized funding observed at close of day `t-1` decides whether
        `CRYPTO_FUNDING_CARRY` stays active on day `t` or auto-rotates into `CASH_TBILL_BUFFER`
        (`SGOV/BIL`) with `FUNDING_COMPRESSION_ALERT`.
      - Enforces hard `CEX <= max_cex_exposure (<= 25%)` on EVERY simulated day (fail-closed).
      - Applies explicit carry/ETF transition friction on every rotation toggle.
    """
    _enforce_readonly_runtime()
    cfg = config or OwnBookConfig()

    m_etf = validate_pre_holdout_return_map(macro_etf_returns, context="composite.macro_etf")
    m_spot = validate_pre_holdout_return_map(crypto_spot_returns, context="composite.crypto_spot")
    m_carry = validate_pre_holdout_return_map(crypto_carry_returns, context="composite.crypto_carry")
    m_tbill = validate_pre_holdout_return_map(tbill_returns, context="composite.tbill")

    if not isinstance(funding_ann_map, Mapping) or len(funding_ann_map) == 0:
        raise ValueError("INVALID_FUNDING_MAP: funding_ann_map must be a non-empty mapping.")
    enforce_ownbook_pre_holdout(
        list(funding_ann_map.keys()),
        context="composite.funding_ann_map",
        allow_empty=False,
    )
    clean_fund = {
        str(k).strip(): validate_finite_float(v, f"funding_ann_map[{k}]", minimum=-10.0, maximum=50.0)
        for k, v in funding_ann_map.items()
    }

    sleeve_maps = {
        SLEEVE_MACRO_ETF: m_etf,
        SLEEVE_CRYPTO_SPOT: m_spot,
        SLEEVE_CRYPTO_CARRY: m_carry,
        SLEEVE_CASH_TBILL: m_tbill,
    }
    lo = max(cfg.start_date, max(min(m.keys()) for m in sleeve_maps.values()))
    hi = min(cfg.cutoff_date, min(max(m.keys()) for m in sleeve_maps.values()))
    if hi < lo:
        raise ValueError(f"EMPTY_OVERLAP: no common pre-holdout dates in [{lo}..{hi}].")

    biz_days, mat, names = align_sleeves_business_days(sleeve_maps, start_day=lo, end_day=hi)
    holdout_rows = enforce_ownbook_pre_holdout(biz_days, context="composite.biz_days", allow_empty=False)

    idx_etf = names.index(SLEEVE_MACRO_ETF)
    idx_spot = names.index(SLEEVE_CRYPTO_SPOT)
    idx_carry = names.index(SLEEVE_CRYPTO_CARRY)
    idx_tbill = names.index(SLEEVE_CASH_TBILL)

    w_etf = float(cfg.target_weights[SLEEVE_MACRO_ETF])
    w_spot = float(cfg.target_weights[SLEEVE_CRYPTO_SPOT])
    w_carry_base = float(cfg.target_weights[SLEEVE_CRYPTO_CARRY])
    w_tbill_base = float(cfg.target_weights[SLEEVE_CASH_TBILL])

    n_t = len(biz_days)
    guarded_rets = np.zeros(n_t, dtype=np.float64)
    static_rets = np.zeros(n_t, dtype=np.float64)
    cex_exp_series = np.zeros(n_t, dtype=np.float64)
    compression_flags = np.zeros(n_t, dtype=bool)
    rotation_events = 0
    prev_carry_active = True
    rot_cost_rate = (cfg.carry_oneway_pair_cost_bps + cfg.etf_cost_bps_oneway) / 10_000.0

    # Resolve causal funding rate per business day (latest known <= day)
    sorted_f_days = sorted(clean_fund.keys())
    f_vals_biz = np.zeros(n_t, dtype=np.float64)
    f_ptr = 0
    last_f = clean_fund[sorted_f_days[0]]
    for i, d in enumerate(biz_days):
        while f_ptr < len(sorted_f_days) and sorted_f_days[f_ptr] <= d:
            last_f = clean_fund[sorted_f_days[f_ptr]]
            f_ptr += 1
        f_vals_biz[i] = last_f

    for t in range(n_t):
        # Strictly causal signal: use day t-1 trailing funding to govern day t carry allocation
        sig_f = f_vals_biz[t - 1] if t > 0 else f_vals_biz[0]
        compressed = sig_f < cfg.funding_compression_threshold_ann
        compression_flags[t] = compressed

        w_c = 0.0 if compressed else w_carry_base
        w_tb = w_tbill_base + (w_carry_base if compressed else 0.0)
        cex_day = w_spot + w_c
        if cex_day > cfg.max_cex_exposure + 1e-12:
            raise ValueError(
                f"CEX_CAP_VIOLATION_RUNTIME: day {biz_days[t]} CEX={cex_day * 100.0:.2f}% "
                f"> {cfg.max_cex_exposure * 100.0:.2f}%."
            )
        cex_exp_series[t] = cex_day

        carry_active = not compressed
        toggle_cost = 0.0
        if t > 0 and carry_active != prev_carry_active and w_carry_base > 0.0:
            rotation_events += 1
            toggle_cost = w_carry_base * rot_cost_rate
        prev_carry_active = carry_active

        r_row = mat[t]
        static_rets[t] = (
            w_etf * r_row[idx_etf]
            + w_spot * r_row[idx_spot]
            + w_carry_base * r_row[idx_carry]
            + w_tbill_base * r_row[idx_tbill]
        )
        guarded_rets[t] = (
            w_etf * r_row[idx_etf]
            + w_spot * r_row[idx_spot]
            + w_c * r_row[idx_carry]
            + w_tb * r_row[idx_tbill]
            - toggle_cost
        )

    guarded_metrics = compute_series_metrics(guarded_rets, ann_days=252.0)
    static_metrics = compute_series_metrics(static_rets, ann_days=252.0)
    etf_metrics = compute_series_metrics(mat[:, idx_etf], ann_days=252.0)
    spot_metrics = compute_series_metrics(mat[:, idx_spot], ann_days=252.0)
    carry_metrics = compute_series_metrics(mat[:, idx_carry], ann_days=252.0)
    tbill_metrics = compute_series_metrics(mat[:, idx_tbill], ann_days=252.0)

    return {
        "dates": biz_days,
        "window": f"{biz_days[0]}..{biz_days[-1]}",
        "n_business_days": n_t,
        "holdout_rows_analysed": holdout_rows,
        "guarded_returns": guarded_rets,
        "static_returns": static_rets,
        "guarded_metrics": guarded_metrics,
        "static_metrics": static_metrics,
        "sleeve_metrics": {
            SLEEVE_MACRO_ETF: etf_metrics,
            SLEEVE_CRYPTO_SPOT: spot_metrics,
            SLEEVE_CRYPTO_CARRY: carry_metrics,
            SLEEVE_CASH_TBILL: tbill_metrics,
        },
        "max_realized_cex_exposure_pct": round(float(np.max(cex_exp_series)) * 100.0, 2),
        "mean_realized_cex_exposure_pct": round(float(np.mean(cex_exp_series)) * 100.0, 2),
        "funding_compression_days": int(np.sum(compression_flags)),
        "funding_compression_pct_days": round(100.0 * float(np.mean(compression_flags)), 2),
        "carry_rotation_events": int(rotation_events),
        "latest_funding_ann": float(f_vals_biz[-1]),
        "latest_funding_ann_pct": round(float(f_vals_biz[-1]) * 100.0, 2),
    }


# ---------------------------------------------------------------------------
# 4 Extreme Stress Tests (`STRESS_1 .. STRESS_4`)
# ---------------------------------------------------------------------------
def _compute_window_ret_and_dd(rets: np.ndarray) -> dict[str, float]:
    arr = np.asarray(rets, dtype=np.float64)
    if arr.size == 0:
        return {"return_pct": 0.0, "max_dd_pct": 0.0}
    eq = np.cumprod(np.maximum(0.0, 1.0 + arr))
    peaks = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    dd = np.where(peaks > 0.0, (peaks - eq) / peaks, 1.0)
    return {
        "return_pct": round((float(eq[-1]) - 1.0) * 100.0, 2),
        "max_dd_pct": round(float(np.max(dd)) * 100.0, 2),
    }


def run_stress_1_cex_cap_25pct_insolvency(
    config: OwnBookConfig | None = None,
    *,
    effective_weights: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """STRESS_1_CEX_CAP_25PCT_INSOLVENCY: Hard CEX <= 25% + simulated -100% CEX insolvency haircut.

    Verifies:
      1. Any mutated allocation > 25% CEX is rejected fail-closed (`ValueError`).
      2. Under a total `-100%` CEX wipeout (0% recovery on Crypto Spot + Funding Carry),
         total Own-Book drawdown is strictly bounded `<= 25.0%` and remaining segregated
         non-CEX equity (IBKR ETF + `SGOV/BIL`) stays `>= 75.0%`.
    """
    _enforce_readonly_runtime()
    cfg = config or OwnBookConfig()
    weights = effective_weights if effective_weights is not None else cfg.target_weights
    alloc = validate_ownbook_allocation(weights, max_cex_exposure=cfg.max_cex_exposure, allow_clamp=False)

    # Active fail-closed mutation check: 35% CEX MUST raise ValueError
    mutated_overcap = {
        SLEEVE_MACRO_ETF: 0.50,
        SLEEVE_CRYPTO_SPOT: 0.15,
        SLEEVE_CRYPTO_CARRY: 0.20,  # 35% CEX > 25% hard cap!
        SLEEVE_CASH_TBILL: 0.15,
    }
    breach_rejected = False
    try:
        validate_ownbook_allocation(mutated_overcap, max_cex_exposure=cfg.max_cex_exposure, allow_clamp=False)
    except ValueError:
        breach_rejected = True

    # Simulate -100% CEX haircut on both actual effective weights and worst-case 25% boundary
    eff_cex_frac = float(alloc["cex_exposure_frac"])
    eff_haircut_dd_pct = round(eff_cex_frac * 100.0, 2)
    eff_surviving_equity_pct = round((1.0 - eff_cex_frac) * 100.0, 2)

    cap_boundary_dd_pct = round(cfg.max_cex_exposure * 100.0, 2)
    cap_boundary_surviving_pct = round((1.0 - cfg.max_cex_exposure) * 100.0, 2)

    passed = bool(
        breach_rejected
        and alloc["cex_cap_compliant"]
        and eff_haircut_dd_pct <= MAX_CEX_EXPOSURE_PCT + 1e-9
        and cap_boundary_dd_pct <= MAX_CEX_EXPOSURE_PCT + 1e-9
        and eff_surviving_equity_pct >= 75.0 - 1e-9
    )
    return {
        "stress_id": STRESS_1_ID,
        "passed": passed,
        "breach_gt25_rejected_fail_closed": breach_rejected,
        "cex_exposure_pct": alloc["cex_exposure_pct"],
        "cex_cap_pct": MAX_CEX_EXPOSURE_PCT,
        "simulated_cex_haircut_pct": -100.0,
        "effective_ownbook_dd_pct": eff_haircut_dd_pct,
        "effective_surviving_equity_pct": eff_surviving_equity_pct,
        "worst_case_cap_boundary_dd_pct": cap_boundary_dd_pct,
        "worst_case_surviving_equity_pct": cap_boundary_surviving_pct,
        "dd_bound_pct": MAX_CEX_EXPOSURE_PCT,
        "dd_within_25pct_bound": eff_haircut_dd_pct <= MAX_CEX_EXPOSURE_PCT + 1e-9,
        "holdout_rows_analysed": 0,
    }


def run_stress_2_funding_compression_lt3pct(
    config: OwnBookConfig | None = None,
    *,
    n_warmup_days: int = 21,
    n_compression_days: int = 180,
    tbill_ann_yield: float = 0.04,
) -> dict[str, Any]:
    """STRESS_2_FUNDING_COMPRESSION_LT3PCT: 6-month funding < 3% + negative spikes.

    Verifies:
      - `FUNDING_COMPRESSION_ALERT` fires promptly when trailing 7d annualized funding < 3.0%.
      - Carry allocation de-risks cleanly to `0.0%` and rotates into `SGOV/BIL` T-Bills.
      - Guarded Own-Book carry sleeve strictly outperforms unprotected static carry in both
        total return and max drawdown across the 6-month compressed + negative-spike regime.
    """
    _enforce_readonly_runtime()
    cfg = config or OwnBookConfig()
    n_w = validate_positive_int(n_warmup_days, "n_warmup_days", minimum=7)
    n_c = validate_positive_int(n_compression_days, "n_compression_days", minimum=120)
    tb_yield = validate_finite_float(tbill_ann_yield, "tbill_ann_yield", minimum=0.0, maximum=0.20)

    n_total = n_w + n_c
    # Deterministic daily annualized funding trajectory:
    #   Days 0..n_w-1: healthy +10.5% ann (carry active)
    #   Days n_w..n_total-1 (180d = 6m): compressed < 3% (+1.5% -> +0.4% + negative spikes -12%..-22%)
    ann_series = np.full(n_total, 0.105, dtype=np.float64)
    for k in range(n_c):
        t = n_w + k
        if k < 25:
            ann_series[t] = 0.015
        elif k % 17 in (0, 1, 2):
            ann_series[t] = -0.22
        elif k % 11 in (0, 1):
            ann_series[t] = -0.10
        else:
            ann_series[t] = 0.006

    daily_funding = ann_series / 365.0
    daily_tbill = tb_yield / 365.0
    notional_cap = 1.0 / cfg.carry_equity_buffer_mult
    w_carry_target = float(cfg.target_weights[SLEEVE_CRYPTO_CARRY])
    rot_cost_rate = (cfg.carry_oneway_pair_cost_bps + cfg.etf_cost_bps_oneway) / 10_000.0

    # Trailing 7d causal annualized funding
    trail7_ann = np.zeros(n_total, dtype=np.float64)
    for t in range(n_total):
        lo = max(0, t - 6)
        trail7_ann[t] = float(np.mean(daily_funding[lo : t + 1])) * 365.0

    guarded_sleeve_rets = np.zeros(n_total, dtype=np.float64)
    unprotected_sleeve_rets = np.zeros(n_total, dtype=np.float64)
    alerts_emitted: list[str] = []
    first_alert_day: int | None = None
    active_carry_days_in_compression = 0
    carry_active = True

    for t in range(n_total):
        sig_ann = trail7_ann[t - 1] if t > 0 else trail7_ann[0]
        # Unprotected static carry keeps holding through < 3% and negative spikes
        unprotected_sleeve_rets[t] = notional_cap * daily_funding[t]

        step_eval = evaluate_funding_compression_step(
            cfg.target_weights,
            sig_ann,
            threshold_ann=cfg.funding_compression_threshold_ann,
            max_cex_exposure=cfg.max_cex_exposure,
            tbill_vehicle=cfg.tbill_vehicle,
        )
        compressed = bool(step_eval["funding_compression_active"])
        if compressed and FUNDING_COMPRESSION_ALERT_CODE in step_eval["alerts"]:
            if first_alert_day is None:
                first_alert_day = t
            if FUNDING_COMPRESSION_ALERT_CODE not in alerts_emitted:
                alerts_emitted.append(FUNDING_COMPRESSION_ALERT_CODE)

        next_active = not compressed
        toggle_cost = rot_cost_rate if (t > 0 and next_active != carry_active) else 0.0
        carry_active = next_active
        if t >= n_w and carry_active:
            active_carry_days_in_compression += 1

        if carry_active:
            guarded_sleeve_rets[t] = notional_cap * daily_funding[t] - toggle_cost
        else:
            guarded_sleeve_rets[t] = daily_tbill - toggle_cost

    # Verify final compression step state
    final_step = evaluate_funding_compression_step(
        cfg.target_weights,
        float(trail7_ann[-1]),
        threshold_ann=cfg.funding_compression_threshold_ann,
        max_cex_exposure=cfg.max_cex_exposure,
        tbill_vehicle=cfg.tbill_vehicle,
    )
    g_stats = _compute_window_ret_and_dd(guarded_sleeve_rets[n_w:])
    u_stats = _compute_window_ret_and_dd(unprotected_sleeve_rets[n_w:])

    # Portfolio-level impact (scaled by w_carry_target)
    g_port_stats = _compute_window_ret_and_dd(w_carry_target * guarded_sleeve_rets[n_w:])
    u_port_stats = _compute_window_ret_and_dd(w_carry_target * unprotected_sleeve_rets[n_w:])

    post_carry_w = float(final_step["effective_weights"][SLEEVE_CRYPTO_CARRY])
    alert_fired = FUNDING_COMPRESSION_ALERT_CODE in alerts_emitted
    passed = bool(
        alert_fired
        and post_carry_w == 0.0
        and final_step["funding_compression_active"]
        and g_stats["return_pct"] > u_stats["return_pct"]
        and g_stats["max_dd_pct"] < u_stats["max_dd_pct"]
        and first_alert_day is not None
        and first_alert_day <= n_w + 7
    )
    return {
        "stress_id": STRESS_2_ID,
        "passed": passed,
        "compression_duration_days": n_c,
        "threshold_pct": round(cfg.funding_compression_threshold_ann * 100.0, 2),
        "min_spike_ann_pct": round(float(np.min(ann_series)) * 100.0, 2),
        "alert_code": FUNDING_COMPRESSION_ALERT_CODE,
        "alert_fired": alert_fired,
        "first_alert_offset_days": int(first_alert_day - n_w) if first_alert_day is not None else None,
        "active_carry_days_during_compression": int(active_carry_days_in_compression),
        "post_compression_carry_weight_pct": round(post_carry_w * 100.0, 2),
        "rotated_to_tbill_pct": final_step["rotated_carry_to_tbill_pct"],
        "tbill_vehicle": cfg.tbill_vehicle,
        "guarded_carry_sleeve_return_pct": g_stats["return_pct"],
        "guarded_carry_sleeve_max_dd_pct": g_stats["max_dd_pct"],
        "unprotected_carry_sleeve_return_pct": u_stats["return_pct"],
        "unprotected_carry_sleeve_max_dd_pct": u_stats["max_dd_pct"],
        "ownbook_carry_contribution_guarded_pct": g_port_stats["return_pct"],
        "ownbook_carry_contribution_unprotected_pct": u_port_stats["return_pct"],
        "holdout_rows_analysed": 0,
    }


def run_stress_3_2022_stock_bond_crash(
    *,
    dates: Sequence[str],
    ownbook_returns: Sequence[float] | np.ndarray,
    spy_returns: Mapping[str, float],
    bond_returns: Mapping[str, float],
    tlt_returns: Mapping[str, float] | None = None,
    window_start: str = "2022-01-01",
    window_end: str = "2022-12-31",
    max_allowed_ownbook_dd_pct: float = 15.0,
) -> dict[str, Any]:
    """STRESS_3_2022_SIMULTANEOUS_STOCK_BOND_CRASH: Empirical 2022 Dev window vs Static 60/40.

    Strictly enforces `< 2025-01-01` across all input dates and verifies Own-Book MaxDD containment
    vs the simultaneous stock+bond crash in static `60% SPY + 40% IEF` (plus `60/40 SPY/TLT` ref).
    """
    _enforce_readonly_runtime()
    validate_cutoff_date(window_start, context="stress3.window_start")
    validate_cutoff_date(window_end, context="stress3.window_end")
    max_dd_cap = validate_finite_float(max_allowed_ownbook_dd_pct, "max_allowed_ownbook_dd_pct", strictly_positive=True)

    holdout_rows = enforce_ownbook_pre_holdout(dates, context="stress3.dates", allow_empty=False)
    clean_spy = validate_pre_holdout_return_map(spy_returns, context="stress3.spy_returns")
    clean_bond = validate_pre_holdout_return_map(bond_returns, context="stress3.bond_returns")
    clean_tlt = (
        validate_pre_holdout_return_map(tlt_returns, context="stress3.tlt_returns")
        if tlt_returns is not None
        else None
    )

    own_arr = np.asarray(ownbook_returns, dtype=np.float64)
    if len(dates) != len(own_arr):
        raise ValueError(f"LENGTH_MISMATCH: len(dates)={len(dates)} != len(ownbook_returns)={len(own_arr)}.")
    if not bool(np.all(np.isfinite(own_arr))):
        raise ValueError("INVALID_RETURNS: ownbook_returns contains NaN/Inf.")

    idx_2022 = [i for i, d in enumerate(dates) if window_start <= str(d) <= window_end]
    if len(idx_2022) < 20:
        raise ValueError(f"INSUFFICIENT_2022_WINDOW: found only {len(idx_2022)} rows in {window_start}..{window_end}.")

    r_own = np.array([own_arr[i] for i in idx_2022], dtype=np.float64)
    r_spy = np.array([clean_spy.get(str(dates[i]), 0.0) for i in idx_2022], dtype=np.float64)
    r_ief = np.array([clean_bond.get(str(dates[i]), 0.0) for i in idx_2022], dtype=np.float64)
    r_60_40 = 0.60 * r_spy + 0.40 * r_ief

    own_stats = _compute_window_ret_and_dd(r_own)
    bm_stats = _compute_window_ret_and_dd(r_60_40)

    tlt_60_40_stats: dict[str, float] | None = None
    if clean_tlt is not None:
        r_tlt = np.array([clean_tlt.get(str(dates[i]), 0.0) for i in idx_2022], dtype=np.float64)
        tlt_60_40_stats = _compute_window_ret_and_dd(0.60 * r_spy + 0.40 * r_tlt)

    dd_reduction_pp = round(bm_stats["max_dd_pct"] - own_stats["max_dd_pct"], 2)
    dd_ratio = round(own_stats["max_dd_pct"] / max(bm_stats["max_dd_pct"], 1e-6), 4)
    passed = bool(
        own_stats["max_dd_pct"] < bm_stats["max_dd_pct"]
        and own_stats["max_dd_pct"] <= max_dd_cap
    )
    return {
        "stress_id": STRESS_3_ID,
        "passed": passed,
        "window": f"{dates[idx_2022[0]]}..{dates[idx_2022[-1]]}",
        "n_days": len(idx_2022),
        "ownbook_2022_return_pct": own_stats["return_pct"],
        "ownbook_2022_max_dd_pct": own_stats["max_dd_pct"],
        "static_60_40_ief_2022_return_pct": bm_stats["return_pct"],
        "static_60_40_ief_2022_max_dd_pct": bm_stats["max_dd_pct"],
        "static_60_40_tlt_2022_ref": tlt_60_40_stats,
        "dd_reduction_vs_60_40_pp": dd_reduction_pp,
        "dd_ratio_vs_60_40": dd_ratio,
        "max_allowed_ownbook_dd_pct": round(max_dd_cap, 2),
        "holdout_rows_analysed": holdout_rows,
    }


def run_stress_4_crypto_flash_crash_minus35pct(
    config: OwnBookConfig | None = None,
    *,
    effective_weights: Mapping[str, float] | None = None,
    spot_shock_pct: float = -35.0,
    adverse_basis_blowout_bps: float = 300.0,
    intraday_whipsaw_jump_pct: float = 35.0,
    max_allowed_shock_dd_pct: float = 10.0,
) -> dict[str, Any]:
    """STRESS_4_CRYPTO_FLASH_CRASH_MINUS35PCT: -35% 24h crypto shock + basis blow-out.

    Audits BOTH:
      1. Spot unlevered `-35%` 24h crash loss (`0` liquidations because Spot is 1x unlevered).
      2. Delta-neutral Funding Carry (`2.0x` equity buffer -> `0.50x` notional Spot Long +
         `0.50x` Perp Short backed by `0.50x` USDT perp margin = `1.0x` perp leverage,
         `liq_threshold_jump = (buffer - 1.0) - 0.05 = 95.0%`) under BOTH:
         - `-35%` crash with adverse `-300 bps` Spot-Perp basis blow-out + exit shock friction
         - `+35%` violent dead-cat whipsaw jump against the short perp leg
         verifying `isolated_liq_events == 0`, `cross_liq_events == 0`, and portfolio survival!
    """
    _enforce_readonly_runtime()
    cfg = config or OwnBookConfig()
    weights = effective_weights if effective_weights is not None else cfg.target_weights
    alloc = validate_ownbook_allocation(weights, max_cex_exposure=cfg.max_cex_exposure, allow_clamp=False)

    shock_pct = validate_finite_float(spot_shock_pct, "spot_shock_pct", minimum=-95.0, maximum=-1.0)
    basis_bps = validate_finite_float(
        adverse_basis_blowout_bps,
        "adverse_basis_blowout_bps",
        minimum=0.0,
        maximum=2500.0,
    )
    whipsaw_pct = validate_finite_float(
        intraday_whipsaw_jump_pct,
        "intraday_whipsaw_jump_pct",
        minimum=0.0,
        maximum=200.0,
    )
    max_shock_dd = validate_finite_float(max_allowed_shock_dd_pct, "max_allowed_shock_dd_pct", strictly_positive=True)

    w_spot = float(alloc["weights"].get(SLEEVE_CRYPTO_SPOT, 0.0))
    w_carry = float(alloc["weights"].get(SLEEVE_CRYPTO_CARRY, 0.0))

    # 1. Crypto Spot sleeve: 1x unlevered spot -> zero liquidation risk
    spot_shock_frac = shock_pct / 100.0  # -0.35
    spot_ownbook_pnl_frac = w_spot * spot_shock_frac  # e.g., 0.10 * -0.35 = -0.035
    spot_liq_events = 0

    # 2. Funding Carry sleeve (exact `funding_carry_v2.py` margin buffer & basis blow-out accounting)
    notional_cap = 1.0 / cfg.carry_equity_buffer_mult  # 0.50 at 2.0x buffer
    perp_margin_ratio = max(0.05, cfg.carry_equity_buffer_mult - 1.0)  # 1.00 at 2.0x buffer
    liq_threshold_jump = perp_margin_ratio - 0.05  # 0.95 (+95% jump required to liquidate short perp)

    basis_blowout_frac = basis_bps / 10_000.0  # 0.03 (300 bps adverse basis)
    exit_shock_frac = min(0.0025, 0.5 * basis_blowout_frac)  # capped adverse exit friction per funding_carry_v2
    carry_sleeve_loss_frac = -(notional_cap * (basis_blowout_frac + exit_shock_frac))
    carry_ownbook_pnl_frac = w_carry * carry_sleeve_loss_frac

    # Mark-Price liquidation audit on violent +whipsaw_pct short-squeeze bounce
    whipsaw_frac = whipsaw_pct / 100.0
    isolated_liq_events = 1 if (w_carry > 1e-9 and whipsaw_frac >= liq_threshold_jump) else 0
    futures_margin_pool = max(1e-6, 1.0 - notional_cap)
    cross_margin_draw_frac = (notional_cap * whipsaw_frac) / futures_margin_pool if w_carry > 1e-9 else 0.0
    cross_liq_events = 1 if (w_carry > 1e-9 and cross_margin_draw_frac >= 0.90) else 0

    total_ownbook_pnl_frac = spot_ownbook_pnl_frac + carry_ownbook_pnl_frac
    total_ownbook_dd_pct = round(max(0.0, -total_ownbook_pnl_frac) * 100.0, 2)
    post_crash_equity_pct = round((1.0 + total_ownbook_pnl_frac) * 100.0, 2)
    margin_headroom_pct = round((liq_threshold_jump - whipsaw_frac) * 100.0, 2)

    zero_liquidation = (spot_liq_events == 0) and (isolated_liq_events == 0) and (cross_liq_events == 0)
    passed = bool(
        zero_liquidation
        and total_ownbook_dd_pct <= max_shock_dd
        and total_ownbook_dd_pct <= MAX_CEX_EXPOSURE_PCT
        and post_crash_equity_pct >= (100.0 - max_shock_dd)
        and margin_headroom_pct > 0.0
    )
    return {
        "stress_id": STRESS_4_ID,
        "passed": passed,
        "spot_shock_pct": round(shock_pct, 2),
        "adverse_basis_blowout_bps": round(basis_bps, 1),
        "intraday_whipsaw_jump_pct": round(whipsaw_pct, 2),
        "carry_equity_buffer_mult": cfg.carry_equity_buffer_mult,
        "perp_liq_threshold_jump_pct": round(liq_threshold_jump * 100.0, 2),
        "cross_margin_draw_pct": round(cross_margin_draw_frac * 100.0, 2),
        "margin_headroom_pct": margin_headroom_pct,
        "spot_liquidation_events": spot_liq_events,
        "isolated_liq_events": isolated_liq_events,
        "cross_liq_events": cross_liq_events,
        "zero_liquidation": zero_liquidation,
        "spot_ownbook_impact_pct": round(spot_ownbook_pnl_frac * 100.0, 2),
        "carry_ownbook_impact_pct": round(carry_ownbook_pnl_frac * 100.0, 2),
        "total_ownbook_shock_dd_pct": total_ownbook_dd_pct,
        "post_crash_equity_pct": post_crash_equity_pct,
        "portfolio_survived": post_crash_equity_pct > 75.0 and zero_liquidation,
        "holdout_rows_analysed": 0,
    }


def run_all_four_stress_tests(
    config: OwnBookConfig,
    *,
    dates: Sequence[str],
    ownbook_returns: Sequence[float] | np.ndarray,
    spy_returns: Mapping[str, float],
    bond_returns: Mapping[str, float],
    tlt_returns: Mapping[str, float] | None = None,
    effective_weights: Mapping[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run all 4 mandatory Extreme Stress Tests and return keyed by canonical stress ID."""
    _enforce_readonly_runtime()
    s1 = run_stress_1_cex_cap_25pct_insolvency(config, effective_weights=effective_weights)
    s2 = run_stress_2_funding_compression_lt3pct(config)
    s3 = run_stress_3_2022_stock_bond_crash(
        dates=dates,
        ownbook_returns=ownbook_returns,
        spy_returns=spy_returns,
        bond_returns=bond_returns,
        tlt_returns=tlt_returns,
    )
    s4 = run_stress_4_crypto_flash_crash_minus35pct(config, effective_weights=effective_weights)
    return {
        STRESS_1_ID: s1,
        STRESS_2_ID: s2,
        STRESS_3_ID: s3,
        STRESS_4_ID: s4,
    }


# ---------------------------------------------------------------------------
# OPS-4 Compatible Health Snapshot (`GREEN` / `AMBER` / `RED`)
# ---------------------------------------------------------------------------
def _ops4_finding(code: str, severity: str, detail: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "subsystem": "ownbook_shadow_ops",
        "detail": detail,
    }


def build_ops4_health_snapshot(
    *,
    weights: Mapping[str, float],
    annualized_funding_rate: float,
    stress_results: Mapping[str, Mapping[str, Any]],
    as_of_date: str = HOLDOUT_CUTOFF_INCLUSIVE,
    threshold_ann: float = FUNDING_COMPRESSION_THRESHOLD_ANN,
    max_cex_exposure: float = MAX_CEX_EXPOSURE_FRAC,
    allow_clamp: bool = False,
    current_dd_pct: float = 0.0,
    holdout_rows_analysed: int = 0,
    tbill_vehicle: str = TBILL_BUFFER_VEHICLE,
) -> dict[str, Any]:
    """Emit an OPS-4 compatible Own-Book health snapshot (`GREEN` / `AMBER` / `RED`).

    Objective Traffic Light rules:
      - `RED`: CEX > 25%, ANY of 4 stress tests failed, `holdout_rows_analysed != 0`,
               `order_send_capable != False`, or severe DD >= 20%.
      - `AMBER`: `FUNDING_COMPRESSION_ALERT` (`annualized_funding < 3.0%` -> rotated to
                 `SGOV/BIL`), `CEX_CAP_CLAMPED`, or elevated Own-Book DD watch (`>= 10%`).
      - `GREEN`: CEX `<= 25.0%`, funding `>= 3.0%`, `4/4` stress tests passed, `0` alerts,
                 `holdout_rows_analysed == 0`, `order_send_capable == False`.
    """
    _enforce_readonly_runtime()
    as_of = validate_cutoff_date(as_of_date, context="ops4_health.as_of_date")
    enforce_holdout_zero_rows(holdout_rows_analysed, context="ops4_health.holdout_rows_analysed")
    cur_dd = validate_finite_float(current_dd_pct, "current_dd_pct", minimum=0.0, maximum=100.0)

    step = evaluate_funding_compression_step(
        weights,
        annualized_funding_rate,
        threshold_ann=threshold_ann,
        max_cex_exposure=max_cex_exposure,
        allow_clamp=allow_clamp,
        tbill_vehicle=tbill_vehicle,
    )

    findings: list[dict[str, str]] = []
    active_alerts: list[str] = list(step["alerts"])

    if not step["cex_cap_compliant"] or step["effective_cex_exposure_pct"] > MAX_CEX_EXPOSURE_PCT + 1e-9:
        if CEX_CAP_BREACH_ALERT_CODE not in active_alerts:
            active_alerts.append(CEX_CAP_BREACH_ALERT_CODE)
        findings.append(
            _ops4_finding(
                CEX_CAP_BREACH_ALERT_CODE,
                TRAFFIC_RED,
                f"Effective CEX exposure {step['effective_cex_exposure_pct']:.2f}% exceeds hard 25.0% cap.",
            )
        )

    if step["was_clamped"]:
        findings.append(
            _ops4_finding(
                CEX_CAP_CLAMPED_ALERT_CODE,
                TRAFFIC_AMBER,
                f"Over-cap CEX weight was clamped down to {MAX_CEX_EXPOSURE_PCT:.1f}% and rerouted to {tbill_vehicle}.",
            )
        )

    if step["funding_compression_active"]:
        findings.append(
            _ops4_finding(
                FUNDING_COMPRESSION_ALERT_CODE,
                TRAFFIC_AMBER,
                f"Annualized funding {step['annualized_funding_rate_pct']:.2f}% < {step['threshold_pct']:.2f}%; "
                f"rotated {step['rotated_carry_to_tbill_pct']:.2f}% carry into {tbill_vehicle}.",
            )
        )

    stress_statuses: dict[str, bool] = {}
    missing_stresses: list[str] = []
    failed_stresses: list[str] = []
    for sid in ALL_STRESS_IDS:
        item = stress_results.get(sid)
        if not isinstance(item, Mapping):
            stress_statuses[sid] = False
            missing_stresses.append(sid)
        else:
            ok = bool(item.get("passed", False))
            stress_statuses[sid] = ok
            if not ok:
                failed_stresses.append(sid)

    if missing_stresses or failed_stresses:
        code = "OWNBOOK_STRESS_FAILURE"
        if code not in active_alerts:
            active_alerts.append(code)
        findings.append(
            _ops4_finding(
                code,
                TRAFFIC_RED,
                f"Extreme stress gate failed (missing={missing_stresses}, failed={failed_stresses}).",
            )
        )

    if cur_dd >= 20.0:
        code = "OWNBOOK_DRAWDOWN_RED"
        active_alerts.append(code)
        findings.append(_ops4_finding(code, TRAFFIC_RED, f"Own-Book drawdown {cur_dd:.2f}% >= 20.0% hard stop."))
    elif cur_dd >= 10.0:
        code = "OWNBOOK_DRAWDOWN_AMBER"
        active_alerts.append(code)
        findings.append(_ops4_finding(code, TRAFFIC_AMBER, f"Own-Book drawdown {cur_dd:.2f}% >= 10.0% watch."))

    red_findings = [f for f in findings if f["severity"] == TRAFFIC_RED]
    amber_findings = [f for f in findings if f["severity"] == TRAFFIC_AMBER]
    if red_findings:
        traffic_light = TRAFFIC_RED
    elif amber_findings:
        traffic_light = TRAFFIC_AMBER
    else:
        traffic_light = TRAFFIC_GREEN

    decision = dict(TRAFFIC_ACTION_MATRIX[traffic_light])
    decision["red_trigger_count"] = len(red_findings)
    decision["amber_trigger_count"] = len(amber_findings)
    decision["red_codes"] = [f["code"] for f in red_findings]
    decision["amber_codes"] = [f["code"] for f in amber_findings]

    passed_count = sum(1 for v in stress_statuses.values() if v)
    return {
        "schema": OPS4_HEALTH_SCHEMA,
        "as_of_date": as_of,
        "readonly": True,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_INCLUSIVE,
        "holdout_rows_analysed": 0,
        "traffic_light": traffic_light,
        "action": decision["action"],
        "risk_multiplier": decision["risk_multiplier"],
        "decision": decision,
        "cex_exposure_pct": step["effective_cex_exposure_pct"],
        "cex_cap_pct": MAX_CEX_EXPOSURE_PCT,
        "cex_cap_compliant": step["cex_cap_compliant"],
        "annualized_funding_rate_pct": step["annualized_funding_rate_pct"],
        "funding_compression_threshold_pct": step["threshold_pct"],
        "funding_compression_active": step["funding_compression_active"],
        "rotated_carry_to_tbill_pct": step["rotated_carry_to_tbill_pct"],
        "tbill_buffer_vehicle": tbill_vehicle,
        "current_dd_pct": round(cur_dd, 2),
        "target_weights": step["target_weights"],
        "effective_weights": step["effective_weights"],
        "active_alerts": active_alerts,
        "findings": findings,
        "stress_summary": {
            "passed": passed_count,
            "total": len(ALL_STRESS_IDS),
            "all_passed": passed_count == len(ALL_STRESS_IDS),
            "statuses": stress_statuses,
        },
    }


# ---------------------------------------------------------------------------
# End-to-End Local-Cache Orchestrator & Receipt Emitter
# ---------------------------------------------------------------------------
def run_ownbook_shadow_ops_study(
    *,
    config: OwnBookConfig | None = None,
    etf_cache_dir: Path = ETF40_CACHE_DIR,
    funding_dir: Path = FUNDING_CACHE_DIR,
    spot_cache_dir: Path = SPOT_CACHE_DIR,
    returns_dir: Path = DEFAULT_RETURNS_DIR,
    out_summary_path: Path | None = DEFAULT_SUMMARY_PATH,
    verify_holdout_lock_file: bool = True,
) -> dict[str, Any]:
    """Run complete Dev (`<= 2024-12-31`) Own-Book Shadow Ops study + 4/4 stress tests + OPS-4 snapshot."""
    _enforce_readonly_runtime()
    t0 = time.perf_counter()
    cfg = config or OwnBookConfig()
    lock_sha = assert_holdout_locked() if verify_holdout_lock_file else "OFFLINE_SYNTHETIC_NO_LOCKFILE"

    etf_data = load_etf_super_sleeve_dev_returns(
        cache_dir=etf_cache_dir,
        cutoff_date=cfg.cutoff_date,
        cost_bps_oneway=cfg.etf_cost_bps_oneway,
        ibkr_capital_usd=cfg.ibkr_capital_usd,
    )
    carry_data = load_crypto_carry_dev_series(
        funding_dir=funding_dir,
        spot_cache_dir=spot_cache_dir,
        cutoff_date=cfg.cutoff_date,
        equity_buffer_mult=cfg.carry_equity_buffer_mult,
    )
    spot_data = load_crypto_spot_dev_returns(
        returns_dir=returns_dir,
        cutoff_date=cfg.cutoff_date,
    )

    total_holdout_rows = (
        int(etf_data["holdout_rows_analysed"])
        + int(carry_data["holdout_rows_analysed"])
        + int(spot_data["holdout_rows_analysed"])
    )
    enforce_holdout_zero_rows(total_holdout_rows, context="run_ownbook_shadow_ops_study.loaders")

    composite = simulate_ownbook_composite(
        macro_etf_returns=etf_data["macro_etf_returns"],
        crypto_spot_returns=spot_data["crypto_spot_returns"],
        crypto_carry_returns=carry_data["carry_returns"],
        tbill_returns=etf_data["bil_returns"],
        funding_ann_map=carry_data["funding_ann_map"],
        config=cfg,
    )
    enforce_holdout_zero_rows(composite["holdout_rows_analysed"], context="run_ownbook_shadow_ops_study.composite")

    # Compute current Dev drawdown at end of window for OPS-4 snapshot
    eq_curve = np.cumprod(np.maximum(0.0, 1.0 + composite["guarded_returns"]))
    peak_eq = float(np.max(eq_curve)) if eq_curve.size > 0 else 1.0
    cur_dd_pct = round(max(0.0, (peak_eq - float(eq_curve[-1])) / max(peak_eq, 1e-12)) * 100.0, 2)

    stresses = run_all_four_stress_tests(
        cfg,
        dates=composite["dates"],
        ownbook_returns=composite["guarded_returns"],
        spy_returns=etf_data["spy_returns"],
        bond_returns=etf_data["ief_returns"],
        tlt_returns=etf_data["tlt_returns"],
        effective_weights=cfg.target_weights,
    )
    for sid, sres in stresses.items():
        enforce_holdout_zero_rows(sres.get("holdout_rows_analysed", -1), context=f"stress.{sid}")

    ops4_health = build_ops4_health_snapshot(
        weights=cfg.target_weights,
        annualized_funding_rate=composite["latest_funding_ann"],
        stress_results=stresses,
        as_of_date=composite["dates"][-1],
        threshold_ann=cfg.funding_compression_threshold_ann,
        max_cex_exposure=cfg.max_cex_exposure,
        current_dd_pct=cur_dd_pct,
        holdout_rows_analysed=0,
        tbill_vehicle=cfg.tbill_vehicle,
    )

    # Secondary OPS-4 verification probe: demonstrate AMBER + FUNDING_COMPRESSION_ALERT under < 3% funding
    ops4_compression_probe = build_ops4_health_snapshot(
        weights=cfg.target_weights,
        annualized_funding_rate=0.012,
        stress_results=stresses,
        as_of_date=composite["dates"][-1],
        threshold_ann=cfg.funding_compression_threshold_ann,
        max_cex_exposure=cfg.max_cex_exposure,
        current_dd_pct=cur_dd_pct,
        holdout_rows_analysed=0,
        tbill_vehicle=cfg.tbill_vehicle,
    )

    summary: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA,
        "gate_id": "W4-G08",
        "worker": "w4-m2b-ownops",
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": SPEND_VND,
            "holdout_cutoff_inclusive": HOLDOUT_CUTOFF_INCLUSIVE,
            "holdout_cutoff_exclusive": HOLDOUT_CUTOFF_EXCLUSIVE,
            "holdout_lock_sha256": lock_sha,
            "holdout_rows_analysed": 0,
            "hard_cex_cap_pct": MAX_CEX_EXPOSURE_PCT,
            "funding_compression_threshold_pct": FUNDING_COMPRESSION_THRESHOLD_PCT,
            "zero_bare_asserts": True,
        },
        "data_provenance": {
            "etf_super_sleeve_max_date": etf_data["max_date"],
            "etf_raw_holdout_rows_excluded": etf_data["raw_holdout_rows_excluded"],
            "crypto_carry_max_date": carry_data["max_date"],
            "crypto_carry_raw_holdout_rows_excluded": carry_data["raw_holdout_rows_excluded"],
            "crypto_spot_max_date": spot_data["max_date"],
            "crypto_spot_raw_holdout_rows_excluded": spot_data["raw_holdout_rows_excluded"],
            "composite_window": composite["window"],
            "composite_business_days": composite["n_business_days"],
            "reused_modules": [
                "tooling/ai-engines/quant_factory/ownbook_etf_super_sleeve.py",
                "projects/quant-trading/src/quant_lab/funding_carry_v2.py",
                "tooling/ai-engines/quant_factory/live_ops/daily_live_ops_pipeline.py",
                "tooling/ai-engines/quant_core/holdout_guard.py",
                "tooling/ai-engines/quant_core/tca.py",
                "tooling/ai-engines/quant_factory/portfolio_allocator.py",
            ],
        },
        "ownbook_dev_performance": {
            "target_weights": dict(cfg.target_weights),
            "guarded_metrics": composite["guarded_metrics"],
            "static_unrotated_metrics": composite["static_metrics"],
            "sleeve_metrics": composite["sleeve_metrics"],
            "max_realized_cex_exposure_pct": composite["max_realized_cex_exposure_pct"],
            "mean_realized_cex_exposure_pct": composite["mean_realized_cex_exposure_pct"],
            "funding_compression_days": composite["funding_compression_days"],
            "funding_compression_pct_days": composite["funding_compression_pct_days"],
            "carry_rotation_events": composite["carry_rotation_events"],
            "carry_v2_margin_stress_dev": carry_data["margin_stress"],
            "carry_v2_dev_metrics": carry_data["carry_metrics_dev"],
            "ibkr_integer_share_audit_dev": etf_data["ibkr_lot_audit_dev"],
        },
        "extreme_stress_tests": stresses,
        "ops4_health_snapshot": ops4_health,
        "ops4_compression_amber_probe": {
            "traffic_light": ops4_compression_probe["traffic_light"],
            "active_alerts": ops4_compression_probe["active_alerts"],
            "rotated_carry_to_tbill_pct": ops4_compression_probe["rotated_carry_to_tbill_pct"],
            "effective_cex_exposure_pct": ops4_compression_probe["cex_exposure_pct"],
            "effective_weights": ops4_compression_probe["effective_weights"],
        },
        "runtime_seconds": round(time.perf_counter() - t0, 3),
    }

    if out_summary_path is not None:
        receipt = write_atomic_sha256_json(out_summary_path, summary)
        summary["report_sha256"] = receipt["report_sha256"]
    else:
        summary["report_sha256"] = canonical_payload_sha256(summary)

    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave 4 Own-Book Shadow Operations Engine (W4-G08) — Strictly Dev <= 2024-12-31, OrderSend=0"
    )
    parser.add_argument("--cutoff-date", default=HOLDOUT_CUTOFF_INCLUSIVE, help="Inclusive Dev cutoff (<= 2024-12-31)")
    parser.add_argument("--ibkr-capital-usd", type=float, default=50_000.0, help="IBKR capital tier for lot audit")
    parser.add_argument("--out-summary", default=str(DEFAULT_SUMMARY_PATH), help="Output JSON path for summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    cfg = OwnBookConfig(cutoff_date=args.cutoff_date, ibkr_capital_usd=args.ibkr_capital_usd)
    out_path = Path(args.out_summary)
    res = run_ownbook_shadow_ops_study(config=cfg, out_summary_path=out_path)
    print(
        json.dumps(
            {
                "status": "PASS" if res["ops4_health_snapshot"]["stress_summary"]["all_passed"] else "FAIL",
                "output_summary": str(out_path),
                "report_sha256": res["report_sha256"],
                "holdout_rows_analysed": res["invariants"]["holdout_rows_analysed"],
                "order_send_capable": res["invariants"]["order_send_capable"],
                "traffic_light": res["ops4_health_snapshot"]["traffic_light"],
                "cex_exposure_pct": res["ops4_health_snapshot"]["cex_exposure_pct"],
                "annualized_funding_rate_pct": res["ops4_health_snapshot"]["annualized_funding_rate_pct"],
                "stress_statuses": res["ops4_health_snapshot"]["stress_summary"]["statuses"],
                "runtime_seconds": res["runtime_seconds"],
            },
            indent=2,
        )
    )
    return 0


__all__ = [
    "ALL_STRESS_IDS",
    "CANONICAL_OWNBOOK_SLEEVES",
    "CEX_CAP_BREACH_ALERT_CODE",
    "CEX_CAP_CLAMPED_ALERT_CODE",
    "CEX_SLEEVE_IDS",
    "DEFAULT_AUDIT_RECEIPT_PATH",
    "DEFAULT_DROPBOX_PATH",
    "DEFAULT_OWNBOOK_WEIGHTS",
    "DEFAULT_SUMMARY_PATH",
    "FUNDING_COMPRESSION_ALERT_CODE",
    "FUNDING_COMPRESSION_THRESHOLD_ANN",
    "FUNDING_COMPRESSION_THRESHOLD_PCT",
    "HOLDOUT_CUTOFF_EXCLUSIVE",
    "HOLDOUT_CUTOFF_INCLUSIVE",
    "MAX_CEX_EXPOSURE_FRAC",
    "MAX_CEX_EXPOSURE_PCT",
    "OPS4_HEALTH_SCHEMA",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "OwnBookConfig",
    "SLEEVE_CASH_TBILL",
    "SLEEVE_CRYPTO_CARRY",
    "SLEEVE_CRYPTO_SPOT",
    "SLEEVE_MACRO_ETF",
    "SPEND_VND",
    "STRESS_1_ID",
    "STRESS_2_ID",
    "STRESS_3_ID",
    "STRESS_4_ID",
    "SUMMARY_SCHEMA",
    "TBILL_BUFFER_VEHICLE",
    "build_ops4_health_snapshot",
    "enforce_ownbook_pre_holdout",
    "evaluate_funding_compression_step",
    "load_crypto_carry_dev_series",
    "load_crypto_spot_dev_returns",
    "load_etf_super_sleeve_dev_returns",
    "run_all_four_stress_tests",
    "run_ownbook_shadow_ops_study",
    "run_stress_1_cex_cap_25pct_insolvency",
    "run_stress_2_funding_compression_lt3pct",
    "run_stress_3_2022_stock_bond_crash",
    "run_stress_4_crypto_flash_crash_minus35pct",
    "simulate_ownbook_composite",
    "validate_cutoff_date",
    "validate_finite_float",
    "validate_ownbook_allocation",
]


if __name__ == "__main__":
    raise SystemExit(main())
