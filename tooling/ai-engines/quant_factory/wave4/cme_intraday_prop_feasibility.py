"""Wave 4 (`W4-G15`): 4-Firm CME Futures Intraday Prop Feasibility Engine.

Compares 4 major CME Futures prop firms (`Topstep`, `MFFU / MyFundedFutures`,
`TakeProfitTrader`, `Tradeify`) head-to-head against incumbent CFD prop baselines
(`FTMO Standard 10K` and `FTMO Standard 100K`) strictly on sealed Dev `< 2025-01-01`
data (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `holdout_rows_analysed = 0`).

Hard invariants (ZERO exceptions):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0` (offline research/audit only).
  - ZERO bare Python `assert` statements (`[ARCH-02]`, 100% safe under `python -O`).
  - ZERO `MetaTrader5` imports; ZERO top-level `scipy` imports (`[ARCH-01]`, `[ARCH-07]`).
  - Holdout `2025+` 100% SEALED via `quant_core.holdout_guard.enforce_pre_holdout_dates`.
  - Windows `tzdata`-free PEP-495 DST resolver for `America/Chicago` (`15:10 CT` flat close).
  - Honest provenance tags (`verified_utc`, `TERMS_VERIFIED_EXECUTION_UNMEASURED`) for
    all 4 CME firms where live broker fill telemetry is unmeasured.
  - Strict `G12` compliance: zero proactive firm-support contact nudges.
  - All Wave 4 JSON outputs written exclusively under `.runtime/offensive4/futures/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from datetime import time as dt_time
from enum import StrEnum
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
from numba import njit

AI_ENGINES_DIR: Path = Path(__file__).resolve().parents[2]
ROOT: Path = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
)

from quant_factory.cme_futures_prop_lab import (  # noqa: E402
    CME_CACHE_DIR,
    DEV_CUTOFF_DATE,
    SLEEVE5_RETURNS_PATH,
    load_cme_dev_d1_strict,
)
from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE, ORDER_SEND_CAPABLE  # noqa: E402

# ---------------------------------------------------------------------------
# Constants, Schema & SSOT Paths
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave4-cme-intraday-feasibility-v1"
ORDER_SEND_COUNT: int = 0
RULES_VERIFIED_UTC: str = "2026-11-27T18:35:00Z"
CME_EXECUTION_STATUS: str = "TERMS_VERIFIED_EXECUTION_UNMEASURED"
FTMO_EXECUTION_STATUS: str = "MEASURED_DEMO_EXECUTION"
RESOLUTION_LABEL_VI: str = "XẤP XỈ CẤP NGÀY"
RESOLUTION_TAG: str = "APPROX_DAILY_RESOLUTION"
EVIDENCE_STAGE: str = "BACKTEST_DEV_SEALED_LE_2024"

DEFAULT_SSOT_DIR: Path = AI_ENGINES_DIR / "configs" / "ssot"
DEFAULT_FX_RATES_PATH: Path = DEFAULT_SSOT_DIR / "fx_rates.json"
DEFAULT_FIRMS_CATALOG_PATH: Path = DEFAULT_SSOT_DIR / "firms_catalog.json"
DEFAULT_OUTPUT_DIR: Path = ROOT / ".runtime" / "offensive4" / "futures"
DEFAULT_OUTPUT_JSON: Path = DEFAULT_OUTPUT_DIR / "wave4_cme_intraday_feasibility.json"

TZ_CHICAGO: str = "America/Chicago"
CME_FLAT_CLOSE_HOUR_CT: int = 15
CME_FLAT_CLOSE_MINUTE_CT: int = 10
CME_REOPEN_HOUR_CT: int = 17
CME_REOPEN_MINUTE_CT: int = 0

TRADING_DAYS_PER_MONTH: int = 21
TRADING_DAYS_PER_YEAR: int = 252
DEFAULT_HORIZON_DAYS: int = 504  # 24 trading months
DEFAULT_BLOCK_LEN: int = 5
CALENDAR_DAYS_PER_TRADING_DAY: float = 365.25 / 252.0
WILSON_Z_95: float = 1.959963984540054


class TrailingDDMode(StrEnum):
    EOD_TRAILING = "EOD_TRAILING"
    INTRADAY_UNREALIZED_TRAILING = "INTRADAY_UNREALIZED_TRAILING"
    STATIC_BALANCE = "STATIC_BALANCE"


class VNKycStatus(StrEnum):
    ALLOWED_FULL_VN = "ALLOWED_FULL_VN"
    ALLOWED_XFA_ONLY = "ALLOWED_XFA_ONLY"
    RESTRICTED_VN_PROHIBITED = "RESTRICTED_VN_PROHIBITED"
    UNVERIFIED_VN_STATUS = "UNVERIFIED_VN_STATUS"


class BreachKind(StrEnum):
    NONE = "NONE"
    BOT_AUTO_KILL = "BOT_AUTO_KILL"
    FIRM_SOFT_DLL_PAUSE = "FIRM_SOFT_DLL_PAUSE"
    FIRM_HARD_BREACH = "FIRM_HARD_BREACH"


# ---------------------------------------------------------------------------
# Strict Fail-Closed Numeric Validators (Bug Pattern #3: reject bool/NaN/Inf)
# ---------------------------------------------------------------------------


def _require_finite_float(
    value: Any,
    name: str,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"{name} must be a finite numeric value (non-bool), got {value!r} ({type(value).__name__})")
    fv = float(value)
    if not math.isfinite(fv):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if min_value is not None and fv < min_value:
        raise ValueError(f"{name}={fv} < minimum {min_value}")
    if max_value is not None and fv > max_value:
        raise ValueError(f"{name}={fv} > maximum {max_value}")
    return fv


def _require_int(
    value: Any,
    name: str,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer (non-bool), got {value!r} ({type(value).__name__})")
    iv = int(value)
    if min_value is not None and iv < min_value:
        raise ValueError(f"{name}={iv} < minimum {min_value}")
    if max_value is not None and iv > max_value:
        raise ValueError(f"{name}={iv} > maximum {max_value}")
    return iv


def wilson_upper_95(successes: int, trials: int) -> float | None:
    """Exact 95% Wilson score upper bound in `[0.0, 1.0]` (zero scipy)."""
    s = _require_int(successes, "successes", min_value=0)
    n = _require_int(trials, "trials", min_value=0)
    if n == 0:
        return None
    if s > n:
        raise ValueError(f"successes ({s}) > trials ({n})")
    p_hat = s / n
    z2 = WILSON_Z_95 * WILSON_Z_95
    denom = 1.0 + z2 / n
    center = p_hat + z2 / (2.0 * n)
    rad = WILSON_Z_95 * math.sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n)
    return min(1.0, (center + rad) / denom)


# ---------------------------------------------------------------------------
# Windows tzdata-Free PEP-495 DST Resolver for America/Chicago (15:10 CT)
# ---------------------------------------------------------------------------


def _nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


class _ChicagoDstTzInfo(tzinfo):
    """Deterministic stdlib PEP-495 DST tzinfo for `America/Chicago` (US 2007+ statute).

    Guarantees zero dependency on Windows `tzdata`:
      - Standard Time (`CST`): UTC-6
      - Daylight Saving Time (`CDT`): UTC-5
      - Spring Forward: 2nd Sunday of March at 02:00 CST (08:00 UTC) -> 03:00 CDT
      - Fall Back: 1st Sunday of November at 02:00 CDT (07:00 UTC) -> 01:00 CST (`fold=1`)
    """

    key: str = TZ_CHICAGO
    _STD_OFFSET: timedelta = timedelta(hours=-6)
    _DST_DELTA: timedelta = timedelta(hours=1)

    def _is_dst_utc_naive(self, utc_naive: datetime) -> bool:
        yr = utc_naive.year
        # 2nd Sunday of March 02:00 CST == 08:00 UTC
        spring_utc = datetime.combine(_nth_weekday_of_month(yr, 3, 6, 2), dt_time(2, 0)) - self._STD_OFFSET
        # 1st Sunday of November 02:00 CDT == 07:00 UTC
        fall_utc = (
            datetime.combine(_nth_weekday_of_month(yr, 11, 6, 1), dt_time(2, 0))
            - self._STD_OFFSET
            - self._DST_DELTA
        )
        return spring_utc <= utc_naive < fall_utc

    def _resolve_local_is_dst(self, dt: datetime) -> bool:
        loc = dt.replace(tzinfo=None)
        u_dst = loc - (self._STD_OFFSET + self._DST_DELTA)
        u_std = loc - self._STD_OFFSET
        valid_dst = self._is_dst_utc_naive(u_dst)
        valid_std = not self._is_dst_utc_naive(u_std)
        if valid_dst and not valid_std:
            return True
        if valid_std and not valid_dst:
            return False
        if valid_dst and valid_std:
            # Fall-back ambiguous 01:00..01:59 hour: fold=0 is CDT (earlier), fold=1 is CST (later)
            return dt.fold == 0
        # Spring-forward non-existent 02:00..02:59 gap: PEP-495 fold=0 uses pre-transition CST, fold=1 uses CDT
        return dt.fold == 1

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return None
        return self._STD_OFFSET + (self._DST_DELTA if self._resolve_local_is_dst(dt) else timedelta(0))

    def dst(self, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return None
        return self._DST_DELTA if self._resolve_local_is_dst(dt) else timedelta(0)

    def tzname(self, dt: datetime | None) -> str | None:
        if dt is None:
            return self.key
        return "CDT" if self._resolve_local_is_dst(dt) else "CST"

    def fromutc(self, dt: datetime) -> datetime:
        if dt.tzinfo is not self:
            raise ValueError("fromutc: dt.tzinfo is not _ChicagoDstTzInfo")
        u = dt.replace(tzinfo=None)
        is_dst_now = self._is_dst_utc_naive(u)
        off = self._STD_OFFSET + (self._DST_DELTA if is_dst_now else timedelta(0))
        local_naive = u + off
        is_fold = (not is_dst_now) and self._is_dst_utc_naive(u - self._DST_DELTA)
        return local_naive.replace(tzinfo=self, fold=1 if is_fold else 0)

    def __repr__(self) -> str:
        return "_ChicagoDstTzInfo('America/Chicago')"


_CHICAGO_FALLBACK_TZ: tzinfo = _ChicagoDstTzInfo()
_CHICAGO_TZ_CACHE: tzinfo | None = None


def resolve_chicago_tz(*, prefer_fallback: bool = False) -> tzinfo:
    """Resolve `America/Chicago` via `ZoneInfo`, falling back seamlessly to PEP-495 stdlib DST."""
    global _CHICAGO_TZ_CACHE
    if prefer_fallback:
        return _CHICAGO_FALLBACK_TZ
    if _CHICAGO_TZ_CACHE is not None:
        return _CHICAGO_TZ_CACHE
    try:
        tz: tzinfo = ZoneInfo(TZ_CHICAGO)
    except (ZoneInfoNotFoundError, ModuleNotFoundError):
        tz = _CHICAGO_FALLBACK_TZ
    _CHICAGO_TZ_CACHE = tz
    return tz


@dataclass(frozen=True)
class CMEFlatCloseDecision:
    utc_iso: str
    chicago_iso: str
    tz_abbr: str
    utc_offset_hours: int
    is_dst: bool
    fold: int
    weekday_ct: int  # 0=Mon..6=Sun
    open_contracts: int
    in_blackout_window: bool
    in_pre_close_buffer: bool
    must_flatten_now: bool
    breach_if_position_open: bool
    action: str
    seconds_to_1510_ct: float
    order_send_capable: bool = False


def evaluate_cme_1510_ct_flatten(
    dt_aware: datetime,
    *,
    open_contracts: int = 0,
    close_buffer_sec: int = 60,
    prefer_fallback_tz: bool = False,
) -> CMEFlatCloseDecision:
    """Evaluate CME Futures prop mandatory `15:10 CT` flat-close rule on any timezone-aware timestamp.

    Rules modeled:
      - Daily maintenance blackout: `[15:10:00 CT, 17:00:00 CT)` Mon–Thu (MUST be flat by `15:10 CT`).
      - Weekend closure blackout: Friday `15:10:00 CT` through Sunday `17:00:00 CT`.
      - Pre-close flatten buffer: `[15:10:00 CT - close_buffer_sec, 15:10:00 CT)` Mon–Fri.
      - Fails closed (`ValueError`) on naive datetimes, negative contracts, or invalid buffer.
    """
    if not isinstance(dt_aware, datetime) or dt_aware.tzinfo is None or dt_aware.utcoffset() is None:
        raise ValueError(f"dt_aware must be a timezone-aware datetime, got {dt_aware!r}")
    contracts = _require_int(open_contracts, "open_contracts", min_value=0)
    buf_sec = _require_int(close_buffer_sec, "close_buffer_sec", min_value=0, max_value=3600)

    dt_utc = dt_aware.astimezone(UTC)
    chi_tz = resolve_chicago_tz(prefer_fallback=prefer_fallback_tz)
    dt_chi = dt_utc.astimezone(chi_tz)

    wd = dt_chi.weekday()  # 0=Mon .. 4=Fri, 5=Sat, 6=Sun
    sec_of_day = dt_chi.hour * 3600 + dt_chi.minute * 60 + dt_chi.second + dt_chi.microsecond / 1_000_000.0
    cutoff_sec = float(CME_FLAT_CLOSE_HOUR_CT * 3600 + CME_FLAT_CLOSE_MINUTE_CT * 60)  # 15:10 CT = 54600s
    reopen_sec = float(CME_REOPEN_HOUR_CT * 3600 + CME_REOPEN_MINUTE_CT * 60)  # 17:00 CT = 61200s

    if wd == 5:  # Saturday: closed all day
        in_blackout = True
    elif wd == 6:  # Sunday: closed until 17:00 CT reopen
        in_blackout = sec_of_day < reopen_sec
    elif wd == 4:  # Friday: closed from 15:10 CT onward
        in_blackout = sec_of_day >= cutoff_sec
    else:  # Mon..Thu: daily maintenance blackout [15:10 CT, 17:00 CT)
        in_blackout = cutoff_sec <= sec_of_day < reopen_sec

    in_buffer = (wd in (0, 1, 2, 3, 4)) and (cutoff_sec - buf_sec <= sec_of_day < cutoff_sec)

    # Compute exact seconds until next 15:10 CT cutoff (0.0 if already in blackout)
    if in_blackout:
        sec_to_cutoff = 0.0
    elif wd == 6:
        # Sunday >= 17:00 CT -> Monday 15:10 CT
        sec_to_cutoff = (86400.0 - sec_of_day) + cutoff_sec
    elif sec_of_day < cutoff_sec:
        sec_to_cutoff = cutoff_sec - sec_of_day
    else:
        # Mon..Thu >= 17:00 CT -> next day 15:10 CT
        sec_to_cutoff = (86400.0 - sec_of_day) + cutoff_sec

    breach_risk = in_blackout and contracts > 0
    must_flatten = (in_blackout or in_buffer) and contracts > 0

    if breach_risk:
        action = "FORCE_FLAT_VIOLATION_RISK"
    elif in_blackout:
        action = "SESSION_CLOSED_FLAT"
    elif must_flatten:
        action = "PRE_CLOSE_FLATTEN_REQUIRED"
    else:
        action = "ALLOW_TRADING"

    off = dt_chi.utcoffset()
    dst_val = dt_chi.dst()
    off_hours = int(round(off.total_seconds() / 3600.0)) if off is not None else -6
    is_dst = bool(dst_val is not None and dst_val.total_seconds() > 0)

    return CMEFlatCloseDecision(
        utc_iso=dt_utc.isoformat().replace("+00:00", "Z"),
        chicago_iso=dt_chi.isoformat(),
        tz_abbr=dt_chi.tzname() or ("CDT" if is_dst else "CST"),
        utc_offset_hours=off_hours,
        is_dst=is_dst,
        fold=int(dt_chi.fold),
        weekday_ct=wd,
        open_contracts=contracts,
        in_blackout_window=in_blackout,
        in_pre_close_buffer=in_buffer,
        must_flatten_now=must_flatten,
        breach_if_position_open=breach_risk,
        action=action,
        seconds_to_1510_ct=round(sec_to_cutoff, 3),
        order_send_capable=False,
    )


def get_1510_ct_utc_cutoff(trading_day: date, *, prefer_fallback_tz: bool = False) -> datetime:
    """Return exact UTC `datetime` corresponding to `15:10:00 America/Chicago` on `trading_day`.

    Winter (CST, UTC-6) -> `21:10:00Z`; Summer (CDT, UTC-5) -> `20:10:00Z`.
    """
    chi_tz = resolve_chicago_tz(prefer_fallback=prefer_fallback_tz)
    local_cutoff = datetime(
        trading_day.year,
        trading_day.month,
        trading_day.day,
        CME_FLAT_CLOSE_HOUR_CT,
        CME_FLAT_CLOSE_MINUTE_CT,
        0,
        tzinfo=chi_tz,
    )
    return local_cutoff.astimezone(UTC)


def apply_1510_ct_intraday_flatten_to_positions(
    timestamps_utc: Sequence[datetime],
    desired_contracts: Sequence[int],
    *,
    close_buffer_sec: int = 60,
    prefer_fallback_tz: bool = False,
) -> dict[str, Any]:
    """Enforce mandatory `15:10 CT` flat rule across a bar stream, returning flattened schedule & audit counts."""
    if len(timestamps_utc) != len(desired_contracts):
        raise ValueError(
            f"Length mismatch: timestamps_utc ({len(timestamps_utc)}) != desired_contracts ({len(desired_contracts)})"
        )
    effective: list[int] = []
    forced_flattens = 0
    blocked_entries = 0
    dst_days_seen: set[str] = set()
    std_days_seen: set[str] = set()

    prev_eff = 0
    for ts, want in zip(timestamps_utc, desired_contracts, strict=True):
        want_i = _require_int(want, "desired_contracts_elem", min_value=0)
        dec = evaluate_cme_1510_ct_flatten(
            ts,
            open_contracts=max(prev_eff, want_i),
            close_buffer_sec=close_buffer_sec,
            prefer_fallback_tz=prefer_fallback_tz,
        )
        day_key = dec.chicago_iso[:10]
        if dec.is_dst:
            dst_days_seen.add(day_key)
        else:
            std_days_seen.add(day_key)

        if dec.in_blackout_window or dec.in_pre_close_buffer:
            if prev_eff > 0:
                forced_flattens += 1
            elif want_i > 0:
                blocked_entries += 1
            eff = 0
        else:
            eff = want_i
        effective.append(eff)
        prev_eff = eff

    return {
        "effective_contracts": effective,
        "forced_flatten_count": forced_flattens,
        "blocked_entry_count": blocked_entries,
        "dst_days_count": len(dst_days_seen),
        "std_days_count": len(std_days_seen),
        "order_send_count": ORDER_SEND_COUNT,
    }


# ---------------------------------------------------------------------------
# Exact EOD Trailing DD vs Intraday Unrealized Trailing DD State Machine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DDTransitionEvent:
    step_index: int
    mode: str
    equity_pnl_usd: float
    hwm_usd: float
    floor_usd: float
    margin_to_floor_usd: float
    gap_through_usd: float
    breach_kind: str
    breached: bool
    dll_paused: bool
    floor_locked: bool


class CMEPropDDStateMachine:
    """Exact two-sided boundary state machine for EOD Trailing vs Intraday Unrealized Trailing DD.

    Semantics (relative PnL where `0.0` = initial account balance):
      - Initial floor = `-max_dd_usd` (e.g., `-2,000.0` on a 50K account).
      - Floor locks permanently at `lock_floor_pnl_usd` (`0.0` for Topstep/TPT; `+100.0` for MFFU/Tradeify)
        once `hwm >= max_dd_usd + lock_floor_pnl_usd` (or upon first payout if `lock_on_first_payout=True`).
      - **Conservative breach rule**: `equity_pnl <= floor_usd` -> `FIRM_HARD_BREACH`:
          * `floor + 0.01 USD` -> SAFE (`margin = +0.01`)
          * `floor + 0.00 USD` -> BREACH (`margin = 0.00`, conservative `<=` model vs firm `<` boundary documented)
          * `floor - 0.01 USD` -> BREACH (`margin = -0.01`, `gap_through = 0.01`)
          * `floor - 250.00 USD` -> GAP-THROUGH BREACH (`margin = -250.00`, `gap_through = 250.00`)
      - **`EOD_TRAILING`**:
          * Real-time intraday low IS checked against the current fixed-for-the-day floor.
          * High-water mark (`hwm`) and floor update ONLY at End-of-Day (`15:10 CT` flat close)!
      - **`INTRADAY_UNREALIZED_TRAILING`** (TakeProfitTrader PRO):
          * High-water mark (`hwm`) and floor ratchet upward IMMEDIATELY on intraday unrealized equity peaks!
          * Subsequent intraday drawdown is evaluated immediately against the newly ratcheted floor!
      - Cleanly separates `BOT_AUTO_KILL` (internal protective stop) vs `FIRM_SOFT_DLL_PAUSE`
        vs `FIRM_HARD_BREACH` (Law 13).
    """

    def __init__(
        self,
        *,
        mode: TrailingDDMode,
        max_dd_usd: float,
        lock_floor_pnl_usd: float = 0.0,
        firm_daily_loss_limit_usd: float | None = None,
        daily_loss_is_hard_breach: bool = False,
        bot_daily_kill_usd: float | None = None,
    ) -> None:
        if not isinstance(mode, TrailingDDMode):
            raise ValueError(f"mode must be TrailingDDMode, got {mode!r}")
        self.mode: TrailingDDMode = mode
        self.max_dd_usd: float = _require_finite_float(max_dd_usd, "max_dd_usd", min_value=1.0)
        self.lock_floor_pnl_usd: float = _require_finite_float(
            lock_floor_pnl_usd, "lock_floor_pnl_usd", min_value=0.0
        )
        self.firm_daily_loss_limit_usd: float | None = (
            None
            if firm_daily_loss_limit_usd is None
            else _require_finite_float(firm_daily_loss_limit_usd, "firm_daily_loss_limit_usd", min_value=1.0)
        )
        self.daily_loss_is_hard_breach: bool = bool(daily_loss_is_hard_breach)
        self.bot_daily_kill_usd: float | None = (
            None
            if bot_daily_kill_usd is None
            else _require_finite_float(bot_daily_kill_usd, "bot_daily_kill_usd", min_value=1.0)
        )

        self.hwm_usd: float = 0.0
        self.floor_usd: float = -self.max_dd_usd
        self.realized_pnl_usd: float = 0.0
        self.day_start_pnl_usd: float = 0.0
        self.breached: bool = False
        self.breach_kind: BreachKind = BreachKind.NONE
        self.floor_locked: bool = False
        self.step_count: int = 0
        self.bot_auto_kill_count: int = 0
        self.soft_dll_pause_count: int = 0
        self.hard_breach_count: int = 0

    def _ratchet_floor(self, candidate_hwm: float) -> None:
        if candidate_hwm > self.hwm_usd:
            self.hwm_usd = candidate_hwm
            if self.mode != TrailingDDMode.STATIC_BALANCE:
                proposed = min(self.lock_floor_pnl_usd, self.hwm_usd - self.max_dd_usd)
                if proposed > self.floor_usd:
                    self.floor_usd = proposed
                if self.floor_usd >= self.lock_floor_pnl_usd - 1e-12:
                    self.floor_usd = self.lock_floor_pnl_usd
                    self.floor_locked = True

    def lock_floor_after_payout(self) -> None:
        """Lock trailing floor permanently at `lock_floor_pnl_usd` (e.g., Topstep XFA after Payout #1)."""
        if self.floor_usd < self.lock_floor_pnl_usd:
            self.floor_usd = self.lock_floor_pnl_usd
        self.floor_locked = True

    def start_new_session(self) -> None:
        """Reset intraday session anchor at 17:00 CT reopen."""
        self.day_start_pnl_usd = self.realized_pnl_usd

    def step_tick(self, equity_pnl_usd: float, *, is_eod_close: bool = False) -> DDTransitionEvent:
        """Process a single real-time equity tick (or EOD flat close)."""
        eq = _require_finite_float(equity_pnl_usd, "equity_pnl_usd")
        self.step_count += 1
        if self.breached:
            margin = eq - self.floor_usd
            return DDTransitionEvent(
                step_index=self.step_count,
                mode=self.mode.value,
                equity_pnl_usd=eq,
                hwm_usd=self.hwm_usd,
                floor_usd=self.floor_usd,
                margin_to_floor_usd=round(margin, 6),
                gap_through_usd=round(max(0.0, -margin), 6),
                breach_kind=self.breach_kind.value,
                breached=True,
                dll_paused=False,
                floor_locked=self.floor_locked,
            )

        # Intraday unrealized trailing updates HWM & floor live on EVERY tick
        if self.mode == TrailingDDMode.INTRADAY_UNREALIZED_TRAILING:
            self._ratchet_floor(eq)

        margin = eq - self.floor_usd
        gap_through = max(0.0, -margin)
        day_pnl = eq - self.day_start_pnl_usd

        # 1. Hard MLL/Trailing DD check (strict conservative <= boundary)
        if eq <= self.floor_usd:
            self.breached = True
            self.breach_kind = BreachKind.FIRM_HARD_BREACH
            self.hard_breach_count += 1
            return DDTransitionEvent(
                step_index=self.step_count,
                mode=self.mode.value,
                equity_pnl_usd=eq,
                hwm_usd=self.hwm_usd,
                floor_usd=self.floor_usd,
                margin_to_floor_usd=round(margin, 6),
                gap_through_usd=round(gap_through, 6),
                breach_kind=self.breach_kind.value,
                breached=True,
                dll_paused=False,
                floor_locked=self.floor_locked,
            )

        # 2. Daily Loss Limit & Bot Auto-Kill checks
        dll_paused = False
        step_kind = BreachKind.NONE
        if self.firm_daily_loss_limit_usd is not None and day_pnl <= -self.firm_daily_loss_limit_usd:
            if self.daily_loss_is_hard_breach:
                self.breached = True
                self.breach_kind = BreachKind.FIRM_HARD_BREACH
                self.hard_breach_count += 1
                step_kind = BreachKind.FIRM_HARD_BREACH
            else:
                dll_paused = True
                self.soft_dll_pause_count += 1
                step_kind = BreachKind.FIRM_SOFT_DLL_PAUSE
        elif self.bot_daily_kill_usd is not None and day_pnl <= -self.bot_daily_kill_usd:
            dll_paused = True
            self.bot_auto_kill_count += 1
            step_kind = BreachKind.BOT_AUTO_KILL

        # 3. EOD Trailing updates HWM & floor ONLY at 15:10 CT flat close (if not breached)
        if is_eod_close and not self.breached:
            self.realized_pnl_usd = eq
            if self.mode == TrailingDDMode.EOD_TRAILING:
                self._ratchet_floor(eq)

        return DDTransitionEvent(
            step_index=self.step_count,
            mode=self.mode.value,
            equity_pnl_usd=eq,
            hwm_usd=self.hwm_usd,
            floor_usd=self.floor_usd,
            margin_to_floor_usd=round(eq - self.floor_usd, 6),
            gap_through_usd=round(max(0.0, self.floor_usd - eq), 6),
            breach_kind=step_kind.value,
            breached=self.breached,
            dll_paused=dll_paused,
            floor_locked=self.floor_locked,
        )

    def step_session_bar(
        self,
        *,
        intraday_high_pnl_usd: float,
        intraday_low_pnl_usd: float,
        eod_close_pnl_usd: float,
    ) -> DDTransitionEvent:
        """Process a full trading session `(high, low, eod_close)` conservatively.

        Conservative worst-case intrabar ordering:
          - For `INTRADAY_UNREALIZED_TRAILING`: peak occurs BEFORE trough so HWM ratchets up first,
            testing whether subsequent giveback breaches the newly ratcheted intraday floor!
          - For `EOD_TRAILING`: trough is checked against the fixed-for-day floor; if survived,
            EOD close updates HWM and next-day floor at 15:10 CT!
        """
        hi = _require_finite_float(intraday_high_pnl_usd, "intraday_high_pnl_usd")
        lo = _require_finite_float(intraday_low_pnl_usd, "intraday_low_pnl_usd")
        cl = _require_finite_float(eod_close_pnl_usd, "eod_close_pnl_usd")
        if lo > hi + 1e-9:
            raise ValueError(f"intraday_low_pnl_usd ({lo}) > intraday_high_pnl_usd ({hi})")
        if cl < lo - 1e-9 or cl > hi + 1e-9:
            raise ValueError(f"eod_close_pnl_usd ({cl}) outside [low={lo}, high={hi}]")

        self.start_new_session()
        if self.mode == TrailingDDMode.INTRADAY_UNREALIZED_TRAILING:
            ev_hi = self.step_tick(hi, is_eod_close=False)
            if ev_hi.breached:
                return ev_hi
        ev_lo = self.step_tick(lo, is_eod_close=False)
        if ev_lo.breached:
            return ev_lo
        return self.step_tick(cl, is_eod_close=True)


# ---------------------------------------------------------------------------
# Verified 4-Firm CME Futures Prop Rule Catalog + VN KYC Matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CMEFuturesPropTierSpec:
    tier_id: str
    firm_id: str
    firm_display_name: str
    program_name: str
    nominal_usd: float
    is_straight_to_funded: bool
    profit_target_usd: float
    max_dd_usd: float
    eval_dd_mode: str
    funded_dd_mode: str
    lock_floor_above_initial_usd: float
    daily_loss_limit_usd: float
    daily_loss_is_hard_breach: bool
    eval_consistency_max_day_share: float
    funded_consistency_max_day_share: float
    min_eval_trading_days: int
    monthly_sub_usd: float  # 0.0 for one-time fee tiers
    one_time_fee_usd: float  # 0.0 for recurring monthly tiers
    activation_fee_usd: float
    reset_fee_usd: float
    max_minis: int
    max_micros: int
    scaling_plan_summary: str
    mandatory_flat_ct: str
    payout_min_win_days: int
    payout_win_day_threshold_usd: float
    payout_min_buffer_usd: float
    payout_max_withdraw_share: float
    payout_cap_per_request_usd: float
    payout_cadence_days: int  # 1 = daily eligible (TPT PRO), 5 = win-day cycle, 14 = biweekly
    first_100pct_split_cap_usd: float
    post_cap_split_frac: float
    news_restricted_funded: bool
    vn_kyc_status: str
    vn_kyc_eligible: bool
    vn_live_funded_eligible: bool
    vn_kyc_notes: str
    execution_status: str
    verified_utc: str
    source_urls: tuple[str, ...]
    max_attempts: int = 8
    eval_scale_default: float = 1.5
    funded_scale_default: float = 1.0


CME_4FIRM_CATALOG: dict[str, CMEFuturesPropTierSpec] = {
    # --- 1. TOPSTEP (50K / 100K / 150K Trading Combine -> XFA) ---
    "topstep_50k_combine": CMEFuturesPropTierSpec(
        tier_id="topstep_50k_combine",
        firm_id="topstep",
        firm_display_name="Topstep",
        program_name="50K Trading Combine -> XFA (Standard Path)",
        nominal_usd=50_000.0,
        is_straight_to_funded=False,
        profit_target_usd=3_000.0,
        max_dd_usd=2_000.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        lock_floor_above_initial_usd=0.0,
        daily_loss_limit_usd=1_000.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.50,
        funded_consistency_max_day_share=0.0,
        min_eval_trading_days=2,
        monthly_sub_usd=49.0,
        one_time_fee_usd=0.0,
        activation_fee_usd=149.0,
        reset_fee_usd=49.0,
        max_minis=5,
        max_micros=50,
        scaling_plan_summary=(
            "XFA starts 2 minis (20 micros) -> 3 minis at +$1,500 -> 5 minis at +$2,000 (next session)."
        ),
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=5,
        payout_win_day_threshold_usd=200.0,
        payout_min_buffer_usd=2_000.0,
        payout_max_withdraw_share=0.50,
        payout_cap_per_request_usd=5_000.0,
        payout_cadence_days=5,
        first_100pct_split_cap_usd=10_000.0,
        post_cap_split_frac=0.90,
        news_restricted_funded=False,
        vn_kyc_status=VNKycStatus.ALLOWED_XFA_ONLY.value,
        vn_kyc_eligible=True,
        vn_live_funded_eligible=False,
        vn_kyc_notes=(
            "Vietnam permitted for Trading Combine and Express Funded Account (XFA) payouts up to lifetime "
            "XFA payout cap (~200,000 USD); ineligible for Live Funded Account (LFA) graduation."
        ),
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://www.topstep.com/",
            "https://help.topstep.com/",
        ),
    ),
    "topstep_100k_combine": CMEFuturesPropTierSpec(
        tier_id="topstep_100k_combine",
        firm_id="topstep",
        firm_display_name="Topstep",
        program_name="100K Trading Combine -> XFA (Standard Path)",
        nominal_usd=100_000.0,
        is_straight_to_funded=False,
        profit_target_usd=6_000.0,
        max_dd_usd=3_000.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        lock_floor_above_initial_usd=0.0,
        daily_loss_limit_usd=2_000.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.50,
        funded_consistency_max_day_share=0.0,
        min_eval_trading_days=2,
        monthly_sub_usd=99.0,
        one_time_fee_usd=0.0,
        activation_fee_usd=149.0,
        reset_fee_usd=99.0,
        max_minis=10,
        max_micros=100,
        scaling_plan_summary="XFA starts 3 minis (30 micros) -> 5 minis at +$1,500 -> 10 minis at +$3,000.",
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=5,
        payout_win_day_threshold_usd=200.0,
        payout_min_buffer_usd=3_000.0,
        payout_max_withdraw_share=0.50,
        payout_cap_per_request_usd=5_000.0,
        payout_cadence_days=5,
        first_100pct_split_cap_usd=10_000.0,
        post_cap_split_frac=0.90,
        news_restricted_funded=False,
        vn_kyc_status=VNKycStatus.ALLOWED_XFA_ONLY.value,
        vn_kyc_eligible=True,
        vn_live_funded_eligible=False,
        vn_kyc_notes="Vietnam permitted for Combine + XFA payouts only (not eligible for Live Funded Account).",
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://www.topstep.com/",
            "https://help.topstep.com/",
        ),
    ),
    "topstep_150k_combine": CMEFuturesPropTierSpec(
        tier_id="topstep_150k_combine",
        firm_id="topstep",
        firm_display_name="Topstep",
        program_name="150K Trading Combine -> XFA (Standard Path)",
        nominal_usd=150_000.0,
        is_straight_to_funded=False,
        profit_target_usd=9_000.0,
        max_dd_usd=4_500.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        lock_floor_above_initial_usd=0.0,
        daily_loss_limit_usd=3_000.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.50,
        funded_consistency_max_day_share=0.0,
        min_eval_trading_days=2,
        monthly_sub_usd=199.0,
        one_time_fee_usd=0.0,
        activation_fee_usd=149.0,
        reset_fee_usd=149.0,
        max_minis=15,
        max_micros=150,
        scaling_plan_summary="XFA starts 3 minis (30 micros) -> 5 minis at +$1,500 -> 10 at +$3,000 -> 15 at +$4,500.",
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=5,
        payout_win_day_threshold_usd=200.0,
        payout_min_buffer_usd=4_500.0,
        payout_max_withdraw_share=0.50,
        payout_cap_per_request_usd=5_000.0,
        payout_cadence_days=5,
        first_100pct_split_cap_usd=10_000.0,
        post_cap_split_frac=0.90,
        news_restricted_funded=False,
        vn_kyc_status=VNKycStatus.ALLOWED_XFA_ONLY.value,
        vn_kyc_eligible=True,
        vn_live_funded_eligible=False,
        vn_kyc_notes="Vietnam permitted for Combine + XFA payouts only (not eligible for Live Funded Account).",
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://www.topstep.com/",
            "https://help.topstep.com/",
        ),
    ),
    # --- 2. MFFU (MyFundedFutures Starter / Expert EOD) ---
    "mffu_starter_50k": CMEFuturesPropTierSpec(
        tier_id="mffu_starter_50k",
        firm_id="mffu",
        firm_display_name="MyFundedFutures (MFFU)",
        program_name="50K Starter / Core-EOD Equivalent (No Activation)",
        nominal_usd=50_000.0,
        is_straight_to_funded=False,
        profit_target_usd=3_000.0,
        max_dd_usd=2_000.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        lock_floor_above_initial_usd=100.0,
        daily_loss_limit_usd=1_200.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.50,
        funded_consistency_max_day_share=0.40,
        min_eval_trading_days=2,
        monthly_sub_usd=97.0,
        one_time_fee_usd=0.0,
        activation_fee_usd=0.0,
        reset_fee_usd=97.0,
        max_minis=5,
        max_micros=50,
        scaling_plan_summary=(
            "Legacy Starter transitioned to Core/Rapid/Pro; EOD trailing locks at +$100 above initial balance."
        ),
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=5,
        payout_win_day_threshold_usd=100.0,
        payout_min_buffer_usd=2_100.0,
        payout_max_withdraw_share=0.60,
        payout_cap_per_request_usd=1_200.0,
        payout_cadence_days=5,
        first_100pct_split_cap_usd=10_000.0,
        post_cap_split_frac=0.90,
        news_restricted_funded=True,
        vn_kyc_status=VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
        vn_kyc_eligible=False,
        vn_live_funded_eligible=False,
        vn_kyc_notes="Vietnam is officially listed on MFFU Restricted Countries list (KYC & payouts blocked).",
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://myfundedfutures.com/",
            "https://help.myfundedfutures.com/",
        ),
    ),
    "mffu_expert_50k": CMEFuturesPropTierSpec(
        tier_id="mffu_expert_50k",
        firm_id="mffu",
        firm_display_name="MyFundedFutures (MFFU)",
        program_name="50K Expert / Pro-EOD Equivalent (No Activation)",
        nominal_usd=50_000.0,
        is_straight_to_funded=False,
        profit_target_usd=3_000.0,
        max_dd_usd=2_000.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        lock_floor_above_initial_usd=100.0,
        daily_loss_limit_usd=1_200.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.50,
        funded_consistency_max_day_share=0.0,
        min_eval_trading_days=2,
        monthly_sub_usd=157.0,
        one_time_fee_usd=0.0,
        activation_fee_usd=0.0,
        reset_fee_usd=157.0,
        max_minis=5,
        max_micros=50,
        scaling_plan_summary="Legacy Expert -> Pro-EOD lineup; no funded consistency rule, biweekly payouts.",
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=1,
        payout_win_day_threshold_usd=100.0,
        payout_min_buffer_usd=2_100.0,
        payout_max_withdraw_share=0.80,
        payout_cap_per_request_usd=5_000.0,
        payout_cadence_days=10,  # ~14 calendar days = 10 trading days
        first_100pct_split_cap_usd=10_000.0,
        post_cap_split_frac=0.90,
        news_restricted_funded=False,
        vn_kyc_status=VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
        vn_kyc_eligible=False,
        vn_live_funded_eligible=False,
        vn_kyc_notes="Vietnam is officially listed on MFFU Restricted Countries list (KYC & payouts blocked).",
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://myfundedfutures.com/",
            "https://help.myfundedfutures.com/",
        ),
    ),
    # --- 3. TAKEPROFITTRADER (Eval EOD Trailing -> PRO Intraday Unrealized Trailing!) ---
    "tpt_50k_pro": CMEFuturesPropTierSpec(
        tier_id="tpt_50k_pro",
        firm_id="takeprofittrader",
        firm_display_name="TakeProfitTrader",
        program_name="50K Test (EOD DD) -> PRO (Intraday Trailing DD, Daily Payout)",
        nominal_usd=50_000.0,
        is_straight_to_funded=False,
        profit_target_usd=3_000.0,
        max_dd_usd=2_000.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.INTRADAY_UNREALIZED_TRAILING.value,
        lock_floor_above_initial_usd=0.0,
        daily_loss_limit_usd=1_000.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.50,
        funded_consistency_max_day_share=0.0,
        min_eval_trading_days=5,
        monthly_sub_usd=170.0,  # Full un-discounted list price (promo NOFEE40 is MODEL_ASSUMPTION, not default)
        one_time_fee_usd=0.0,
        activation_fee_usd=130.0,
        reset_fee_usd=100.0,
        max_minis=6,
        max_micros=60,
        scaling_plan_summary=(
            "Eval uses EOD trailing DD; PRO switches to REAL-TIME Intraday Unrealized Trailing DD until locked at $0 "
            "after $2,000 buffer. Daily payouts above $2,000 buffer at 80% split (90% PRO+)."
        ),
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=1,
        payout_win_day_threshold_usd=0.0,
        payout_min_buffer_usd=2_000.0,
        payout_max_withdraw_share=1.0,  # Any profit above buffer withdrawable daily
        payout_cap_per_request_usd=10_000.0,
        payout_cadence_days=1,  # Daily payout eligibility from Day 1 above buffer
        first_100pct_split_cap_usd=0.0,
        post_cap_split_frac=0.80,
        news_restricted_funded=True,
        vn_kyc_status=VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
        vn_kyc_eligible=False,
        vn_live_funded_eligible=False,
        vn_kyc_notes=(
            "Vietnam is explicitly listed on TakeProfitTrader Restricted Countries list; platform access, "
            "market data, and VPN/travel usage from Vietnam are strictly prohibited."
        ),
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://takeprofittrader.com/",
            "https://takeprofittraderhelp.zendesk.com/",
        ),
    ),
    # --- 4. TRADEIFY (Growth & Straight-to-SimFunded / Lightning) ---
    "tradeify_50k_growth": CMEFuturesPropTierSpec(
        tier_id="tradeify_50k_growth",
        firm_id="tradeify",
        firm_display_name="Tradeify",
        program_name="50K Growth Eval -> SimFunded (EOD Trailing, No Activation)",
        nominal_usd=50_000.0,
        is_straight_to_funded=False,
        profit_target_usd=3_000.0,
        max_dd_usd=2_000.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        lock_floor_above_initial_usd=100.0,
        daily_loss_limit_usd=1_250.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.0,  # Latest Growth eval has 0% eval consistency, 35% funded consistency
        funded_consistency_max_day_share=0.35,
        min_eval_trading_days=1,
        monthly_sub_usd=0.0,
        one_time_fee_usd=145.0,
        activation_fee_usd=0.0,
        reset_fee_usd=95.0,
        max_minis=4,
        max_micros=40,
        scaling_plan_summary="EOD trailing locks at +$100 above initial; 35% funded consistency; 5 win days >= $150.",
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=5,
        payout_win_day_threshold_usd=150.0,
        payout_min_buffer_usd=2_100.0,
        payout_max_withdraw_share=0.50,
        payout_cap_per_request_usd=5_000.0,
        payout_cadence_days=5,
        first_100pct_split_cap_usd=15_000.0,
        post_cap_split_frac=0.90,
        news_restricted_funded=False,
        vn_kyc_status=VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
        vn_kyc_eligible=False,
        vn_live_funded_eligible=False,
        vn_kyc_notes="Vietnam is explicitly listed on Tradeify Restricted Countries list (KYC & payouts prohibited).",
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://tradeify.co/",
            "https://help.tradeify.co/",
        ),
    ),
    "tradeify_50k_straight_to_sim": CMEFuturesPropTierSpec(
        tier_id="tradeify_50k_straight_to_sim",
        firm_id="tradeify",
        firm_display_name="Tradeify",
        program_name="50K Straight-to-SimFunded / Lightning (Instant SimFunded, EOD DD)",
        nominal_usd=50_000.0,
        is_straight_to_funded=True,
        profit_target_usd=0.0,
        max_dd_usd=2_000.0,
        eval_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        funded_dd_mode=TrailingDDMode.EOD_TRAILING.value,
        lock_floor_above_initial_usd=100.0,
        daily_loss_limit_usd=1_250.0,
        daily_loss_is_hard_breach=False,
        eval_consistency_max_day_share=0.0,
        funded_consistency_max_day_share=0.20,  # Progressive 20% -> 25% -> 30% (conservative 20% baseline)
        min_eval_trading_days=0,
        monthly_sub_usd=0.0,
        one_time_fee_usd=492.0,
        activation_fee_usd=0.0,
        reset_fee_usd=492.0,  # No reset; repurchase required on breach
        max_minis=4,
        max_micros=40,
        scaling_plan_summary="Skips eval directly into SimFunded; EOD trailing locks +$100; 20%/25%/30% consistency.",
        mandatory_flat_ct="15:10 America/Chicago",
        payout_min_win_days=5,
        payout_win_day_threshold_usd=150.0,
        payout_min_buffer_usd=2_100.0,
        payout_max_withdraw_share=0.50,
        payout_cap_per_request_usd=3_000.0,
        payout_cadence_days=10,
        first_100pct_split_cap_usd=15_000.0,
        post_cap_split_frac=0.90,
        news_restricted_funded=False,
        vn_kyc_status=VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
        vn_kyc_eligible=False,
        vn_live_funded_eligible=False,
        vn_kyc_notes="Vietnam is explicitly listed on Tradeify Restricted Countries list (KYC & payouts prohibited).",
        execution_status=CME_EXECUTION_STATUS,
        verified_utc=RULES_VERIFIED_UTC,
        source_urls=(
            "https://tradeify.co/",
            "https://help.tradeify.co/",
        ),
    ),
}

PRIMARY_4FIRM_BENCHMARK_TIERS: tuple[str, ...] = (
    "topstep_50k_combine",
    "topstep_100k_combine",
    "topstep_150k_combine",
    "mffu_starter_50k",
    "mffu_expert_50k",
    "tpt_50k_pro",
    "tradeify_50k_growth",
    "tradeify_50k_straight_to_sim",
)


def load_ssot_fx_usd_vnd(fx_path: Path = DEFAULT_FX_RATES_PATH) -> tuple[float, dict[str, Any]]:
    """Load SSOT `usd_vnd` FX rate fail-closed from `configs/ssot/fx_rates.json`."""
    if not fx_path.is_file():
        raise FileNotFoundError(f"SSOT fx_rates.json missing: {fx_path}")
    data = json.loads(fx_path.read_text(encoding="utf-8"))
    rate = _require_finite_float(data.get("usd_vnd"), "usd_vnd", min_value=1_000.0, max_value=1_000_000.0)
    return rate, data


def load_ftmo_incumbent_specs(
    catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH,
) -> dict[str, dict[str, Any]]:
    """Load verified incumbent `FTMO 10K` and `FTMO 100K` Standard contracts from SSOT catalog."""
    if not catalog_path.is_file():
        raise FileNotFoundError(f"SSOT firms_catalog.json missing: {catalog_path}")
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    contracts = raw.get("contracts", {})
    out: dict[str, dict[str, Any]] = {}
    for cid in ("ftmo_standard_10k", "ftmo_standard_100k"):
        if cid not in contracts:
            raise KeyError(f"Required incumbent contract {cid!r} missing from {catalog_path}")
        c = contracts[cid]
        out[cid] = {
            "contract_id": cid,
            "display_name": str(c["display_name"]),
            "capital_usd": _require_finite_float(c["capital_usd"], f"{cid}.capital_usd", min_value=1_000.0),
            "fee_orig_usd": _require_finite_float(c["fee_orig_usd"], f"{cid}.fee_orig_usd", min_value=1.0),
            "fee_promo_usd": _require_finite_float(c["fee_promo_usd"], f"{cid}.fee_promo_usd", min_value=1.0),
            "p1_target_frac": _require_finite_float(
                c["p1_target_frac"], f"{cid}.p1_target_frac", min_value=0.01, max_value=0.5
            ),
            "p2_target_frac": _require_finite_float(
                c["p2_target_frac"], f"{cid}.p2_target_frac", min_value=0.01, max_value=0.5
            ),
            "daily_loss_limit_frac": _require_finite_float(
                c["daily_loss_limit_frac"], f"{cid}.daily_loss_limit_frac", min_value=0.01, max_value=0.25
            ),
            "static_loss_limit_frac": _require_finite_float(
                c["static_loss_limit_frac"], f"{cid}.static_loss_limit_frac", min_value=0.02, max_value=0.5
            ),
            "min_trading_days": _require_int(c["min_trading_days"], f"{cid}.min_trading_days", min_value=1),
            "payout_split_frac": _require_finite_float(
                c["payout_split_frac"], f"{cid}.payout_split_frac", min_value=0.5, max_value=1.0
            ),
            "payout_cycle_trading_days": 10,  # 14 calendar days ~ 10 trading days
            "card_fx_fee_frac": _require_finite_float(
                c["card_fx_fee_frac"], f"{cid}.card_fx_fee_frac", min_value=0.0, max_value=0.10
            ),
            "withdrawal_fee_frac": _require_finite_float(
                c["withdrawal_fee_frac"], f"{cid}.withdrawal_fee_frac", min_value=0.0, max_value=0.10
            ),
            "fee_refund_external_cash_frac": _require_finite_float(
                c["fee_refund_external_cash_frac"], f"{cid}.fee_refund_external_cash_frac", min_value=0.0, max_value=1.0
            ),
            "execution_status": str(c.get("execution_status", FTMO_EXECUTION_STATUS)),
            "verified_utc": str(c.get("verified_utc", RULES_VERIFIED_UTC)),
        }
    return out


def build_vn_kyc_feasibility_matrix() -> list[dict[str, Any]]:
    """Return structured Vietnam KYC, broker-bridge, and payout feasibility matrix (G12-compliant)."""
    return [
        {
            "firm_id": "topstep",
            "firm_name": "Topstep",
            "asset_class": "CME_FUTURES_INTRADAY",
            "vn_kyc_status": VNKycStatus.ALLOWED_XFA_ONLY.value,
            "vn_kyc_eligible": True,
            "vn_live_funded_eligible": False,
            "xfa_lifetime_payout_cap_usd": 200_000.0,
            "execution_platform": "TopstepX / ProjectX / Tradovate / Rithmic (NO native MT5)",
            "payout_rails_vn": ["Wise", "International Wire / ACH via Plane"],
            "mandatory_flat_rule": "15:10 America/Chicago (21:10 UTC CST / 20:10 UTC CDT)",
            "dd_type_eval_vs_funded": "EOD Trailing -> EOD Trailing (locks at $0)",
            "execution_status": CME_EXECUTION_STATUS,
            "verified_utc": RULES_VERIFIED_UTC,
            "blocker_summary": (
                "Only VN-eligible firm among the 4 CME futures prop firms, but capped at XFA-only (no Live Funded "
                "Account graduation) and requires building a non-MT5 execution adapter plus 5-7 CME-native engines."
            ),
        },
        {
            "firm_id": "mffu",
            "firm_name": "MyFundedFutures (MFFU)",
            "asset_class": "CME_FUTURES_INTRADAY",
            "vn_kyc_status": VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
            "vn_kyc_eligible": False,
            "vn_live_funded_eligible": False,
            "xfa_lifetime_payout_cap_usd": 0.0,
            "execution_platform": "Tradovate / NinjaTrader / Quantower / TradingView",
            "payout_rails_vn": [],
            "mandatory_flat_rule": "15:10 America/Chicago",
            "dd_type_eval_vs_funded": "EOD Trailing -> EOD Trailing (locks at +$100)",
            "execution_status": CME_EXECUTION_STATUS,
            "verified_utc": RULES_VERIFIED_UTC,
            "blocker_summary": "HARD COMPLIANCE BLOCKER: Vietnam is on MFFU Restricted Countries list.",
        },
        {
            "firm_id": "takeprofittrader",
            "firm_name": "TakeProfitTrader",
            "asset_class": "CME_FUTURES_INTRADAY",
            "vn_kyc_status": VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
            "vn_kyc_eligible": False,
            "vn_live_funded_eligible": False,
            "xfa_lifetime_payout_cap_usd": 0.0,
            "execution_platform": "Tradovate / Rithmic / NinjaTrader / CQG",
            "payout_rails_vn": [],
            "mandatory_flat_rule": "15:10 America/Chicago + strict PRO red-news ban",
            "dd_type_eval_vs_funded": "EOD Trailing (Eval) -> INTRADAY UNREALIZED Trailing (PRO)",
            "execution_status": CME_EXECUTION_STATUS,
            "verified_utc": RULES_VERIFIED_UTC,
            "blocker_summary": (
                "HARD COMPLIANCE BLOCKER: Vietnam is on TakeProfitTrader Restricted Countries list "
                "(plus PRO Intraday Unrealized Trailing DD heavily penalizes trend/breakout strategies)."
            ),
        },
        {
            "firm_id": "tradeify",
            "firm_name": "Tradeify",
            "asset_class": "CME_FUTURES_INTRADAY",
            "vn_kyc_status": VNKycStatus.RESTRICTED_VN_PROHIBITED.value,
            "vn_kyc_eligible": False,
            "vn_live_funded_eligible": False,
            "xfa_lifetime_payout_cap_usd": 0.0,
            "execution_platform": "Tradovate / ProjectX / NinjaTrader",
            "payout_rails_vn": [],
            "mandatory_flat_rule": "15:10 America/Chicago",
            "dd_type_eval_vs_funded": "EOD Trailing -> EOD Trailing (locks at +$100)",
            "execution_status": CME_EXECUTION_STATUS,
            "verified_utc": RULES_VERIFIED_UTC,
            "blocker_summary": "HARD COMPLIANCE BLOCKER: Vietnam is on Tradeify Restricted Countries list.",
        },
        {
            "firm_id": "ftmo_incumbent",
            "firm_name": "FTMO (Incumbent CFD Benchmark)",
            "asset_class": "CFD_PROP_MT5",
            "vn_kyc_status": VNKycStatus.ALLOWED_FULL_VN.value,
            "vn_kyc_eligible": True,
            "vn_live_funded_eligible": True,
            "xfa_lifetime_payout_cap_usd": None,
            "execution_platform": "Native MetaTrader 5 (existing verified Naqex EA + PropGuard)",
            "payout_rails_vn": ["Bank Wire / Skrill / Crypto / Wise (verified VN rails)"],
            "mandatory_flat_rule": "Standard flat overnight/weekend; Swing allows overnight/weekend",
            "dd_type_eval_vs_funded": "Static 10% Max DD + 5% Daily DD (Prague midnight reset)",
            "execution_status": FTMO_EXECUTION_STATUS,
            "verified_utc": "2026-11-26T11:25:00Z",
            "blocker_summary": "NONE — Verified VN checkout, measured MT5 demo execution, static 10% DD, one-time fee.",
        },
    ]


# ---------------------------------------------------------------------------
# Numba-Accelerated Shared-Path Monte Carlo Kernels (10,000 Paths)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _simulate_cme_tier_numba(
    sim_ret: np.ndarray,
    nominal_usd: float,
    is_straight_to_funded: int,
    profit_target_usd: float,
    max_dd_usd: float,
    eval_is_intraday_dd: int,
    funded_is_intraday_dd: int,
    lock_floor_above_initial: float,
    daily_loss_limit_usd: float,
    daily_loss_is_hard: int,
    eval_consistency_share: float,
    funded_consistency_share: float,
    min_eval_days: int,
    monthly_sub_usd: float,
    one_time_fee_usd: float,
    activation_fee_usd: float,
    reset_fee_usd: float,
    payout_min_win_days: int,
    payout_win_day_thresh: float,
    payout_min_buffer: float,
    payout_max_share: float,
    payout_cap_usd: float,
    payout_cadence_days: int,
    first_100_cap: float,
    post_cap_split: float,
    max_attempts: int,
    eval_scale: float,
    funded_scale: float,
    card_fx_fee_frac: float,
    withdrawal_fee_frac: float,
    mfe_giveback_mult: float,
    mae_intrabar_mult: float,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Run exact shared-path CME Futures Prop lifecycle simulation across `n_paths` x `horizon_days`.

    Tracks BOTH:
      1. First-ticket zero-retry single-ticket lifecycle outcomes (`first_pass_day`, `first_fail_day`)
         for exact Law 13 `Pass + Fail + Pending == 100.0%` at 3m/6m/12m/24m!
      2. Full 24m campaign cashflow, fees (including VN card FX & withdrawal friction), OOP95,
         12m (252 trading day) fixed-window Funded blowup counts (uncensored vs censored),
         Payout #1 day, `BOT_AUTO_KILL` vs `FIRM_HARD_BREACH` counts!
    """
    n_paths = sim_ret.shape[0]
    horizon_days = sim_ret.shape[1]

    total_fees_arr = np.zeros(n_paths, dtype=np.float64)
    net_cf_arr = np.zeros(n_paths, dtype=np.float64)
    max_oop_arr = np.zeros(n_paths, dtype=np.float64)
    first_pass_day = np.full(n_paths, -1, dtype=np.int64)
    first_fail_day = np.full(n_paths, -1, dtype=np.int64)
    first_payout_day = np.full(n_paths, -1, dtype=np.int64)
    # 0=never funded, 1=survived full 252d, 2=blew up <=252d, 3=censored (<252d remaining)
    funded_12m_status = np.zeros(n_paths, dtype=np.int64)
    payout_count_arr = np.zeros(n_paths, dtype=np.int64)
    hard_breaches_arr = np.zeros(n_paths, dtype=np.int64)
    soft_dll_arr = np.zeros(n_paths, dtype=np.int64)

    fee_buy_mult = 1.0 + card_fx_fee_frac
    payout_net_mult = 1.0 - withdrawal_fee_frac

    for p in range(n_paths):
        attempts = 1
        if is_straight_to_funded == 1:
            state = 1  # Directly in SimFunded; Ticket #1 PASS = Payout #1 cleared, FAIL = breach before Payout #1
            fees_paid = one_time_fee_usd * fee_buy_mult
        else:
            state = 0  # In Eval
            initial_fee = monthly_sub_usd if monthly_sub_usd > 0.0 else one_time_fee_usd
            fees_paid = initial_fee * fee_buy_mult

        cash_in = 0.0
        max_oop = fees_paid

        # Eval state
        eval_days = 0
        eval_active_days = 0
        eq = 0.0
        hwm = 0.0
        floor = -max_dd_usd
        best_eval_day = 0.0

        # Funded state
        funded_eq = 0.0
        funded_hwm = 0.0
        funded_floor = -max_dd_usd
        funded_entry_day = 0 if is_straight_to_funded == 1 else -1
        funded_first_window_done = 0
        days_since_payout = 0
        win_days_cycle = 0
        cycle_profit = 0.0
        best_cycle_day = 0.0
        cum_withdrawn = 0.0
        payout_count = 0

        hard_breaches = 0
        soft_dlls = 0

        for t in range(horizon_days):
            if state == 2:
                break

            raw_ret = sim_ret[p, t]
            if state == 0:
                # Monthly subscription renewal every 21 trading days during eval
                if monthly_sub_usd > 0.0 and eval_days > 0 and (eval_days % 21 == 0):
                    fees_paid += monthly_sub_usd * fee_buy_mult
                    oop_now = fees_paid - cash_in
                    if oop_now > max_oop:
                        max_oop = oop_now

                day_pnl_raw = raw_ret * nominal_usd * eval_scale
                if abs(day_pnl_raw) > 1e-9:
                    eval_active_days += 1
                eval_days += 1

                # Soft DLL protection clips daily close loss if soft DLL enabled
                day_pnl = day_pnl_raw
                if daily_loss_limit_usd > 0.0 and day_pnl < -daily_loss_limit_usd:
                    if daily_loss_is_hard == 1:
                        hard_breaches += 1
                        if attempts == 1 and first_pass_day[p] < 0 and first_fail_day[p] < 0:
                            first_fail_day[p] = t + 1
                        if attempts >= max_attempts:
                            state = 2
                        else:
                            attempts += 1
                            eval_days = 0
                            eval_active_days = 0
                            eq = 0.0
                            hwm = 0.0
                            floor = -max_dd_usd
                            best_eval_day = 0.0
                            fees_paid += reset_fee_usd * fee_buy_mult
                            if fees_paid - cash_in > max_oop:
                                max_oop = fees_paid - cash_in
                        continue
                    else:
                        day_pnl = -daily_loss_limit_usd
                        soft_dlls += 1

                # Conservative intrabar excursion around daily closed PnL
                abs_move = abs(day_pnl)
                if day_pnl >= 0.0:
                    intra_hi = eq + day_pnl * (1.0 + mfe_giveback_mult)
                    intra_lo = eq - abs_move * mae_intrabar_mult
                else:
                    intra_hi = eq + abs_move * mfe_giveback_mult
                    intra_lo = eq + day_pnl * (1.0 + mae_intrabar_mult)

                if eval_is_intraday_dd == 1 and intra_hi > hwm:
                    hwm = intra_hi
                    prop_fl = hwm - max_dd_usd
                    if prop_fl > lock_floor_above_initial:
                        prop_fl = lock_floor_above_initial
                    if prop_fl > floor:
                        floor = prop_fl

                eq_end = eq + day_pnl

                # Real-time intraday trough & close breach check
                if intra_lo <= floor or eq_end <= floor:
                    hard_breaches += 1
                    if attempts == 1 and first_pass_day[p] < 0 and first_fail_day[p] < 0:
                        first_fail_day[p] = t + 1
                    if attempts >= max_attempts:
                        state = 2
                    else:
                        attempts += 1
                        eval_days = 0
                        eval_active_days = 0
                        eq = 0.0
                        hwm = 0.0
                        floor = -max_dd_usd
                        best_eval_day = 0.0
                        fees_paid += reset_fee_usd * fee_buy_mult
                        if fees_paid - cash_in > max_oop:
                            max_oop = fees_paid - cash_in
                    continue

                eq = eq_end
                if day_pnl > best_eval_day:
                    best_eval_day = day_pnl

                # EOD trailing update at 15:10 CT close
                if eval_is_intraday_dd == 0 and eq > hwm:
                    hwm = eq
                    prop_fl = hwm - max_dd_usd
                    if prop_fl > lock_floor_above_initial:
                        prop_fl = lock_floor_above_initial
                    if prop_fl > floor:
                        floor = prop_fl

                # Profit target + Consistency Rule + Min Trading Days check
                req_target = profit_target_usd
                if best_eval_day > 0.0 and eval_consistency_share > 0.0:
                    cons_req = best_eval_day / eval_consistency_share
                    if cons_req > req_target:
                        req_target = cons_req

                if eq >= req_target and eval_active_days >= min_eval_days:
                    if attempts == 1 and first_pass_day[p] < 0 and first_fail_day[p] < 0:
                        first_pass_day[p] = t + 1
                    fees_paid += activation_fee_usd * fee_buy_mult
                    if fees_paid - cash_in > max_oop:
                        max_oop = fees_paid - cash_in
                    state = 1
                    funded_eq = 0.0
                    funded_hwm = 0.0
                    funded_floor = -max_dd_usd
                    if funded_entry_day < 0:
                        funded_entry_day = t + 1
                    days_since_payout = 0
                    win_days_cycle = 0
                    cycle_profit = 0.0
                    best_cycle_day = 0.0
            else:
                # FUNDED STATE (XFA / SimFunded / PRO)
                day_pnl_raw = raw_ret * nominal_usd * funded_scale
                day_pnl = day_pnl_raw
                if daily_loss_limit_usd > 0.0 and day_pnl < -daily_loss_limit_usd:
                    if daily_loss_is_hard == 1:
                        hard_breaches += 1
                        in_12m = funded_first_window_done == 0 and funded_entry_day >= 0
                        if in_12m and (t + 1 - funded_entry_day) <= 252:
                            funded_12m_status[p] = 2
                            funded_first_window_done = 1
                        if (
                            is_straight_to_funded == 1
                            and attempts == 1
                            and first_pass_day[p] < 0
                            and first_fail_day[p] < 0
                        ):
                            first_fail_day[p] = t + 1
                        if attempts >= max_attempts:
                            state = 2
                        else:
                            attempts += 1
                            if is_straight_to_funded == 1:
                                state = 1
                                funded_eq = 0.0
                                funded_hwm = 0.0
                                funded_floor = -max_dd_usd
                                days_since_payout = 0
                                win_days_cycle = 0
                                cycle_profit = 0.0
                                best_cycle_day = 0.0
                                fees_paid += one_time_fee_usd * fee_buy_mult
                            else:
                                state = 0
                                eval_days = 0
                                eval_active_days = 0
                                eq = 0.0
                                hwm = 0.0
                                floor = -max_dd_usd
                                best_eval_day = 0.0
                                restart_fee = monthly_sub_usd if monthly_sub_usd > 0.0 else one_time_fee_usd
                                fees_paid += restart_fee * fee_buy_mult
                            if fees_paid - cash_in > max_oop:
                                max_oop = fees_paid - cash_in
                        continue
                    else:
                        day_pnl = -daily_loss_limit_usd
                        soft_dlls += 1

                # Conservative intrabar excursion around daily closed PnL
                abs_move = abs(day_pnl)
                if day_pnl >= 0.0:
                    intra_hi = funded_eq + day_pnl * (1.0 + mfe_giveback_mult)
                    intra_lo = funded_eq - abs_move * mae_intrabar_mult
                else:
                    intra_hi = funded_eq + abs_move * mfe_giveback_mult
                    intra_lo = funded_eq + day_pnl * (1.0 + mae_intrabar_mult)

                # INTRADAY UNREALIZED TRAILING (TakeProfitTrader PRO!) ratchets HWM & floor live BEFORE trough check!
                if funded_is_intraday_dd == 1 and intra_hi > funded_hwm:
                    funded_hwm = intra_hi
                    prop_fl = funded_hwm - max_dd_usd
                    if prop_fl > lock_floor_above_initial:
                        prop_fl = lock_floor_above_initial
                    if prop_fl > funded_floor:
                        funded_floor = prop_fl

                funded_end = funded_eq + day_pnl

                if intra_lo <= funded_floor or funded_end <= funded_floor:
                    hard_breaches += 1
                    in_12m_b = funded_first_window_done == 0 and funded_entry_day >= 0
                    if in_12m_b and (t + 1 - funded_entry_day) <= 252:
                        funded_12m_status[p] = 2
                        funded_first_window_done = 1
                    if (
                        is_straight_to_funded == 1
                        and attempts == 1
                        and first_pass_day[p] < 0
                        and first_fail_day[p] < 0
                    ):
                        first_fail_day[p] = t + 1
                    if attempts >= max_attempts:
                        state = 2
                    else:
                        attempts += 1
                        if is_straight_to_funded == 1:
                            state = 1
                            funded_eq = 0.0
                            funded_hwm = 0.0
                            funded_floor = -max_dd_usd
                            days_since_payout = 0
                            win_days_cycle = 0
                            cycle_profit = 0.0
                            best_cycle_day = 0.0
                            fees_paid += one_time_fee_usd * fee_buy_mult
                        else:
                            state = 0
                            eval_days = 0
                            eval_active_days = 0
                            eq = 0.0
                            hwm = 0.0
                            floor = -max_dd_usd
                            best_eval_day = 0.0
                            restart_fee = monthly_sub_usd if monthly_sub_usd > 0.0 else one_time_fee_usd
                            fees_paid += restart_fee * fee_buy_mult
                        if fees_paid - cash_in > max_oop:
                            max_oop = fees_paid - cash_in
                    continue

                funded_eq = funded_end
                days_since_payout += 1
                cycle_profit += day_pnl
                if day_pnl > best_cycle_day:
                    best_cycle_day = day_pnl

                # EOD trailing update at 15:10 CT close
                if funded_is_intraday_dd == 0 and funded_eq > funded_hwm:
                    funded_hwm = funded_eq
                    prop_fl = funded_hwm - max_dd_usd
                    if prop_fl > lock_floor_above_initial:
                        prop_fl = lock_floor_above_initial
                    if prop_fl > funded_floor:
                        funded_floor = prop_fl

                # Check if 12m (252 trading day) fixed funded survival window completed cleanly
                if funded_first_window_done == 0 and funded_entry_day >= 0 and (t + 1 - funded_entry_day) >= 252:
                    funded_12m_status[p] = 1
                    funded_first_window_done = 1

                if day_pnl >= payout_win_day_thresh and day_pnl > 0.0:
                    win_days_cycle += 1

                # Payout eligibility check: win days + cadence + buffer + funded consistency
                cons_ok = True
                if funded_consistency_share > 0.0 and best_cycle_day > 0.0:
                    if cycle_profit <= 0.0 or (best_cycle_day / cycle_profit) > funded_consistency_share + 1e-9:
                        cons_ok = False

                withdrawable_above_buf = funded_eq - payout_min_buffer
                if withdrawable_above_buf < 0.0:
                    withdrawable_above_buf = 0.0
                max_by_share = funded_eq * payout_max_share
                if max_by_share > payout_cap_usd:
                    max_by_share = payout_cap_usd
                gross_req = withdrawable_above_buf if withdrawable_above_buf < max_by_share else max_by_share

                if (
                    cons_ok
                    and win_days_cycle >= payout_min_win_days
                    and days_since_payout >= payout_cadence_days
                    and gross_req >= 250.0
                ):
                    rem_100 = first_100_cap - cum_withdrawn
                    if rem_100 < 0.0:
                        rem_100 = 0.0
                    part_100 = gross_req if gross_req < rem_100 else rem_100
                    part_post = gross_req - part_100
                    if part_post < 0.0:
                        part_post = 0.0
                    net_payout = (part_100 + part_post * post_cap_split) * payout_net_mult
                    funded_eq -= gross_req
                    if funded_floor < lock_floor_above_initial:
                        funded_floor = lock_floor_above_initial
                    cum_withdrawn += gross_req
                    cash_in += net_payout
                    payout_count += 1
                    if first_payout_day[p] < 0:
                        first_payout_day[p] = t + 1
                    if (
                        is_straight_to_funded == 1
                        and attempts == 1
                        and first_pass_day[p] < 0
                        and first_fail_day[p] < 0
                    ):
                        first_pass_day[p] = t + 1
                    win_days_cycle = 0
                    days_since_payout = 0
                    cycle_profit = 0.0
                    best_cycle_day = 0.0

        # Mark censored if funded entered with < 252 trading days remaining and never blew up
        if funded_entry_day >= 0 and funded_first_window_done == 0:
            funded_12m_status[p] = 3

        total_fees_arr[p] = fees_paid
        net_cf_arr[p] = cash_in - fees_paid
        max_oop_arr[p] = max_oop
        payout_count_arr[p] = payout_count
        hard_breaches_arr[p] = hard_breaches
        soft_dll_arr[p] = soft_dlls

    return (
        total_fees_arr,
        net_cf_arr,
        max_oop_arr,
        first_pass_day,
        first_fail_day,
        first_payout_day,
        funded_12m_status,
        payout_count_arr,
        hard_breaches_arr,
        soft_dll_arr,
    )


@njit(cache=True)
def _simulate_ftmo_incumbent_numba(
    sim_ret: np.ndarray,
    capital_usd: float,
    fee_usd: float,
    p1_target_frac: float,
    p2_target_frac: float,
    daily_dd_frac: float,
    static_dd_frac: float,
    min_trading_days: int,
    payout_split_frac: float,
    payout_cycle_days: int,
    fee_refund_frac: float,
    card_fx_fee_frac: float,
    withdrawal_fee_frac: float,
    eval_scale: float,
    funded_scale: float,
    lot_efficiency: float,
    max_attempts: int,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Simulate incumbent FTMO 2-Step Static DD (10K / 100K) on the exact same shared market paths."""
    n_paths = sim_ret.shape[0]
    horizon_days = sim_ret.shape[1]

    total_fees_arr = np.zeros(n_paths, dtype=np.float64)
    net_cf_arr = np.zeros(n_paths, dtype=np.float64)
    max_oop_arr = np.zeros(n_paths, dtype=np.float64)
    first_pass_day = np.full(n_paths, -1, dtype=np.int64)
    first_fail_day = np.full(n_paths, -1, dtype=np.int64)
    first_payout_day = np.full(n_paths, -1, dtype=np.int64)
    funded_12m_status = np.zeros(n_paths, dtype=np.int64)
    payout_count_arr = np.zeros(n_paths, dtype=np.int64)
    hard_breaches_arr = np.zeros(n_paths, dtype=np.int64)

    fee_buy_usd = fee_usd * (1.0 + card_fx_fee_frac)
    payout_net_mult = 1.0 - withdrawal_fee_frac
    p1_target_usd = capital_usd * p1_target_frac
    p2_target_usd = capital_usd * p2_target_frac
    daily_dd_usd = capital_usd * daily_dd_frac
    static_floor_usd = -capital_usd * static_dd_frac
    bot_kill_daily_usd = daily_dd_usd * 0.80  # Internal protective kill switch below 5% firm daily DD

    for p in range(n_paths):
        state = 0  # 0=P1, 1=P2, 2=FUNDED, 3=EXHAUSTED
        attempts = 1
        eq = 0.0
        phase_days = 0
        funded_entry_day = -1
        funded_first_window_done = 0
        days_since_payout = 0
        refund_claimed = 0

        fees_paid = fee_buy_usd
        cash_in = 0.0
        max_oop = fees_paid
        payout_count = 0
        hard_breaches = 0

        for t in range(horizon_days):
            if state == 3:
                break

            raw_ret = sim_ret[p, t] * lot_efficiency
            scale = eval_scale if state < 2 else funded_scale
            day_pnl = raw_ret * capital_usd * scale

            # Conservative internal daily protective stop (below firm 5% hard daily DD)
            if day_pnl < -daily_dd_usd:
                # Gap-through daily hard breach
                breach_now = True
            else:
                if day_pnl < -bot_kill_daily_usd:
                    day_pnl = -bot_kill_daily_usd
                eq += day_pnl
                breach_now = eq <= static_floor_usd

            if breach_now:
                hard_breaches += 1
                in_ftmo_12m = state == 2 and funded_first_window_done == 0 and funded_entry_day >= 0
                if in_ftmo_12m and (t + 1 - funded_entry_day) <= 252:
                    funded_12m_status[p] = 2
                    funded_first_window_done = 1
                if attempts == 1 and first_pass_day[p] < 0 and first_fail_day[p] < 0:
                    first_fail_day[p] = t + 1
                if attempts >= max_attempts:
                    state = 3
                else:
                    attempts += 1
                    state = 0
                    eq = 0.0
                    phase_days = 0
                    refund_claimed = 0
                    fees_paid += fee_buy_usd
                    if fees_paid - cash_in > max_oop:
                        max_oop = fees_paid - cash_in
                continue

            if abs(day_pnl) > 1e-9:
                phase_days += 1

            if state == 0:
                if eq >= p1_target_usd and phase_days >= min_trading_days:
                    state = 1
                    eq = 0.0
                    phase_days = 0
            elif state == 1:
                if eq >= p2_target_usd and phase_days >= min_trading_days:
                    if attempts == 1 and first_pass_day[p] < 0 and first_fail_day[p] < 0:
                        first_pass_day[p] = t + 1
                    state = 2
                    eq = 0.0
                    days_since_payout = 0
                    if funded_entry_day < 0:
                        funded_entry_day = t + 1
            else:
                days_since_payout += 1
                if funded_first_window_done == 0 and funded_entry_day >= 0 and (t + 1 - funded_entry_day) >= 252:
                    funded_12m_status[p] = 1
                    funded_first_window_done = 1

                if days_since_payout >= payout_cycle_days and eq >= 50.0:
                    gross_payout = eq
                    net_payout = gross_payout * payout_split_frac * payout_net_mult
                    if refund_claimed == 0:
                        net_payout += fee_usd * fee_refund_frac * payout_net_mult
                        refund_claimed = 1
                    eq = 0.0
                    cash_in += net_payout
                    payout_count += 1
                    if first_payout_day[p] < 0:
                        first_payout_day[p] = t + 1
                    days_since_payout = 0

        if funded_entry_day >= 0 and funded_first_window_done == 0:
            funded_12m_status[p] = 3

        total_fees_arr[p] = fees_paid
        net_cf_arr[p] = cash_in - fees_paid
        max_oop_arr[p] = max_oop
        payout_count_arr[p] = payout_count
        hard_breaches_arr[p] = hard_breaches

    return (
        total_fees_arr,
        net_cf_arr,
        max_oop_arr,
        first_pass_day,
        first_fail_day,
        first_payout_day,
        funded_12m_status,
        payout_count_arr,
        hard_breaches_arr,
    )


# ---------------------------------------------------------------------------
# Strategy Metrics, Law 13–15 Summarization, and 4-Firm MC Runner
# ---------------------------------------------------------------------------


def _extract_validated_dev_returns(
    dev_returns_le_2024: Mapping[str, Any] | np.ndarray | Sequence[float],
    *,
    dates: Sequence[str] | None = None,
) -> tuple[np.ndarray, list[str] | None, str | None, str | None]:
    """Extract and strictly validate Dev (`< 2025-01-01`) daily return array (100% `-O`-safe)."""
    extracted_dates: list[str] | None = None

    if isinstance(dev_returns_le_2024, Mapping):
        if "daily_returns" in dev_returns_le_2024 and isinstance(dev_returns_le_2024["daily_returns"], Mapping):
            rmap = dev_returns_le_2024["daily_returns"]
            extracted_dates = sorted(str(k) for k in rmap.keys())
            vals = [_require_finite_float(rmap[k], f"daily_returns[{k}]") for k in extracted_dates]
        elif "dates" in dev_returns_le_2024 and "returns" in dev_returns_le_2024:
            extracted_dates = [str(d) for d in dev_returns_le_2024["dates"]]
            raw_rets = dev_returns_le_2024["returns"]
            if len(extracted_dates) != len(raw_rets):
                raise ValueError(
                    f"Length mismatch: dates ({len(extracted_dates)}) != returns ({len(raw_rets)})"
                )
            vals = [_require_finite_float(v, f"returns[{i}]") for i, v in enumerate(raw_rets)]
        else:
            # Plain {iso_date: float} mapping
            extracted_dates = sorted(str(k) for k in dev_returns_le_2024.keys())
            vals = [_require_finite_float(dev_returns_le_2024[k], f"dev_returns[{k}]") for k in extracted_dates]
        arr = np.asarray(vals, dtype=np.float64)
    else:
        raw_seq = list(dev_returns_le_2024)
        vals = [_require_finite_float(v, f"dev_returns[{i}]") for i, v in enumerate(raw_seq)]
        arr = np.asarray(vals, dtype=np.float64)
        if dates is not None:
            extracted_dates = [str(d) for d in dates]
            if len(extracted_dates) != len(arr):
                raise ValueError(f"Length mismatch: dates ({len(extracted_dates)}) != returns ({len(arr)})")

    if arr.size < 20:
        raise ValueError(f"dev_returns_le_2024 requires >= 20 daily observations, got {arr.size}")

    if extracted_dates is not None:
        enforce_pre_holdout_dates(
            extracted_dates,
            context="wave4.cme_intraday_prop_feasibility.dev_returns_le_2024",
            cutoff_day=HOLDOUT_CUTOFF_DAY,
            allow_empty=False,
        )
        max_dt = max(extracted_dates)
        if max_dt > HOLDOUT_CUTOFF_DATE or max_dt >= HOLDOUT_CUTOFF_DAY:
            raise HoldoutLockError(
                f"HOLDOUT_CONTAMINATION [wave4.cme_intraday]: max_date={max_dt} exceeds {HOLDOUT_CUTOFF_DATE}"
            )
        return arr, extracted_dates, min(extracted_dates), max_dt

    return arr, None, None, None


def compute_strategy_balanced_metrics(daily_returns: np.ndarray) -> dict[str, Any]:
    """Compute balanced Law 15 strategy diagnostics (Winrate, RR, EV/day, PF, Max DD, Calmar, Sharpe)."""
    r = np.asarray(daily_returns, dtype=np.float64)
    active = r[np.abs(r) > 1e-12]
    wins = active[active > 0.0]
    losses = active[active < 0.0]

    n_days = int(r.size)
    n_active = int(active.size)
    winrate_pct = (100.0 * float(wins.size) / n_active) if n_active > 0 else 0.0
    avg_win = float(np.mean(wins)) if wins.size > 0 else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses.size > 0 else 0.0
    rr_ratio = (avg_win / avg_loss) if avg_loss > 1e-12 else (99.0 if avg_win > 0.0 else 0.0)
    gross_win = float(np.sum(wins)) if wins.size > 0 else 0.0
    gross_loss = abs(float(np.sum(losses))) if losses.size > 0 else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 1e-12 else (99.0 if gross_win > 0.0 else 0.0)

    mean_d = float(np.mean(r))
    std_d = float(np.std(r, ddof=1)) if n_days > 1 else 0.0
    sharpe = (mean_d / std_d) * math.sqrt(TRADING_DAYS_PER_YEAR) if std_d > 1e-12 else 0.0

    # Additive equity curve for prop drawdown consistency
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]
    dd = peak - eq
    max_dd_pct = float(np.max(dd) * 100.0) if dd.size > 0 else 0.0
    ann_ret_pct = mean_d * TRADING_DAYS_PER_YEAR * 100.0
    calmar = (ann_ret_pct / max_dd_pct) if max_dd_pct > 1e-9 else (99.0 if ann_ret_pct > 0.0 else 0.0)

    # Longest losing streak on active trading days
    max_loss_streak = 0
    cur_streak = 0
    for val in active:
        if val < 0.0:
            cur_streak += 1
            if cur_streak > max_loss_streak:
                max_loss_streak = cur_streak
        else:
            cur_streak = 0

    return {
        "n_days": n_days,
        "n_active_days": n_active,
        "winrate_pct": round(winrate_pct, 2),
        "rr_ratio": round(rr_ratio, 3),
        "ev_per_active_day_pct": round((float(np.mean(active)) * 100.0) if n_active > 0 else 0.0, 4),
        "profit_factor": round(pf, 3),
        "ann_return_pct": round(ann_ret_pct, 2),
        "max_dd_pct": round(max_dd_pct, 2),
        "max_loss_streak_days": max_loss_streak,
        "calmar": round(calmar, 3),
        "sharpe": round(sharpe, 3),
    }


def _summarize_pass_fail_pending(
    first_pass_day: np.ndarray,
    first_fail_day: np.ndarray,
    *,
    horizons_months: tuple[int, ...] = (3, 6, 12, 24),
) -> dict[str, dict[str, float]]:
    """Compute mutually exclusive `Pass + Fail + Pending == 100.0%` rates at each monthly horizon."""
    n = int(first_pass_day.size)
    out: dict[str, dict[str, float]] = {}
    for m in horizons_months:
        cutoff_d = m * TRADING_DAYS_PER_MONTH
        passed = int(np.sum((first_pass_day >= 0) & (first_pass_day <= cutoff_d)))
        failed = int(np.sum((first_fail_day >= 0) & (first_fail_day <= cutoff_d)))
        pending = n - passed - failed
        if pending < 0:
            raise RuntimeError(f"Accounting violation at {m}m: passed({passed}) + failed({failed}) > n({n})")
        p_pct = round(100.0 * passed / n, 4)
        f_pct = round(100.0 * failed / n, 4)
        # Preserve exact 100.0000 sum with zero floating-point drift
        pend_pct = round(100.0 - p_pct - f_pct, 4)
        out[f"{m}m"] = {
            "pass_pct": p_pct,
            "fail_pct": f_pct,
            "pending_pct": pend_pct,
            "sum_pct": round(p_pct + f_pct + pend_pct, 4),
        }
    return out


def _grade_prop_scorecard(
    *,
    asset_class: str,
    ev_per_fee: float,
    funded_blowup_12m_pct: float | None,
    vn_kyc_eligible: bool,
) -> dict[str, Any]:
    """Grade inside-out by Law 15 domain tier (Tier 1 CFD Prop vs Tier 2 CME Futures Intraday)."""
    blowup = 100.0 if funded_blowup_12m_pct is None else funded_blowup_12m_pct
    if asset_class == "CFD_PROP_MT5":
        if ev_per_fee <= 0.0 or blowup > 5.0:
            tier = "XAU"
            gap = "EV/Phí <= 0x hoặc cháy Funded 12 tháng > 5% trên chuỗi lợi suất hiện tại."
        elif ev_per_fee < 3.0 or blowup >= 1.0:
            tier = "DU_DUNG"
            gap = "Cần >= +3.0x EV/Phí và cháy Funded 12 tháng < 1% (ví dụ đủ bộ 7 động cơ PORT_7E)."
        elif ev_per_fee < 5.0:
            tier = "TOT"
            gap = "Đã đạt ngưỡng Tốt; chạm Top 1% khi >= +5.0x EV/Phí và xác minh thực tế trên tiền thật."
        else:
            tier = "TOP_1_PCT_CANDIDATE_BACKTEST"
            gap = "Mới ở mức backtest Dev; cần xác nhận trên Demo/Live tiền thật và rút payout."
        return {
            "domain_tier": "TIER_1_CFD_PROP_SINGLE_BOT",
            "grade": tier,
            "scale_definition": {
                "XAU": "EV/Fee <= 0x or Funded blowup 12m > 5%",
                "DU_DUNG": "EV/Fee +0.01x..+2.99x or blowup 1%..5%",
                "TOT": "EV/Fee +3.0x..+4.99x & blowup < 1%",
                "TOP_1_PCT": "EV/Fee >= +5.0x & blowup < 1% verified on live payouts",
            },
            "gap_to_top1_vi": gap,
        }

    if not vn_kyc_eligible:
        tier = "BLOCKED_VN_KYC"
        gap = "Hãng chặn KYC cư trú Việt Nam (không thể rút tiền hợp lệ từ VN)."
    elif ev_per_fee <= 0.0 or blowup > 35.0:
        tier = "XAU"
        gap = "EV/Phí âm hoặc cháy Funded 12 tháng > 35% do Trailing DD chặt và phí thuê bao."
    elif ev_per_fee < 3.0 or blowup > 15.0:
        tier = "DU_DUNG"
        gap = "Cần >= +3.0x EV/Phí và cháy Funded 12 tháng <= 15% (cần bộ 5-7 động cơ thuần MNQ/MES/MGC/MCL)."
    elif ev_per_fee < 5.0 or blowup > 5.0:
        tier = "TOT"
        gap = "Cần >= +5.0x EV/Phí, cháy Funded 12 tháng < 5%, và kiểm chứng lệnh demo/forward thực tế."
    else:
        tier = "TOP_1_PCT_CANDIDATE_BACKTEST"
        gap = "Mới ở mức backtest Dev; cần chứng minh khớp lệnh thật trên ProjectX/Tradovate & 12m forward."

    return {
        "domain_tier": "TIER_2_CME_FUTURES_INTRADAY",
        "grade": tier,
        "scale_definition": {
            "XAU": "EV/Fee <= 0x or Funded blowup 12m > 35%",
            "DU_DUNG": "EV/Fee +0.01x..+2.99x or blowup 15%..35%",
            "TOT": "EV/Fee +3.0x..+4.99x & blowup <= 15%",
            "TOP_1_PCT": "EV/Fee >= +5.0x & blowup < 5% verified on live/forward fills",
        },
        "gap_to_top1_vi": gap,
    }


def _pack_mc_result(
    *,
    tier_id: str,
    firm_id: str,
    display_name: str,
    asset_class: str,
    dd_mode_eval: str,
    dd_mode_funded: str,
    vn_kyc_status: str,
    vn_kyc_eligible: bool,
    execution_status: str,
    verified_utc: str,
    n_paths: int,
    usd_vnd: float,
    total_fees_arr: np.ndarray,
    net_cf_arr: np.ndarray,
    max_oop_arr: np.ndarray,
    first_pass_day: np.ndarray,
    first_fail_day: np.ndarray,
    first_payout_day: np.ndarray,
    funded_12m_status: np.ndarray,
    payout_count_arr: np.ndarray,
    hard_breaches_arr: np.ndarray,
    soft_dll_arr: np.ndarray | None,
) -> dict[str, Any]:
    mean_fees = float(np.mean(total_fees_arr))
    mean_net = float(np.mean(net_cf_arr))
    med_net = float(np.median(net_cf_arr))
    p10_net = float(np.percentile(net_cf_arr, 10))
    p90_net = float(np.percentile(net_cf_arr, 90))
    oop95 = float(np.percentile(max_oop_arr, 95))
    ev_per_fee = mean_net / max(1e-6, mean_fees)
    prob_net_le_zero_pct = float(100.0 * np.mean(net_cf_arr <= 0.0))

    # Fixed 12m (252 trading days) Funded blowup rate with explicit denominator & censoring
    n_survived_12m = int(np.sum(funded_12m_status == 1))
    n_blew_12m = int(np.sum(funded_12m_status == 2))
    n_censored_12m = int(np.sum(funded_12m_status == 3))
    n_uncensored_funded = n_survived_12m + n_blew_12m
    funded_blowup_12m_pct: float | None = (
        round(100.0 * n_blew_12m / n_uncensored_funded, 2) if n_uncensored_funded > 0 else None
    )
    wilson_ub_95 = wilson_upper_95(n_blew_12m, n_uncensored_funded)
    wilson_ub_95_pct = round(wilson_ub_95 * 100.0, 2) if wilson_ub_95 is not None else None

    # Payout #1 latency: both conditional & unconditional (capped at 730 calendar days per Law 13)
    pay1_mask = first_payout_day >= 0
    p_payout_1_pct = float(100.0 * np.mean(pay1_mask))
    p_payout_3_pct = float(100.0 * np.mean(payout_count_arr >= 3))
    if np.any(pay1_mask):
        med_days_to_pay1_cond: float | None = round(
            float(np.median(first_payout_day[pay1_mask])) * CALENDAR_DAYS_PER_TRADING_DAY, 1
        )
    else:
        med_days_to_pay1_cond = None
    uncond_cal_days = np.where(
        pay1_mask,
        first_payout_day.astype(np.float64) * CALENDAR_DAYS_PER_TRADING_DAY,
        730.0,
    )
    med_days_to_pay1_uncond = round(float(np.median(uncond_cal_days)), 1)

    pfp = _summarize_pass_fail_pending(first_pass_day, first_fail_day)
    grade = _grade_prop_scorecard(
        asset_class=asset_class,
        ev_per_fee=ev_per_fee,
        funded_blowup_12m_pct=funded_blowup_12m_pct,
        vn_kyc_eligible=vn_kyc_eligible,
    )

    return {
        "tier_id": tier_id,
        "firm_id": firm_id,
        "display_name": display_name,
        "asset_class": asset_class,
        "dd_mode_eval": dd_mode_eval,
        "dd_mode_funded": dd_mode_funded,
        "vn_kyc_status": vn_kyc_status,
        "vn_kyc_eligible": vn_kyc_eligible,
        "execution_status": execution_status,
        "verified_utc": verified_utc,
        "resolution_label_vi": RESOLUTION_LABEL_VI,
        "resolution_tag": RESOLUTION_TAG,
        "evidence_stage": EVIDENCE_STAGE,
        "n_paths": n_paths,
        "pass_fail_pending": pfp,
        "ev_per_usd_fee": round(ev_per_fee, 3),
        "avg_fees_24m_usd": round(mean_fees, 2),
        "avg_fees_24m_vnd": round(mean_fees * usd_vnd, 0),
        "mean_net_24m_usd": round(mean_net, 2),
        "mean_net_24m_vnd": round(mean_net * usd_vnd, 0),
        "median_net_24m_usd": round(med_net, 2),
        "median_net_24m_vnd": round(med_net * usd_vnd, 0),
        "p10_net_24m_usd": round(p10_net, 2),
        "p90_net_24m_usd": round(p90_net, 2),
        "oop95_usd": round(oop95, 2),
        "oop95_vnd": round(oop95 * usd_vnd, 0),
        "prob_net_le_zero_pct": round(prob_net_le_zero_pct, 2),
        "p_payout_1_pct": round(p_payout_1_pct, 2),
        "p_payout_3_pct": round(p_payout_3_pct, 2),
        "median_cal_days_to_payout1_conditional": med_days_to_pay1_cond,
        "median_cal_days_to_payout1_unconditional": med_days_to_pay1_uncond,
        "funded_blowup_12m_pct": funded_blowup_12m_pct,
        "funded_blowup_12m_wilson_ub95_pct": wilson_ub_95_pct,
        "funded_12m_uncensored_n": n_uncensored_funded,
        "funded_12m_blew_n": n_blew_12m,
        "funded_12m_censored_n": n_censored_12m,
        "funded_12m_power_note": (
            "Requires >= 299 independent uncensored observations for 95% Wilson upper bound < 1.0%."
        ),
        "mean_firm_hard_breaches": round(float(np.mean(hard_breaches_arr)), 3),
        "mean_soft_dll_pauses": round(float(np.mean(soft_dll_arr)), 3) if soft_dll_arr is not None else 0.0,
        "domain_scorecard": grade,
    }


def run_cme_4firm_monte_carlo(
    dev_returns_le_2024: Mapping[str, Any] | np.ndarray | Sequence[float],
    *,
    n_paths: int = 10_000,
    seed: int = 42,
    dates: Sequence[str] | None = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    block_len: int = DEFAULT_BLOCK_LEN,
    cme_eval_scale: float = 1.5,
    cme_funded_scale: float = 1.0,
    ftmo_eval_scale: float = 2.5,
    ftmo_funded_scale: float = 1.5,
    mfe_giveback_mult: float = 0.35,
    mae_intrabar_mult: float = 0.25,
    tier_ids: Sequence[str] = PRIMARY_4FIRM_BENCHMARK_TIERS,
    fx_rates_path: Path = DEFAULT_FX_RATES_PATH,
    firms_catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH,
    write_output_path: Path | None = None,
) -> dict[str, Any]:
    """Run 10,000-path shared-market-path MC comparing all 4 CME firms vs FTMO 10K/100K incumbents.

    Emits balanced Law 13–15 metrics and explicit decision `GO_WAVE5_FUTURES` or `SKIP`.
    Strictly validates `dev_returns_le_2024 < 2025-01-01` (fail-closed `HoldoutLockError` under `python -O`).
    """
    t0 = time.perf_counter()
    enforce_holdout_zero_rows(0, context="wave4.cme_intraday_prop_feasibility")
    n_p = _require_int(n_paths, "n_paths", min_value=50, max_value=200_000)
    sd = _require_int(seed, "seed", min_value=0)
    h_days = _require_int(horizon_days, "horizon_days", min_value=63, max_value=1512)
    b_len = _require_int(block_len, "block_len", min_value=1, max_value=21)
    _require_finite_float(cme_eval_scale, "cme_eval_scale", min_value=0.1, max_value=10.0)
    _require_finite_float(cme_funded_scale, "cme_funded_scale", min_value=0.1, max_value=10.0)
    _require_finite_float(ftmo_eval_scale, "ftmo_eval_scale", min_value=0.1, max_value=10.0)
    _require_finite_float(ftmo_funded_scale, "ftmo_funded_scale", min_value=0.1, max_value=10.0)
    mfe_m = _require_finite_float(mfe_giveback_mult, "mfe_giveback_mult", min_value=0.0, max_value=2.0)
    mae_m = _require_finite_float(mae_intrabar_mult, "mae_intrabar_mult", min_value=0.0, max_value=2.0)

    ret_arr, _valid_dates, min_date, max_date = _extract_validated_dev_returns(dev_returns_le_2024, dates=dates)
    usd_vnd, fx_meta = load_ssot_fx_usd_vnd(fx_rates_path)
    ftmo_specs = load_ftmo_incumbent_specs(firms_catalog_path)
    strategy_metrics = compute_strategy_balanced_metrics(ret_arr)

    # Shared circular-block-bootstrap matrix so ALL 4 CME firms and BOTH FTMO incumbents see identical paths
    n_src = int(ret_arr.size)
    rng = np.random.default_rng(sd)
    n_blocks = (h_days + b_len - 1) // b_len
    starts = rng.integers(0, n_src, size=(n_p, n_blocks))
    offsets = np.arange(b_len, dtype=np.int64)
    idx_mat = (starts[:, :, None] + offsets[None, None, :]) % n_src
    sim_ret = np.ascontiguousarray(ret_arr[idx_mat.reshape(n_p, n_blocks * b_len)[:, :h_days]], dtype=np.float64)

    vn_card_fee = 0.025
    vn_withdraw_fee = 0.015

    # 1. Evaluate all requested CME 4-firm tiers
    cme_results: dict[str, dict[str, Any]] = {}
    for tid in tier_ids:
        if tid not in CME_4FIRM_CATALOG:
            raise KeyError(f"Unknown CME tier_id {tid!r}; valid={sorted(CME_4FIRM_CATALOG.keys())}")
        spec = CME_4FIRM_CATALOG[tid]
        out_tuple = _simulate_cme_tier_numba(
            sim_ret=sim_ret,
            nominal_usd=spec.nominal_usd,
            is_straight_to_funded=1 if spec.is_straight_to_funded else 0,
            profit_target_usd=spec.profit_target_usd,
            max_dd_usd=spec.max_dd_usd,
            eval_is_intraday_dd=1 if spec.eval_dd_mode == TrailingDDMode.INTRADAY_UNREALIZED_TRAILING.value else 0,
            funded_is_intraday_dd=1 if spec.funded_dd_mode == TrailingDDMode.INTRADAY_UNREALIZED_TRAILING.value else 0,
            lock_floor_above_initial=spec.lock_floor_above_initial_usd,
            daily_loss_limit_usd=spec.daily_loss_limit_usd,
            daily_loss_is_hard=1 if spec.daily_loss_is_hard_breach else 0,
            eval_consistency_share=spec.eval_consistency_max_day_share,
            funded_consistency_share=spec.funded_consistency_max_day_share,
            min_eval_days=spec.min_eval_trading_days,
            monthly_sub_usd=spec.monthly_sub_usd,
            one_time_fee_usd=spec.one_time_fee_usd,
            activation_fee_usd=spec.activation_fee_usd,
            reset_fee_usd=spec.reset_fee_usd,
            payout_min_win_days=spec.payout_min_win_days,
            payout_win_day_thresh=spec.payout_win_day_threshold_usd,
            payout_min_buffer=spec.payout_min_buffer_usd,
            payout_max_share=spec.payout_max_withdraw_share,
            payout_cap_usd=spec.payout_cap_per_request_usd,
            payout_cadence_days=spec.payout_cadence_days,
            first_100_cap=spec.first_100pct_split_cap_usd,
            post_cap_split=spec.post_cap_split_frac,
            max_attempts=spec.max_attempts,
            eval_scale=cme_eval_scale,
            funded_scale=cme_funded_scale,
            card_fx_fee_frac=vn_card_fee,
            withdrawal_fee_frac=vn_withdraw_fee,
            mfe_giveback_mult=mfe_m,
            mae_intrabar_mult=mae_m,
        )
        cme_results[tid] = _pack_mc_result(
            tier_id=spec.tier_id,
            firm_id=spec.firm_id,
            display_name=f"{spec.firm_display_name} — {spec.program_name}",
            asset_class="CME_FUTURES_INTRADAY",
            dd_mode_eval=spec.eval_dd_mode,
            dd_mode_funded=spec.funded_dd_mode,
            vn_kyc_status=spec.vn_kyc_status,
            vn_kyc_eligible=spec.vn_kyc_eligible,
            execution_status=spec.execution_status,
            verified_utc=spec.verified_utc,
            n_paths=n_p,
            usd_vnd=usd_vnd,
            total_fees_arr=out_tuple[0],
            net_cf_arr=out_tuple[1],
            max_oop_arr=out_tuple[2],
            first_pass_day=out_tuple[3],
            first_fail_day=out_tuple[4],
            first_payout_day=out_tuple[5],
            funded_12m_status=out_tuple[6],
            payout_count_arr=out_tuple[7],
            hard_breaches_arr=out_tuple[8],
            soft_dll_arr=out_tuple[9],
        )

    # 2. Evaluate incumbent FTMO 10K & FTMO 100K on the EXACT SAME shared Dev paths
    incumbent_results: dict[str, dict[str, Any]] = {}
    for cid, lot_eff in (("ftmo_standard_10k", 0.94), ("ftmo_standard_100k", 0.995)):
        cfg = ftmo_specs[cid]
        inc_tuple = _simulate_ftmo_incumbent_numba(
            sim_ret=sim_ret,
            capital_usd=cfg["capital_usd"],
            fee_usd=cfg["fee_orig_usd"],
            p1_target_frac=cfg["p1_target_frac"],
            p2_target_frac=cfg["p2_target_frac"],
            daily_dd_frac=cfg["daily_loss_limit_frac"],
            static_dd_frac=cfg["static_loss_limit_frac"],
            min_trading_days=cfg["min_trading_days"],
            payout_split_frac=cfg["payout_split_frac"],
            payout_cycle_days=cfg["payout_cycle_trading_days"],
            fee_refund_frac=cfg["fee_refund_external_cash_frac"],
            card_fx_fee_frac=cfg["card_fx_fee_frac"],
            withdrawal_fee_frac=cfg["withdrawal_fee_frac"],
            eval_scale=ftmo_eval_scale,
            funded_scale=ftmo_funded_scale,
            lot_efficiency=lot_eff,
            max_attempts=8,
        )
        incumbent_results[cid] = _pack_mc_result(
            tier_id=cid,
            firm_id="ftmo",
            display_name=cfg["display_name"],
            asset_class="CFD_PROP_MT5",
            dd_mode_eval=TrailingDDMode.STATIC_BALANCE.value,
            dd_mode_funded=TrailingDDMode.STATIC_BALANCE.value,
            vn_kyc_status=VNKycStatus.ALLOWED_FULL_VN.value,
            vn_kyc_eligible=True,
            execution_status=cfg["execution_status"],
            verified_utc=cfg["verified_utc"],
            n_paths=n_p,
            usd_vnd=usd_vnd,
            total_fees_arr=inc_tuple[0],
            net_cf_arr=inc_tuple[1],
            max_oop_arr=inc_tuple[2],
            first_pass_day=inc_tuple[3],
            first_fail_day=inc_tuple[4],
            first_payout_day=inc_tuple[5],
            funded_12m_status=inc_tuple[6],
            payout_count_arr=inc_tuple[7],
            hard_breaches_arr=inc_tuple[8],
            soft_dll_arr=None,
        )

    # 3. Deterministic Fail-Closed Decision: GO_WAVE5_FUTURES vs SKIP
    inc_10k = incumbent_results["ftmo_standard_10k"]
    inc_100k = incumbent_results["ftmo_standard_100k"]

    vn_eligible_cme = [r for r in cme_results.values() if r["vn_kyc_eligible"]]
    best_vn_cme = max(vn_eligible_cme, key=lambda x: x["ev_per_usd_fee"]) if vn_eligible_cme else None
    best_overall_cme = max(cme_results.values(), key=lambda x: x["ev_per_usd_fee"])

    failed_gates: list[str] = []
    if best_vn_cme is None:
        failed_gates.append("NO_VN_KYC_ELIGIBLE_CME_FIRM")
    else:
        if best_vn_cme["ev_per_usd_fee"] < 3.0:
            failed_gates.append(f"EV_PER_FEE_BELOW_3X ({best_vn_cme['ev_per_usd_fee']:.3f}x < 3.000x)")
        ftmo_floor = max(3.0, inc_10k["ev_per_usd_fee"] * 0.85)
        if best_vn_cme["ev_per_usd_fee"] < ftmo_floor:
            failed_gates.append(
                f"UNDERPERFORMS_INCUMBENT_FTMO_10K ({best_vn_cme['ev_per_usd_fee']:.3f}x < {ftmo_floor:.3f}x)"
            )
        if best_vn_cme["median_net_24m_usd"] <= 0.0:
            failed_gates.append(f"NON_POSITIVE_MEDIAN_24M_NET ({best_vn_cme['median_net_24m_usd']:.2f} USD)")
        if best_vn_cme["prob_net_le_zero_pct"] > 25.0:
            failed_gates.append(f"PROB_NET_LE_ZERO_GT_25PCT ({best_vn_cme['prob_net_le_zero_pct']:.2f}%)")
        blowup = best_vn_cme["funded_blowup_12m_pct"]
        if blowup is None or blowup > 15.0:
            blowup_str = f"{blowup:.2f}%" if blowup is not None else "None"
            failed_gates.append(f"FUNDED_BLOWUP_12M_GT_15PCT ({blowup_str})")
        if best_vn_cme["p_payout_1_pct"] < 65.0:
            failed_gates.append(f"P_PAYOUT1_BELOW_65PCT ({best_vn_cme['p_payout_1_pct']:.2f}%)")

    decision = "GO_WAVE5_FUTURES" if not failed_gates else "SKIP"

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "elapsed_sec": round(time.perf_counter() - t0, 3),
        "invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_cutoff_day": HOLDOUT_CUTOFF_DAY,
            "holdout_rows_analysed": 0,
            "resolution_label_vi": RESOLUTION_LABEL_VI,
            "resolution_tag": RESOLUTION_TAG,
            "evidence_stage": EVIDENCE_STAGE,
        },
        "simulation_config": {
            "n_paths": n_p,
            "seed": sd,
            "horizon_days": h_days,
            "block_len": b_len,
            "cme_eval_scale": cme_eval_scale,
            "cme_funded_scale": cme_funded_scale,
            "ftmo_eval_scale": ftmo_eval_scale,
            "ftmo_funded_scale": ftmo_funded_scale,
            "mfe_giveback_mult_model_assumption": mfe_m,
            "mae_intrabar_mult_model_assumption": mae_m,
            "usd_vnd_rate": usd_vnd,
            "fx_verified_utc": fx_meta.get("verified_utc"),
            "dev_input_min_date": min_date,
            "dev_input_max_date": max_date,
            "dev_input_days": int(ret_arr.size),
        },
        "dev_strategy_metrics": strategy_metrics,
        "decision": decision,
        "decision_rationale": {
            "verdict": decision,
            "failed_gates": failed_gates,
            "vn_eligible_best_tier": best_vn_cme["tier_id"] if best_vn_cme else None,
            "vn_eligible_best_ev_per_fee": best_vn_cme["ev_per_usd_fee"] if best_vn_cme else None,
            "overall_technical_best_tier": best_overall_cme["tier_id"],
            "overall_technical_best_ev_per_fee": best_overall_cme["ev_per_usd_fee"],
            "incumbent_ftmo_10k_ev_per_fee": inc_10k["ev_per_usd_fee"],
            "incumbent_ftmo_100k_ev_per_fee": inc_100k["ev_per_usd_fee"],
            "promotion_thresholds": {
                "vn_kyc_eligible": True,
                "min_ev_per_usd_fee": 3.0,
                "min_ratio_vs_ftmo_10k": 0.85,
                "min_median_net_24m_usd": 0.01,
                "max_prob_net_le_zero_pct": 25.0,
                "max_funded_blowup_12m_pct": 15.0,
                "min_p_payout_1_pct": 65.0,
            },
        },
        "cme_4firm_rule_catalog": {tid: asdict(CME_4FIRM_CATALOG[tid]) for tid in tier_ids},
        "vn_kyc_feasibility_matrix": build_vn_kyc_feasibility_matrix(),
        "cme_4firm_results": cme_results,
        "incumbent_ftmo_results": incumbent_results,
    }

    payload_hash = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    result["report_sha256"] = payload_hash

    if write_output_path is not None:
        out_path = Path(write_output_path).resolve()
        allowed_dir = DEFAULT_OUTPUT_DIR.resolve()
        try:
            out_path.relative_to(allowed_dir)
        except ValueError as exc:
            raise ValueError(
                f"Wave 4 CME outputs MUST reside under {allowed_dir}; refused writing to {out_path}"
            ) from exc
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return result


def load_dev_cme_sleeve_returns(returns_path: Path = SLEEVE5_RETURNS_PATH) -> dict[str, float]:
    """Load sealed Dev `< 2025-01-01` Sleeve #5 CME returns with strict `-O`-safe Holdout enforcement."""
    if not returns_path.is_file():
        raise FileNotFoundError(f"Dev CME returns file missing: {returns_path}")
    payload = json.loads(returns_path.read_text(encoding="utf-8"))
    enforce_holdout_zero_rows(payload.get("holdout_rows_analysed", -1), context="wave4.load_dev_cme_sleeve_returns")
    rmap = payload.get("daily_returns")
    if not isinstance(rmap, dict) or not rmap:
        raise ValueError(f"Invalid or empty daily_returns in {returns_path}")
    enforce_pre_holdout_dates(
        list(rmap.keys()),
        context="wave4.load_dev_cme_sleeve_returns",
        cutoff_day=HOLDOUT_CUTOFF_DAY,
        allow_empty=False,
    )
    return {str(k): _require_finite_float(v, f"daily_returns[{k}]") for k, v in sorted(rmap.items())}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 4 (W4-G15): 4-Firm CME Futures Intraday Prop Feasibility Engine")
    ap.add_argument("--n-paths", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--returns-json", type=Path, default=SLEEVE5_RETURNS_PATH)
    ap.add_argument("--cme-cache-dir", type=Path, default=CME_CACHE_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_JSON)
    args = ap.parse_args(argv)

    # Verify sealed CME D1 cache strictly <= 2024-12-31 before running simulation
    d1_check = load_cme_dev_d1_strict(cache_dir=args.cme_cache_dir, cutoff_date=DEV_CUTOFF_DATE)
    dev_ret_map = load_dev_cme_sleeve_returns(args.returns_json)

    res = run_cme_4firm_monte_carlo(
        dev_ret_map,
        n_paths=args.n_paths,
        seed=args.seed,
        write_output_path=args.out,
    )
    print(
        json.dumps(
            {
                "decision": res["decision"],
                "elapsed_sec": res["elapsed_sec"],
                "holdout_rows_analysed": res["invariants"]["holdout_rows_analysed"],
                "cme_d1_strict_max_date": d1_check["max_date"],
                "cme_d1_symbols": d1_check["symbols_loaded"],
                "output_path": str(args.out),
                "report_sha256": res["report_sha256"],
                "decision_rationale": res["decision_rationale"],
            },
            indent=2,
        )
    )
    return 0


__all__ = [
    "BreachKind",
    "CME_4FIRM_CATALOG",
    "CME_EXECUTION_STATUS",
    "CMEFlatCloseDecision",
    "CMEFuturesPropTierSpec",
    "CMEPropDDStateMachine",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_OUTPUT_JSON",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRIMARY_4FIRM_BENCHMARK_TIERS",
    "RULES_VERIFIED_UTC",
    "SCHEMA_VERSION",
    "TZ_CHICAGO",
    "TrailingDDMode",
    "VNKycStatus",
    "apply_1510_ct_intraday_flatten_to_positions",
    "build_vn_kyc_feasibility_matrix",
    "compute_strategy_balanced_metrics",
    "evaluate_cme_1510_ct_flatten",
    "get_1510_ct_utc_cutoff",
    "load_dev_cme_sleeve_returns",
    "load_ftmo_incumbent_specs",
    "load_ssot_fx_usd_vnd",
    "resolve_chicago_tz",
    "run_cme_4firm_monte_carlo",
    "wilson_upper_95",
]


if __name__ == "__main__":
    raise SystemExit(main())
