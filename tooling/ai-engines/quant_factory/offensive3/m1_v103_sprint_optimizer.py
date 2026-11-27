"""Front 1 (Total Offensive #3 v3.5): `.set`-only Prop Challenge Accelerator for `PORT_7E v1.03`.

Optimizes `.set`-only Eval (P1/P2) parameters for immutable `Naqex_Master_Prop7E_v103.mq5`
while locking Funded strictly to `1.0x`, tight `Amber 3.5% / Red 6.0%`, `TotalOpenCap <= 2.25%`
(`< 1%` Funded 12m breach!), Shield B2 `SpreadGuard` ON, and Shield B3 `6-CCY +-10m` red-news
filter ON across ALL phases.

STRICT SAFETY & PARITY INVARIANTS (`G10`, `H5`, `[ARCH-02]`):
  - ZERO modifications to `Naqex_Master_Prop7E_v103.mq5`, `Naqex_Master_Prop7E.mq5`,
    or `frozen_9e_tapes_v2.{json,npz}`.
  - ZERO bare `assert` statements anywhere in this module (`[ARCH-02]`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `holdout_rows_analysed = 0`,
    `max_day < "2025-01-01"`, `max_ts < 1735689600`.
  - Exact `Naqex_Master_Prop7E_v103.mq5` parity:
      * Hard total open risk ceiling `EffectiveTotalOpenRiskCapPct() <= 3.00%` (`L142-150`, `L1083`)
        -> worst simultaneous `1.25x` gap shock `<= 3.75% <= 4.50%`!
      * Intraday `dailyHeadroom < 2.0%` throttle/taper (`L519-526`) + relative AMBER/RED (`L502-516`)
        + `InpSizingMode == 1` barrier headroom taper (`L528-543`) + `InpKillStaticDdPct` (`L996`).
      * Exact `dailyDdPct` Mode 1 (`g_dayAnchorBal / InitialBalance`, `Europe/Prague` DST for FTMO)
        vs Mode 0 (`max(bal, eq)` denominator, `17:00 America/New_York` US DST for The5ers,
        `>= 3` profitable days `>= +0.5%`, `+-2m` red-news ban in BOTH Eval & Funded).
      * Exact SSOT `available_vn = true` SKUs from `configs/ssot/firms_catalog.json`:
        `ftmo_standard_10k`, `ftmo_standard_50k`, `ftmo_standard_100k`,
        `ftmo_swing_10k`, `ftmo_swing_25k`, `the5ers_hs_5k_classic`, `the5ers_hs_5k_new`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
HOLDOUT_STOP_TS: int = 1735689600  # 2025-01-01T00:00:00Z
CLUSTER_A_CUTOFF_DAY: str = "2021-01-01"
CLUSTER_A_MAX_YEAR: int = 2020

TRADING_DAYS_PER_YEAR: int = 252
TRADING_DAYS_PER_MONTH: int = 21
CALENDAR_DAYS_PER_TRADING_DAY: float = 365.2425 / 252.0
BLOCK_LEN: int = 5
DEFAULT_SEED: int = 20261127
DEFAULT_N_PATHS: int = 10_000
DEFAULT_HORIZON_DAYS: int = 756  # 36 trading months

HARD_TOTAL_OPEN_CEILING_PCT: float = 3.00
FUNDED_MAX_TOTAL_OPEN_CAP_PCT: float = 2.25
FUNDED_MAX_KILL_STATIC_DD_PCT: float = 8.00  # OPS-2 account_phase_preflight.py hard Funded ceiling
FUNDED_LOCKED_MULT: float = 1.00
OFFICIAL_V103_BASELINE_EV_PER_FEE: float = 8.75  # FLASHCRASH-PARETO-DEFENSE-V103-20261127.md

# Exact 7-SKU Offensive #3 focus allowlist (`available_vn = true` in `configs/ssot/firms_catalog.json`).
TARGET_SKUS: tuple[str, ...] = (
    "ftmo_standard_10k",
    "ftmo_standard_50k",
    "ftmo_standard_100k",
    "ftmo_swing_10k",
    "ftmo_swing_25k",
    "the5ers_hs_5k_classic",
    "the5ers_hs_5k_new",
)
# SKUs excluded from the 7-SKU Offensive #3 focus matrix:
# - `ftmo_swing_50k`: `available_vn=false` in `configs/ssot/firms_catalog.json`
# - `the5ers_hs_20k`: nonexistent in `configs/ssot/firms_catalog.json`
# - `ftmo_standard_25k`: `available_vn=true` in `configs/ssot/firms_catalog.json`, merely excluded
#   from the 7-SKU Offensive #3 focus matrix (not unavailable/nonexistent)
FORBIDDEN_SKUS: frozenset[str] = frozenset({"ftmo_swing_50k", "ftmo_standard_25k", "the5ers_hs_20k"})

ROOT: Path = Path(__file__).resolve().parents[4]
DEFAULT_DERIVED_DIR: Path = ROOT / ".runtime/hot-m1-cache/_derived"
DEFAULT_M1_CACHE_DIR: Path = ROOT / ".runtime/hot-m1-cache"
DEFAULT_FX_RATES_PATH: Path = ROOT / "tooling/ai-engines/configs/ssot/fx_rates.json"
DEFAULT_FIRMS_CATALOG_PATH: Path = ROOT / "tooling/ai-engines/configs/ssot/firms_catalog.json"
DEFAULT_CAL_523_PATH: Path = ROOT / "tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json"
DEFAULT_OUT_JSON: Path = ROOT / "private_vault/strategies/offensive3_v3/m1_v103_sprint_results.json"
DEFAULT_PRESETS_DIR: Path = ROOT / "private_vault/presets/offensive3_v3"

CORE7_IDS: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
)

CORE7_BASE_RISK_FRAC: dict[str, float] = {
    "E1_USDJPY_TOKYO": 0.001606,
    "E2_USDJPY_EXP80": 0.005894,
    "E3_GBPUSD_VH": 0.0075,
    "E4_US100_SESS40": 0.0050,
    "E5_US100_RS1130": 0.0050,
    "E6_EURJPY_VOLCOMP": 0.0050,
    "E7_USDJPY_NY10ET": 0.0050,
}

ENGINE_ASSET_MAP: dict[str, str] = {
    "E1_USDJPY_TOKYO": "USDJPY",
    "E2_USDJPY_EXP80": "USDJPY",
    "E3_GBPUSD_VH": "GBPUSD",
    "E4_US100_SESS40": "US100",
    "E5_US100_RS1130": "US100",
    "E6_EURJPY_VOLCOMP": "EURJPY",
    "E7_USDJPY_NY10ET": "USDJPY",
}

M1_SPREAD_SPECS: dict[str, tuple[str, float]] = {
    "USDJPY": ("usdjpy", 1.0),
    "GBPUSD": ("gbpusd", 1.0),
    "EURJPY": ("eurjpy", 1.0),
    "US100": ("us100", 0.1),
}

SPREAD_GUARD_CALIBRATION_RULE: str = "ceil_to_5(max(session_A_p99_9, 1.10 * entry_A_p99_9))"
TZ_NY: ZoneInfo = ZoneInfo("America/New_York")
TZ_PRAGUE: ZoneInfo = ZoneInfo("Europe/Prague")


@dataclass(frozen=True)
class SprintCandidate:
    """Pure `.set`-only configuration for immutable `Naqex_Master_Prop7E_v103.mq5`."""

    candidate_id: str
    group: str
    label: str
    # Eval P1 / P2 parameters
    p1_mult: float
    p2_mult: float
    p1_lock_trigger: float  # Fraction of P1 target (0.0 = disabled)
    p1_lock_mult: float
    p2_lock_trigger: float  # Fraction of P2 target (0.0 = disabled)
    p2_lock_mult: float
    eval_symcap_pct: float
    eval_usd_cluster_pct: float
    eval_jpy_cluster_pct: float
    eval_idx_cluster_pct: float
    eval_total_open_cap_pct: float
    eval_amber_dd_pct: float
    eval_amber_mult: float
    eval_red_dd_pct: float
    eval_red_mult: float
    eval_p1_kill_daily_pct: float
    eval_p2_kill_daily_pct: float
    eval_p1_kill_static_pct: float
    eval_p2_kill_static_pct: float
    eval_sizing_mode: int = 0  # 0=STATIC_PHASE_LOCK, 1=BARRIER_HEADROOM_MIN
    # Funded parameters (STRICTLY SEPARATE `.set`; locked 1.0x for all Sprint candidates!)
    funded_mult: float = 1.00
    funded_symcap_pct: float = 1.00
    funded_usd_cluster_pct: float = 1.50
    funded_jpy_cluster_pct: float = 1.25
    funded_idx_cluster_pct: float = 1.00
    funded_total_open_cap_pct: float = 2.00
    funded_amber_dd_pct: float = 3.50
    funded_amber_mult: float = 0.65
    funded_red_dd_pct: float = 6.00
    funded_red_mult: float = 0.40
    funded_kill_daily_pct: float = 2.50
    funded_kill_static_pct: float = FUNDED_MAX_KILL_STATIC_DD_PCT
    # Shield B2/B3 invariants (ON across ALL phases!)
    news_pad_sec: int = 600
    use_6ccy_news_10m: bool = True
    enable_spread_guard: bool = True


# ---------------------------------------------------------------------------
# 1. Exact `Naqex_Master_Prop7E_v103.mq5` Parity Helpers
# ---------------------------------------------------------------------------


def _require_finite_number(value: Any, name: str) -> float:
    """Fail-closed guard rejecting `bool`, non-numeric, `NaN`, and `+-Inf` inputs."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"INVALID_NUMERIC_INPUT: {name} must be a finite real number (got {value!r})")
    fval = float(value)
    if not math.isfinite(fval):
        raise ValueError(f"NON_FINITE_NUMERIC_INPUT: {name} must be finite (got {value!r})")
    return fval


def _require_strict_int(value: Any, name: str) -> int:
    """Fail-closed guard rejecting `bool`, `float`, and non-integer inputs."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"INVALID_INT_INPUT: {name} must be a strict int (got {value!r})")
    return int(value)


def effective_total_open_risk_cap_pct(
    max_total_open_risk_pct: float,
    hard_total_open_ceiling_pct: float = HARD_TOTAL_OPEN_CEILING_PCT,
) -> float:
    """Exact mirror of `Naqex_Master_Prop7E_v103.mq5` `EffectiveTotalOpenRiskCapPct()` (`L142-150`, `L1083`)."""
    try:
        hard_ceil = _require_finite_number(hard_total_open_ceiling_pct, "hard_total_open_ceiling_pct")
        max_open = _require_finite_number(max_total_open_risk_pct, "max_total_open_risk_pct")
    except ValueError as exc:
        raise ValueError(f"V103_INIT_PARAMETERS_INCORRECT: {exc}") from exc
    if hard_ceil <= 0.0 or hard_ceil > HARD_TOTAL_OPEN_CEILING_PCT + 1e-12:
        raise ValueError(
            f"V103_INIT_PARAMETERS_INCORRECT: InpHardTotalOpenCeilingPct must be in (0.0, 3.00] "
            f"(got {hard_total_open_ceiling_pct!r})"
        )
    ceil_pct = min(hard_ceil, HARD_TOTAL_OPEN_CEILING_PCT)
    if max_open <= 0.0:
        return ceil_pct
    return min(max_open, ceil_pct)


def compute_v103_phase_risk_multiplier(
    *,
    base_phase_mult: float,
    daily_dd_pct: float,
    static_dd_pct: float,
    eq_profit_pct: float,
    realized_profit_pct: float,
    profit_lock_pct: float,
    profit_lock_mult: float,
    amber_dd_pct: float,
    amber_mult: float,
    red_dd_pct: float,
    red_mult: float,
    kill_daily_dd_pct: float,
    kill_static_dd_pct: float,
    target_profit_pct: float,
    sizing_mode: int = 0,
    profit_lock_basis_mode: int = 0,
) -> tuple[float, str]:
    """Bit-exact mirror of `Naqex_Master_Prop7E_v103.mq5::ComputePhaseRiskMultiplierV103` (`L467-545`)."""
    mult = float(base_phase_mult)
    regime = "NORMAL"
    eff_profit = float(realized_profit_pct) if profit_lock_basis_mode == 1 else float(eq_profit_pct)

    if profit_lock_basis_mode == 1:
        dd_brake_mult = float(base_phase_mult)
        dd_regime = ""
        if static_dd_pct >= red_dd_pct:
            dd_brake_mult = base_phase_mult * red_mult
            dd_regime = "RED_BRAKE"
        elif static_dd_pct >= amber_dd_pct:
            dd_brake_mult = base_phase_mult * amber_mult
            dd_regime = "AMBER_BRAKE"
        pl_mult = float(base_phase_mult)
        pl_active = profit_lock_pct > 0.0 and realized_profit_pct >= profit_lock_pct
        if pl_active:
            pl_mult = min(pl_mult, profit_lock_mult)
        mult = min(dd_brake_mult, pl_mult)
        if dd_regime and pl_active:
            regime = f"{dd_regime}+PROFIT_LOCK"
        elif dd_regime:
            regime = dd_regime
        elif pl_active:
            regime = "PROFIT_LOCK"
    else:
        if static_dd_pct >= red_dd_pct:
            mult = min(mult, base_phase_mult * red_mult)
            regime = "RED_BRAKE"
        elif static_dd_pct >= amber_dd_pct:
            mult = min(mult, base_phase_mult * amber_mult)
            regime = "AMBER_BRAKE"
        elif profit_lock_pct > 0.0 and eq_profit_pct >= profit_lock_pct:
            mult = min(mult, profit_lock_mult)
            regime = "PROFIT_LOCK"

    # L519-526: Intraday dailyHeadroom < 2.0% throttle/taper
    daily_headroom = max(0.0, float(kill_daily_dd_pct) - float(daily_dd_pct))
    if daily_headroom < 2.0:
        daily_scale = max(0.25, daily_headroom / 2.0)
        mult = min(mult, base_phase_mult * daily_scale)
        if regime == "NORMAL":
            regime = "DAILY_HEADROOM_TAPER"

    # L528-543: InpSizingMode == 1 (BARRIER_HEADROOM_MIN)
    if sizing_mode == 1:
        static_headroom = max(0.0, float(kill_static_dd_pct) - float(static_dd_pct))
        dd_scale = 1.0
        if static_headroom < 3.5:
            dd_scale = min(dd_scale, max(0.25, static_headroom / 3.5))
        if target_profit_pct > 0.0 and eff_profit > 0.0:
            rem_to_target = max(0.0, target_profit_pct - eff_profit)
            frac_rem = rem_to_target / target_profit_pct
            if frac_rem < 0.35:
                dd_scale = min(dd_scale, max(0.35, frac_rem / 0.35))
        mult = min(mult, base_phase_mult * dd_scale)
        if dd_scale < 0.99 and regime == "NORMAL":
            regime = "BARRIER_TAPER"

    return max(0.0, mult), regime


def compute_v103_daily_dd_pct(
    *,
    daily_reset_mode: int,
    initial_balance_usd: float,
    day_anchor_bal: float,
    day_anchor_eq: float,
    current_equity: float,
) -> float:
    """Exact mirror of `Naqex_Master_Prop7E_v103.mq5` `L971-973` Mode 1 (FTMO) vs Mode 0 (The5ers)."""
    mode = _require_strict_int(daily_reset_mode, "daily_reset_mode")
    if mode not in (0, 1):
        raise ValueError(f"INVALID_DAILY_RESET_MODE: expected 0 or 1 (got {daily_reset_mode!r})")
    init_bal = _require_finite_number(initial_balance_usd, "initial_balance_usd")
    anchor_bal = _require_finite_number(day_anchor_bal, "day_anchor_bal")
    anchor_eq = _require_finite_number(day_anchor_eq, "day_anchor_eq")
    cur_eq = _require_finite_number(current_equity, "current_equity")
    if mode == 1:
        if init_bal <= 0.0:
            return 0.0
        return max(0.0, ((anchor_bal - cur_eq) / init_bal) * 100.0)
    if anchor_eq <= 0.0:
        return 0.0
    return max(0.0, ((anchor_eq - cur_eq) / anchor_eq) * 100.0)


def trading_day_key_for_reset_tz(utc_ts: int, reset_tz: str) -> str:
    """Map UTC timestamp to exact firm trading-day boundary.

    - `Europe/Prague`: midnight `00:00 Europe/Prague` (FTMO EU DST).
    - `America/New_York`: `17:00 America/New_York` (The5ers US DST rollover).
    """
    if reset_tz == "America/New_York":
        dt_ny = datetime.fromtimestamp(int(utc_ts), TZ_NY)
        # Trading session for date D runs [17:00 NY on D-1, 17:00 NY on D)
        d = dt_ny.date() + timedelta(days=1) if dt_ny.hour >= 17 else dt_ny.date()
        return d.isoformat()
    if reset_tz == "Europe/Prague":
        return datetime.fromtimestamp(int(utc_ts), TZ_PRAGUE).date().isoformat()
    return datetime.fromtimestamp(int(utc_ts), UTC).date().isoformat()


def audit_tape_reset_crossings(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    engines: tuple[str, ...] = CORE7_IDS,
) -> dict[str, int]:
    """Verify zero overnight/reset crossings across both `00:00 Europe/Prague` and `17:00 America/New_York`."""
    cross_prague = 0
    cross_ny17 = 0
    mismatch_dk_ny17 = 0
    total_trades = 0
    for eng in engines:
        for dk, (row, stamps, _marks) in tapes.get(eng, {}).items():
            total_trades += 1
            t_ent = int(stamps[0])
            t_ext = int(row["exit"])
            p_ent = trading_day_key_for_reset_tz(t_ent, "Europe/Prague")
            p_ext = trading_day_key_for_reset_tz(t_ext, "Europe/Prague")
            n_ent = trading_day_key_for_reset_tz(t_ent, "America/New_York")
            n_ext = trading_day_key_for_reset_tz(t_ext, "America/New_York")
            if p_ent != p_ext:
                cross_prague += 1
            if n_ent != n_ext:
                cross_ny17 += 1
            if n_ent != dk:
                mismatch_dk_ny17 += 1
    return {
        "total_trades_checked": total_trades,
        "cross_prague_midnight": cross_prague,
        "cross_ny_1700_dst": cross_ny17,
        "ny_day_mismatch_vs_utc_day": mismatch_dk_ny17,
    }


def compute_honest_gap_shock_pct(
    *,
    mult: float,
    symcap_pct: float,
    usd_cluster_pct: float,
    jpy_cluster_pct: float,
    idx_cluster_pct: float,
    total_open_cap_pct: float,
    gap_mult: float = 1.25,
) -> dict[str, float | bool]:
    """Honest analytical worst-case simultaneous gap shock (NEVER clamped < 5%!)."""
    eff_tot = effective_total_open_risk_cap_pct(total_open_cap_pct, HARD_TOTAL_OPEN_CEILING_PCT)
    usdjpy_base = (
        CORE7_BASE_RISK_FRAC["E1_USDJPY_TOKYO"]
        + CORE7_BASE_RISK_FRAC["E2_USDJPY_EXP80"]
        + CORE7_BASE_RISK_FRAC["E7_USDJPY_NY10ET"]
    ) * 100.0
    us100_base = (CORE7_BASE_RISK_FRAC["E4_US100_SESS40"] + CORE7_BASE_RISK_FRAC["E5_US100_RS1130"]) * 100.0
    sym_map = {
        "USDJPY": usdjpy_base,
        "GBPUSD": CORE7_BASE_RISK_FRAC["E3_GBPUSD_VH"] * 100.0,
        "US100": us100_base,
        "EURJPY": CORE7_BASE_RISK_FRAC["E6_EURJPY_VOLCOMP"] * 100.0,
    }
    sym_eff = {s: min(v * mult, symcap_pct) for s, v in sym_map.items()}
    symcap_sum = sum(sym_eff.values())
    bounded_open = min(symcap_sum, eff_tot)
    usd_side = min(sym_eff["USDJPY"] + sym_eff["GBPUSD"], usd_cluster_pct, eff_tot)
    jpy_side = min(sym_eff["USDJPY"] + sym_eff["EURJPY"], jpy_cluster_pct, eff_tot)
    idx_side = min(sym_eff["US100"], idx_cluster_pct, eff_tot)
    gap_125 = bounded_open * float(gap_mult)
    gap_150 = bounded_open * 1.50
    return {
        "effective_total_open_cap_pct": round(eff_tot, 2),
        "bounded_open_risk_pct": round(bounded_open, 3),
        "worst_cluster_open_pct": round(max(usd_side, jpy_side, idx_side), 3),
        "gap_shock_125x_pct": round(gap_125, 3),
        "gap_shock_150x_pct": round(gap_150, 3),
        "safe_le_4_50_at_125x": gap_125 <= 4.50 + 1e-9,
        "safe_lt_5_00_at_150x": gap_150 < 5.00 - 1e-9,
    }


# ---------------------------------------------------------------------------
# 2. Direct Sealed Dev Tape Loader, Causal SpreadGuard & Red-News Filter
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def verify_pre_holdout_days(days: list[str] | tuple[str, ...]) -> int:
    """Fail-closed if ANY date string is `>= 2025-01-01`; returns `holdout_rows_analysed = 0`."""
    for d in days:
        ds = str(d)
        if ds >= HOLDOUT_CUTOFF_DAY or int(ds[:4]) > 2024:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: forbidden date >= {HOLDOUT_CUTOFF_DAY}: {ds}")
    return 0


def load_frozen_tapes_direct(
    derived_dir: Path = DEFAULT_DERIVED_DIR,
    *,
    stem: str = "frozen_9e_tapes_v2",
) -> dict[str, Any]:
    """Direct loader for immutable `frozen_9e_tapes_v2.{json,npz}` verifying `npz_sha256` & `< 2025-01-01`."""
    meta_path = derived_dir / f"{stem}.json"
    npz_path = derived_dir / f"{stem}.npz"
    if not meta_path.is_file() or not npz_path.is_file():
        raise FileNotFoundError(f"Missing frozen tape cache files: {meta_path} / {npz_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected_sha = str(meta.get("npz_sha256") or "")
    actual_sha = _sha256_file(npz_path)
    if not expected_sha or actual_sha != expected_sha:
        raise ValueError(f"FROZEN_TAPES_SHA_MISMATCH: expected={expected_sha[:16]} actual={actual_sha[:16]}")

    ext_days = sorted(str(d) for d in meta["ext_days"])
    if not ext_days:
        raise ValueError("Empty ext_days in frozen_9e_tapes_v2.json")
    verify_pre_holdout_days(ext_days)
    max_day = max(ext_days)
    if max_day >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: max_day={max_day} >= {HOLDOUT_CUTOFF_DAY}")

    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    with np.load(npz_path, allow_pickle=False) as z:
        for eng, eng_meta in meta["tapes"].items():
            days_list = [str(d) for d in eng_meta["days"]]
            verify_pre_holdout_days(days_list)
            rows_map = eng_meta["rows"]
            stamps_all = np.asarray(z[f"{eng}__stamps"], dtype=np.int64)
            marks_all = np.asarray(z[f"{eng}__marks"], dtype=np.float64)
            offsets = np.asarray(z[f"{eng}__offsets"], dtype=np.int64)
            if len(stamps_all) > 0 and int(stamps_all.max()) >= HOLDOUT_STOP_TS:
                raise ValueError(
                    f"HOLDOUT_LOCK_VIOLATION: tape {eng} max timestamp {int(stamps_all.max())} >= {HOLDOUT_STOP_TS}"
                )
            day_map: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
            for idx, dk in enumerate(days_list):
                s0 = int(offsets[idx])
                s1 = int(offsets[idx + 1])
                day_map[dk] = (rows_map[dk], stamps_all[s0:s1], marks_all[s0:s1])
            tapes[eng] = day_map

    return {
        "schema": str(meta.get("schema", "")),
        "binding_sha256": str(meta.get("binding_sha256", "")),
        "npz_sha256": actual_sha,
        "ext_days": ext_days,
        "max_day": max_day,
        "holdout_rows_analysed": 0,
        "tapes": tapes,
    }


def load_red_news_calendar_6ccy(cal_path: Path = DEFAULT_CAL_523_PATH) -> dict[str, list[tuple[int, str, int]]]:
    """Load 6-CCY red-news JSON (enforcing `< 2025-01-01` and BoJ `EST03UTC` `+-3600s`)."""
    raw = json.loads(cal_path.read_text(encoding="utf-8"))
    by_day: dict[str, list[tuple[int, str, int]]] = {}
    if "events" in raw:
        for ev in raw["events"]:
            ts = int(ev["utc_ts"])
            if ts >= HOLDOUT_STOP_TS:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: ts={ts}")
            dk = datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
            if dk >= HOLDOUT_CUTOFF_DAY or int(dk[:4]) > 2024:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: day={dk}")
            ccy = str(ev["ccy"]).upper()
            ev_name = str(ev.get("event", "")).upper()
            bsec = int(ev.get("blackout_sec", 3600 if "EST03UTC" in ev_name else 300))
            by_day.setdefault(dk, []).append((ts, ccy, bsec))
        return by_day
    if "events_by_day" in raw:
        for dk, evs in raw["events_by_day"].items():
            dks = str(dk)
            if dks >= HOLDOUT_CUTOFF_DAY or int(dks[:4]) > 2024:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: day={dks}")
            by_day[dks] = []
            for ev in evs:
                ts = int(ev["utc_ts"])
                if ts >= HOLDOUT_STOP_TS:
                    raise ValueError(f"HOLDOUT_LOCK_VIOLATION in calendar {cal_path.name}: ts={ts}")
                by_day[dks].append((ts, str(ev["ccy"]).upper(), int(ev.get("blackout_sec", 300))))
        return by_day
    raise ValueError(f"Unsupported calendar schema in {cal_path}")


def asset_currencies(asset: str) -> tuple[str, ...]:
    u = str(asset).upper()
    if any(tok in u for tok in ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "XAU", "BTC")):
        return ("USD",)
    if any(tok in u for tok in ("GER40", "DE40", "DAX")):
        return ("EUR",)
    if any(tok in u for tok in ("UK100", "FTSE")):
        return ("GBP",)
    if len(u) >= 6:
        return (u[:3], u[3:6])
    return ("USD",)


def directional_factor_deltas(asset: str, side: int) -> tuple[float, float, float, float, float, float]:
    """Return unit-risk directional factor weights `(uL, uS, jL, jS, iL, iS)` matching `Naqex_PropGuard.mqh`."""
    u = str(asset).upper()
    is_buy = int(side) > 0
    u_l = u_s = j_l = j_s = i_l = i_s = 0.0
    if any(tok in u for tok in ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX")):
        if is_buy:
            i_l = 1.0
        else:
            i_s = 1.0
        return u_l, u_s, j_l, j_s, i_l, i_s
    pos_usd = u.find("USD")
    if pos_usd == 0:
        if is_buy:
            u_l = 1.0
        else:
            u_s = 1.0
    elif pos_usd >= 3:
        if is_buy:
            u_s = 1.0
        else:
            u_l = 1.0
    pos_jpy = u.find("JPY")
    if pos_jpy == 0:
        if is_buy:
            j_l = 1.0
        else:
            j_s = 1.0
    elif pos_jpy >= 3:
        if is_buy:
            j_s = 1.0
        else:
            j_l = 1.0
    return u_l, u_s, j_l, j_s, i_l, i_s


def derive_causal_cluster_a_spread_cap(
    sess_a_spreads: np.ndarray | list[float],
    entry_a_spreads: np.ndarray | list[float],
    *,
    min_floor_pts: float = 5.0,
) -> float:
    sa = np.asarray(sess_a_spreads, dtype=np.float64)
    ea = np.asarray(entry_a_spreads, dtype=np.float64)
    sess_p999 = float(np.percentile(sa, 99.9)) if len(sa) > 0 else 0.0
    ent_p999 = float(np.percentile(ea, 99.9)) if len(ea) > 0 else 0.0
    raw = max(sess_p999, 1.10 * ent_p999)
    return float(max(min_floor_pts, math.ceil(raw / 5.0) * 5.0))


def calibrate_m1_spread_guard(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    m1_cache_dir: Path = DEFAULT_M1_CACHE_DIR,
    engines: tuple[str, ...] = CORE7_IDS,
) -> dict[str, Any]:
    """Causal Cluster-A (2018-2020) M1 SpreadGuard calibration matching `flashcrash_pareto_study.py`."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {
            "available": False,
            "reason": "pyarrow_not_installed",
            "calibrated_dev_caps_a": {},
            "entry_spread_pts": {},
        }

    missing = [
        str(m1_cache_dir / sub / f"{sym}-M1-BIDASK-{yr}.parquet")
        for sym, (sub, _) in M1_SPREAD_SPECS.items()
        for yr in range(2018, 2025)
        if not (m1_cache_dir / sub / f"{sym}-M1-BIDASK-{yr}.parquet").is_file()
    ]
    if missing:
        return {
            "available": False,
            "reason": "m1_parquet_cache_incomplete",
            "missing_count": len(missing),
            "calibrated_dev_caps_a": {},
            "entry_spread_pts": {},
        }

    entries_by_sym: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for eng in engines:
        for dk, (row, stamps, _marks) in tapes.get(eng, {}).items():
            sym = str(row.get("asset") or ENGINE_ASSET_MAP[eng])
            ent_min = int(stamps[0]) // 60 if len(stamps) > 0 else int(row["entry"]) // 60
            entries_by_sym[sym].append((ent_min, dk, eng))

    calibrated_dev_caps_a: dict[str, float] = {}
    entry_spread_pts: dict[tuple[str, str], float] = {}

    for sym, (sub, div_pts) in M1_SPREAD_SPECS.items():
        sym_entries = entries_by_sym.get(sym, [])
        entry_hours_a = sorted({(em // 60) % 24 for em, dk, _ in sym_entries if dk < CLUSTER_A_CUTOFF_DAY})
        mins_a_parts: list[np.ndarray] = []
        spr_a_parts: list[np.ndarray] = []
        mins_b_parts: list[np.ndarray] = []
        spr_b_parts: list[np.ndarray] = []
        sess_a_parts: list[np.ndarray] = []

        for yr in range(2018, 2025):
            pq_path = m1_cache_dir / sub / f"{sym}-M1-BIDASK-{yr}.parquet"
            tbl = pq.read_table(pq_path, columns=["minute", "bo", "ao"])
            mn = tbl["minute"].to_numpy()
            if len(mn) > 0 and int(mn.max()) * 60 >= HOLDOUT_STOP_TS:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION in {pq_path.name}: max_min={int(mn.max())}")
            sp = (tbl["ao"].to_numpy() - tbl["bo"].to_numpy()).astype(np.float64) * div_pts
            hr = (mn // 60) % 24
            act = hr < 21
            if yr <= CLUSTER_A_MAX_YEAR:
                mins_a_parts.append(mn)
                spr_a_parts.append(sp)
                sess_mask = np.isin(hr, entry_hours_a) if entry_hours_a else act
                sess_a_parts.append(sp[sess_mask])
            else:
                mins_b_parts.append(mn)
                spr_b_parts.append(sp)

        mn_a = np.concatenate(mins_a_parts) if mins_a_parts else np.empty(0, dtype=np.int64)
        sp_a_raw = np.concatenate(spr_a_parts) if spr_a_parts else np.empty(0, dtype=np.float64)
        mn_all = np.concatenate(mins_a_parts + mins_b_parts)
        sp_all = np.concatenate(spr_a_parts + spr_b_parts)
        sess_a = np.concatenate(sess_a_parts) if sess_a_parts else np.empty(0, dtype=np.float64)

        ent_vals_a: list[float] = []
        for ent_m, dk, eng in sym_entries:
            arr_m, arr_s = (mn_a, sp_a_raw) if dk < CLUSTER_A_CUTOFF_DAY else (mn_all, sp_all)
            idx = int(np.searchsorted(arr_m, ent_m))
            if idx < len(arr_m) and int(arr_m[idx]) == ent_m:
                val = float(arr_s[idx])
            elif idx > 0:
                val = float(arr_s[idx - 1])
            else:
                continue
            entry_spread_pts[(eng, dk)] = val
            if dk < CLUSTER_A_CUTOFF_DAY:
                ent_vals_a.append(val)

        calibrated_dev_caps_a[sym] = derive_causal_cluster_a_spread_cap(sess_a, ent_vals_a)

    return {
        "available": True,
        "holdout_rows_analysed": 0,
        "calibration_rule": SPREAD_GUARD_CALIBRATION_RULE,
        "calibrated_dev_caps_a": calibrated_dev_caps_a,
        "entry_spread_pts": entry_spread_pts,
    }


def estimate_base_friction_usd_per_lot(row: dict[str, Any]) -> float:
    stop_cost = float(row.get("stop_risk_with_cost_usd") or 0.0)
    if stop_cost <= 0.0:
        return 0.0
    init_r = row.get("initial_risk_usd")
    if init_r is not None and float(init_r) > 0.0:
        diff = max(0.0, stop_cost - float(init_r))
        if diff > 0.0:
            return diff
    ep = row.get("entry_price")
    slp = row.get("sl_price") or row.get("stop")
    asset = str(row.get("asset") or "")
    if ep is not None and slp is not None and float(ep) > 0.0 and float(slp) > 0.0:
        dist = abs(float(ep) - float(slp))
        if asset in ("EURUSD", "GBPUSD", "AUDUSD"):
            raw_sl = dist * 100_000.0
        elif asset in ("USDJPY", "EURJPY", "GBPJPY"):
            usd_jpy = float(ep) if asset == "USDJPY" else 135.0
            raw_sl = dist * 100_000.0 / max(80.0, usd_jpy)
        elif asset in ("US100", "US500", "GER40"):
            raw_sl = dist * 1.0
        elif asset == "XAUUSD":
            raw_sl = dist * 100.0
        else:
            raw_sl = stop_cost * 0.96
        if 0.50 * stop_cost <= raw_sl < stop_cost:
            return max(stop_cost - raw_sl, 0.03 * stop_cost)
    return 0.035 * stop_cost


def apply_cost_stress_to_tapes(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    cost_mult: float,
    *,
    engines: tuple[str, ...] = CORE7_IDS,
) -> dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]]:
    if abs(cost_mult - 1.0) < 1e-9:
        return {eng: tapes[eng] for eng in engines if eng in tapes}
    delta = float(cost_mult) - 1.0
    out: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    for eng in engines:
        if eng not in tapes:
            continue
        new_dm: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
        for dk, (row, stamps, marks) in tapes[eng].items():
            extra = delta * estimate_base_friction_usd_per_lot(row)
            new_row = {
                **row,
                "net_usd_per_lot": float(row["net_usd_per_lot"]) - extra,
                "stop_risk_with_cost_usd": float(row["stop_risk_with_cost_usd"]) + extra,
            }
            new_marks = np.asarray(marks, dtype=np.float64) - extra
            new_dm[dk] = (new_row, stamps, new_marks)
        out[eng] = new_dm
    return out


def apply_shield_b2_b3_guards(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    red_news_cal: dict[str, list[tuple[int, str, int]]],
    news_pad_sec: int = 600,
    spread_caps_pts: dict[str, float] | None = None,
    entry_spread_pts: dict[tuple[str, str], float] | None = None,
    engines: tuple[str, ...] = CORE7_IDS,
) -> tuple[dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]], dict[str, int]]:
    """Apply Shield B2 SpreadGuard + Shield B3 6-CCY +-10m (BoJ +-60m) red-news filter causally."""
    if news_pad_sec < 135:
        raise ValueError(f"V103_NEWS_GUARD_VIOLATION: news_pad_sec={news_pad_sec} < 135s hard ban")
    out: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    stats = {
        "total_in": 0,
        "kept_untouched": 0,
        "blocked_spread": 0,
        "blocked_news_entry": 0,
        "flattened_pre_news": 0,
    }
    for eng in engines:
        dm = tapes.get(eng, {})
        eng_out: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
        for dk, (row, stamps, marks) in dm.items():
            stats["total_in"] += 1
            asset = str(row.get("asset") or ENGINE_ASSET_MAP.get(eng, "USDJPY"))

            if spread_caps_pts is not None and entry_spread_pts is not None:
                cap_pts = float(spread_caps_pts.get(asset, 1e9))
                obs_pts = entry_spread_pts.get((eng, dk))
                if obs_pts is not None and obs_pts > cap_pts:
                    stats["blocked_spread"] += 1
                    continue

            ccys = set(asset_currencies(asset))
            day_ev = [
                (ts, max(int(news_pad_sec), int(ev_bsec))) for ts, c, ev_bsec in red_news_cal.get(dk, []) if c in ccys
            ]
            if not day_ev:
                eng_out[dk] = (row, stamps, marks)
                stats["kept_untouched"] += 1
                continue

            t_ent = int(stamps[0])
            t_ext = int(row["exit"])
            if any(abs(t_ent - tn) <= eff_pad for tn, eff_pad in day_ev):
                stats["blocked_news_entry"] += 1
                continue

            cut_events = [tn - eff_pad for tn, eff_pad in day_ev if t_ent < (tn - eff_pad) < t_ext]
            if not cut_events:
                eng_out[dk] = (row, stamps, marks)
                stats["kept_untouched"] += 1
                continue

            t_cut = min(cut_events)
            k = int(stamps.searchsorted(t_cut, side="right")) - 1
            if k < 0:
                stats["blocked_news_entry"] += 1
                continue

            new_stamps = stamps[: k + 1].copy()
            new_marks = marks[: k + 1].copy()
            term_pnl = float(new_marks[-1, 3])
            new_marks[-1, 3] = term_pnl
            new_row = {
                **row,
                "exit": int(new_stamps[-1]) + 60,
                "at_open": False,
                "reason": "NEWS_PRE_FLATTEN",
                "net_usd_per_lot": term_pnl,
                "net_R": float(term_pnl / max(1e-6, float(row["stop_risk_with_cost_usd"]))),
            }
            eng_out[dk] = (new_row, new_stamps, new_marks)
            stats["flattened_pre_news"] += 1
        out[eng] = eng_out
    return out, stats


# ---------------------------------------------------------------------------
# 3. Exact Per-SKU Margin & Intraday `v103.mq5` M1 Replay Engine
# ---------------------------------------------------------------------------


def margin_per_lot_for_leverage(
    asset: str,
    entry_price: float,
    *,
    leverage_fx: float,
    leverage_indices: float,
) -> tuple[float, float, float, float, float]:
    """Return `(margin_per_lot_usd, vol_min, vol_step, vol_max, comm_usd_per_lot)` for exact SKU leverage."""
    if asset in ("US100", "US100.cash", "US500", "US500.cash"):
        mgn = float(entry_price) / max(1.0, float(leverage_indices))
        return mgn, 0.01, 0.01, 1000.0, 0.0
    if asset == "XAUUSD":
        mgn = float(entry_price) * 100.0 / max(1.0, float(leverage_indices))
        return mgn, 0.01, 0.01, 100.0, 5.20
    lev = max(1.0, float(leverage_fx))
    if asset in ("USDJPY", "USDCAD", "USDCHF"):
        notional = 100_000.0
    elif asset.startswith("EUR") and not asset.endswith("USD"):
        notional = 100_000.0 * 1.15
    elif asset.startswith("GBP") and not asset.endswith("USD"):
        notional = 100_000.0 * 1.35
    else:
        notional = 100_000.0 * float(entry_price)
    return notional / lev, 0.01, 0.01, 50.0, 5.0


def floor_lot_step(raw_lots: float, *, step: float = 0.01, vol_min: float = 0.01, vol_max: float = 1000.0) -> float:
    if raw_lots <= 0.0 or not math.isfinite(raw_lots):
        return 0.0
    capped = min(float(raw_lots), float(vol_max))
    steps = math.floor(capped / step + 1e-9)
    lot = round(steps * step, 8)
    return 0.0 if lot < vol_min - 1e-12 else lot


def prealign_days_for_tapes(
    ext_days: list[str],
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    engines: tuple[str, ...] = CORE7_IDS,
    base_risks: dict[str, float] = CORE7_BASE_RISK_FRAC,
) -> list[dict[str, Any]]:
    """Pre-align 1-lot M1 mark matrices ONCE per tape configuration."""
    pre_days: list[dict[str, Any]] = []
    for day_idx, dk in enumerate(ext_days):
        cands = [(eng, tapes[eng][dk]) for eng in engines if eng in tapes and dk in tapes[eng]]
        if not cands:
            continue
        cands.sort(key=lambda kv: (int(kv[1][0]["entry"]), kv[0]))
        k = len(cands)
        min_e = min(int(stamps[0]) for _, (_, stamps, _) in cands)
        max_x = max(int(stamps[-1]) for _, (_, stamps, _) in cands)
        n_tl = int((max_x - min_e) // 60) + 1
        marks_1lot = np.zeros((k, n_tl, 4), dtype=np.float64)

        meta_list: list[dict[str, Any]] = []
        for i, (eng, (row, stamps, marks)) in enumerate(cands):
            asset = str(row.get("asset") or ENGINE_ASSET_MAP.get(eng, "USDJPY"))
            side = int(row.get("side", 1))
            entry_ts = int(stamps[0])
            at_open = bool(row.get("at_open", False))
            release_ts = int(stamps[-1]) + (0 if at_open else 60)
            net_1lot = float(row["net_usd_per_lot"])
            stop_cost = float(row["stop_risk_with_cost_usd"])
            ep = float(row["entry_price"])

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

            meta_list.append(
                {
                    "eng": eng,
                    "asset": asset,
                    "side": side,
                    "factors": directional_factor_deltas(asset, side),
                    "base_r": float(base_risks[eng]),
                    "entry_ts": entry_ts,
                    "release_ts": release_ts,
                    "stop_cost": stop_cost,
                    "net_1lot": net_1lot,
                    "entry_price": ep,
                    "stamps": stamps,
                    "marks": marks,
                }
            )

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

        pre_days.append(
            {
                "day_idx": day_idx,
                "day": dk,
                "year": int(dk[:4]),
                "cands": meta_list,
                "marks_flat": np.ascontiguousarray(marks_1lot.reshape(k, n_tl * 4)),
                "open_fl": open_fl,
            }
        )
    return pre_days


def replay_v103_regime_stage(
    ext_days: list[str],
    pre_days: list[dict[str, Any]],
    *,
    capital_usd: float,
    regime_mult: float,
    base_phase_mult: float,
    symcap_pct: float,
    usd_cluster_cap_pct: float,
    jpy_cluster_cap_pct: float,
    idx_cluster_cap_pct: float,
    total_open_cap_pct: float,
    kill_daily_dd_pct: float,
    leverage_fx: float = 100.0,
    leverage_indices: float = 50.0,
    enable_daily_headroom_taper: bool = True,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    """Exact M1 minute-by-minute replay matching `Naqex_Master_Prop7E_v103.mq5`.

    Enforces:
      - Hard ceiling `EffectiveTotalOpenRiskCapPct() <= 3.00%` (`L142-150`, `L1083`).
      - Intraday `dailyHeadroom < 2.0%` throttle/taper (`L519-526`) + intraday `kill_daily_dd` block (`L996`).
      - Per-symbol cap + Shield B1 directional factor cluster caps (`USD/JPY/IDX`) + Shield A total cap.
      - Exact per-SKU `0.85 * freeMargin` lot downsizing (`L821-827`) matching `v103.mq5`.
      - Post-rounding `actual_risk <= effective_headroom + 1e-6` check (`L839-844`).
    """
    eff_tot_cap_pct = effective_total_open_risk_cap_pct(total_open_cap_pct, HARD_TOTAL_OPEN_CEILING_PCT)
    n_days = len(ext_days)
    nets = np.zeros(n_days, dtype=np.float64)
    dds = np.zeros(n_days, dtype=np.float64)
    flg = np.zeros(n_days, dtype=np.int8)

    initial = float(capital_usd)
    balance = initial
    peak_eq = initial
    max_peak_dd = 0.0
    max_daily_dd = 0.0
    symcap = float(symcap_pct) / 100.0
    tot_cap = eff_tot_cap_pct / 100.0
    usd_cap = float(usd_cluster_cap_pct) / 100.0
    jpy_cap = float(jpy_cluster_cap_pct) / 100.0
    idx_cap = float(idx_cluster_cap_pct) / 100.0
    kill_daily_frac = float(kill_daily_dd_pct) / 100.0

    sized_cnt = 0
    tapered_entries = 0
    intraday_killed_entries = 0
    margin_downsized = 0
    margin_rej = 0
    peak_simultaneous_open_risk_frac = 0.0
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

    for pd_row in pre_days:
        cands = pd_row["cands"]
        k = len(cands)
        open_fl = pd_row["open_fl"]
        lots = np.zeros(k, dtype=np.float64)
        actual_risks = [0.0] * k
        margins = [0.0] * k
        any_sized = False

        for j in range(k):
            cj = cands[j]
            st_j = cj["entry_ts"]
            asset_j = cj["asset"]
            du_l, du_s, dj_l, dj_s, di_l, di_s = cj["factors"]

            # Intraday PnL at entry minute `st_j` (strictly causal: realized + M1 floating)
            fl_sum = 0.0
            used_m = 0.0
            open_sym_r = 0.0
            open_tot_r = 0.0
            u_l = u_s = j_l = j_s = i_l = i_s = 0.0
            for i in range(j):
                if lots[i] > 0.0:
                    fl_sum += lots[i] * open_fl[i, j]
                    if st_j < cands[i]["release_ts"]:
                        used_m += margins[i]
                        ri = actual_risks[i]
                        open_tot_r += ri
                        if cands[i]["asset"] == asset_j:
                            open_sym_r += ri
                        fu_l, fu_s, fj_l, fj_s, fi_l, fi_s = cands[i]["factors"]
                        u_l += fu_l * ri
                        u_s += fu_s * ri
                        j_l += fj_l * ri
                        j_s += fj_s * ri
                        i_l += fi_l * ri
                        i_s += fi_s * ri

            # Exact `v103.mq5 L519-526` intraday `dailyHeadroom < 2.0%` throttle/taper + `L996` daily kill
            eff_mult = float(regime_mult)
            if enable_daily_headroom_taper and any_sized:
                intraday_daily_dd = max(0.0, -fl_sum / initial)
                daily_headroom = max(0.0, kill_daily_frac - intraday_daily_dd)
                if daily_headroom <= 1e-12:
                    intraday_killed_entries += 1
                    continue
                if daily_headroom < 0.02:
                    daily_scale = max(0.25, daily_headroom / 0.02)
                    tapered_m = min(eff_mult, float(base_phase_mult) * daily_scale)
                    if tapered_m < eff_mult - 1e-12:
                        eff_mult = tapered_m
                        tapered_entries += 1

            req_r = cj["base_r"] * eff_mult
            rem_sym = max(0.0, symcap - open_sym_r)
            rem_fac_tot = max(0.0, tot_cap - open_tot_r)
            if du_l > 0.0:
                rem_fac_tot = min(rem_fac_tot, max(0.0, usd_cap - u_l))
            if du_s > 0.0:
                rem_fac_tot = min(rem_fac_tot, max(0.0, usd_cap - u_s))
            if dj_l > 0.0:
                rem_fac_tot = min(rem_fac_tot, max(0.0, jpy_cap - j_l))
            if dj_s > 0.0:
                rem_fac_tot = min(rem_fac_tot, max(0.0, jpy_cap - j_s))
            if di_l > 0.0:
                rem_fac_tot = min(rem_fac_tot, max(0.0, idx_cap - i_l))
            if di_s > 0.0:
                rem_fac_tot = min(rem_fac_tot, max(0.0, idx_cap - i_s))

            eff_headroom = min(rem_sym, rem_fac_tot)
            er = min(req_r, eff_headroom)
            if er <= 1e-4:  # Matches `v103.mq5 L775`: `allowedRiskPct <= 0.01%`
                continue

            mgn_1, vmin, vstep, vmax, _comm_1 = margin_per_lot_for_leverage(
                asset_j, cj["entry_price"], leverage_fx=leverage_fx, leverage_indices=leverage_indices
            )
            budget = initial * er
            lot = floor_lot_step(budget / cj["stop_cost"], step=vstep, vol_min=vmin, vol_max=vmax)
            if lot < vmin:
                continue

            # Matches `v103.mq5 L814-827`: 85% free-margin downsize fail-closed
            free_margin = initial + fl_sum - used_m
            if free_margin <= 0.0 or mgn_1 <= 0.0:
                margin_rej += 1
                continue
            req_margin = lot * mgn_1
            max_allow_m = free_margin * 0.85
            if req_margin > max_allow_m:
                lot = floor_lot_step(lot * (max_allow_m / req_margin), step=vstep, vol_min=vmin, vol_max=vmax)
                if lot < vmin:
                    margin_rej += 1
                    continue
                margin_downsized += 1

            act_r = (lot * cj["stop_cost"]) / initial
            if act_r > eff_headroom + 1e-6:  # Matches `v103.mq5 L840`
                continue

            lots[j] = lot
            actual_risks[j] = act_r
            margins[j] = lot * mgn_1
            any_sized = True
            sized_cnt += 1

            cur_open_r = open_tot_r + act_r
            if cur_open_r > peak_simultaneous_open_risk_frac:
                peak_simultaneous_open_risk_frac = cur_open_r

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

        comb = lots @ pd_row["marks_flat"]
        day_min_rel = float(comb.min())
        day_net = float(comb[-1])
        day_dd = max(0.0, -day_min_rel)

        eq_pts = balance + comb
        if eq_pts.max() > peak_eq:
            run_peaks = np.maximum(peak_eq, np.maximum.accumulate(eq_pts))
            day_peak_dd = float(np.max(run_peaks - eq_pts))
            peak_eq = float(run_peaks[-1])
        else:
            day_peak_dd = float(peak_eq - eq_pts.min())
        if day_peak_dd > max_peak_dd:
            max_peak_dd = day_peak_dd
        if day_dd > max_daily_dd:
            max_daily_dd = day_dd

        d_i = pd_row["day_idx"]
        nets[d_i] = day_net
        dds[d_i] = day_dd
        flg[d_i] = 1
        balance += day_net
        if pd_row["year"] <= CLUSTER_A_MAX_YEAR:
            net_a += day_net
        else:
            net_b += day_net

    yrs_span = max(1.0, float(len({d[:4] for d in ext_days})))
    ann_pct = 100.0 * ((balance - initial) / yrs_span) / initial
    peak_dd_pct = 100.0 * max_peak_dd / initial
    calmar = (ann_pct / peak_dd_pct) if peak_dd_pct > 1e-9 else 0.0
    daily_ret = nets / initial
    std_d = float(np.std(daily_ret, ddof=1)) if n_days > 1 else 0.0
    sharpe = (float(np.mean(daily_ret)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0
    pf = (wins_sum / loss_sum) if loss_sum > 1e-9 else 0.0
    wr = 100.0 * wins_cnt / max(1, wins_cnt + loss_cnt)
    rr = ((wins_sum / wins_cnt) / (loss_sum / loss_cnt)) if (wins_cnt > 0 and loss_cnt > 0) else 0.0
    ev_r = (r_sum / r_cnt) if r_cnt > 0 else 0.0
    ev_usd = (balance - initial) / max(1, sized_cnt)

    metrics = {
        "capital_usd": initial,
        "regime_mult": round(float(regime_mult), 4),
        "base_phase_mult": round(float(base_phase_mult), 4),
        "sized_trades": sized_cnt,
        "tapered_entries": tapered_entries,
        "intraday_killed_entries": intraday_killed_entries,
        "margin_downsized": margin_downsized,
        "margin_rejected": margin_rej,
        "peak_open_risk_pct": round(100.0 * peak_simultaneous_open_risk_frac, 3),
        "max_daily_dd_pct": round(100.0 * max_daily_dd / initial, 3),
        "peak_dd_pct": round(peak_dd_pct, 3),
        "ann_pct": round(ann_pct, 3),
        "ann_cluster_a_pct": round(100.0 * (net_a / 3.0) / initial, 3),
        "ann_cluster_b_pct": round(100.0 * (net_b / 4.0) / initial, 3),
        "calmar": round(calmar, 3),
        "sharpe": round(sharpe, 3),
        "winrate_pct": round(wr, 2),
        "avg_rr": round(rr, 3),
        "ev_per_trade_r": round(ev_r, 4),
        "ev_usd_per_trade": round(ev_usd, 2),
        "profit_factor": round(pf, 3),
        "max_loss_streak_trades": max_loss,
    }
    return metrics, nets, dds, flg


# ---------------------------------------------------------------------------
# 4. Numba Full-Lifecycle Simulator (Exact v1.03 Mode 1 FTMO vs Mode 0 The5ers)
# ---------------------------------------------------------------------------


def make_block_bootstrap_indices(
    n_obs: int,
    *,
    horizon: int = DEFAULT_HORIZON_DAYS,
    n_paths: int = DEFAULT_N_PATHS,
    block_len: int = BLOCK_LEN,
    seed: int = DEFAULT_SEED,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_blocks = (horizon + block_len - 1) // block_len
    starts = rng.integers(0, n_obs, size=(n_paths, n_blocks))
    offs = np.arange(block_len, dtype=np.int64)[None, None, :]
    idxs = (starts[:, :, None] + offs).reshape(n_paths, n_blocks * block_len)[:, :horizon] % n_obs
    return idxs.astype(np.int32)


@njit(cache=False)
def _simulate_v103_prop_lifecycle_numba(
    idx_matrix: np.ndarray,
    # P1 tapes: normal, lock, amber, red
    n_p1_n: np.ndarray,
    d_p1_n: np.ndarray,
    f_p1_n: np.ndarray,
    n_p1_l: np.ndarray,
    d_p1_l: np.ndarray,
    f_p1_l: np.ndarray,
    n_p1_a: np.ndarray,
    d_p1_a: np.ndarray,
    f_p1_a: np.ndarray,
    n_p1_r: np.ndarray,
    d_p1_r: np.ndarray,
    f_p1_r: np.ndarray,
    # P2 tapes: normal, lock, amber, red
    n_p2_n: np.ndarray,
    d_p2_n: np.ndarray,
    f_p2_n: np.ndarray,
    n_p2_l: np.ndarray,
    d_p2_l: np.ndarray,
    f_p2_l: np.ndarray,
    n_p2_a: np.ndarray,
    d_p2_a: np.ndarray,
    f_p2_a: np.ndarray,
    n_p2_r: np.ndarray,
    d_p2_r: np.ndarray,
    f_p2_r: np.ndarray,
    # Funded tapes: normal, amber, red (SEPARATE Funded `.set`!)
    n_fn_n: np.ndarray,
    d_fn_n: np.ndarray,
    f_fn_n: np.ndarray,
    n_fn_a: np.ndarray,
    d_fn_a: np.ndarray,
    f_fn_a: np.ndarray,
    n_fn_r: np.ndarray,
    d_fn_r: np.ndarray,
    f_fn_r: np.ndarray,
    # Contract rules
    cap: float,
    fee_day0_usd: float,
    fee_regular_usd: float,
    card_fx_fee_pct: float,
    withdrawal_fee_pct: float,
    ext_cash_refund_frac: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    static_lim: float,
    daily_reset_mode: int,  # 1 = FTMO (anchor/InitialBalance), 0 = The5ers (max(bal,eq)/anchor)
    min_days: int,
    min_prof_days: int,
    prof_day_thresh_frac: float,
    profit_split: float,
    payout_cycle_days: int,
    min_payout_usd: float,
    # Separate Eval vs Funded `.set` knobs
    p1_lock_trigger: float,
    p2_lock_trigger: float,
    p1_lock_frac: float,
    p2_lock_frac: float,
    eval_amber_dd: float,
    eval_amber_mult: float,
    eval_red_dd: float,
    eval_red_mult: float,
    eval_p1_kill_daily: float,
    eval_p2_kill_daily: float,
    eval_p1_kill_static: float,
    eval_p2_kill_static: float,
    eval_sizing_mode: int,
    fn_amber_dd: float,
    fn_red_dd: float,
    fn_kill_daily: float,
    fn_kill_static: float,
    # Simulation controls
    discount_rate_annual: float,
    max_retries: int,
    balance_compounding: bool,
):
    """Exact `Naqex_Master_Prop7E_v103.mq5` 2-Step Eval + Funded lifecycle Numba kernel.

    Tracks:
      - P1-only pass day (`p1_pass_day`) AND full P1+P2 pass day (`eval_pass_day`).
      - First-ticket fail day (`eval_fail_day`), stage of fail (`p1_fail` vs `p2_fail`),
        `bot_auto_kill_any`, `firm_hard_breach_any`, `static_halt_any`.
      - Best-Day Share (`max_day_profit / phase_target`) for P1 & P2 on first passing ticket.
      - Funded 12m breach, Wilson inputs, dry months, first payout day (`pay1_day`).
      - Multi-ticket bankroll ruin (`wiped_all_tickets`) when `max_retries > 0` (`3` -> 4 tickets, `4` -> 5 tickets).
    """
    n_paths, horizon = idx_matrix.shape
    eff_fee_day0 = fee_day0_usd * (1.0 + card_fx_fee_pct)
    eff_fee_reg = fee_regular_usd * (1.0 + card_fx_fee_pct)
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    static_floor = cap * (1.0 - static_lim)
    inv_df = np.empty(horizon + 2, dtype=np.float64)
    for k_d in range(horizon + 2):
        inv_df[k_d] = (1.0 + discount_rate_annual) ** (-k_d / 252.0)

    p1_pass_day = np.full(n_paths, -1, dtype=np.int32)
    eval_pass_day = np.full(n_paths, -1, dtype=np.int32)
    eval_fail_day = np.full(n_paths, -1, dtype=np.int32)
    eval_fail_stage = np.zeros(n_paths, dtype=np.int8)  # 1=P1, 2=P2
    pay1_day = np.full(n_paths, -1, dtype=np.int32)
    funded_enter_day = np.full(n_paths, -1, dtype=np.int32)
    funded_breach_day = np.full(n_paths, -1, dtype=np.int32)
    bot_kill_any = np.zeros(n_paths, dtype=np.int8)
    firm_breach_any = np.zeros(n_paths, dtype=np.int8)
    static_halt_any = np.zeros(n_paths, dtype=np.int8)
    wiped_all_tickets = np.zeros(n_paths, dtype=np.int8)
    tickets_used = np.ones(n_paths, dtype=np.int32)

    p1_best_day_share = np.full(n_paths, -1.0, dtype=np.float64)
    p2_best_day_share = np.full(n_paths, -1.0, dtype=np.float64)

    npv_24m = np.zeros(n_paths, dtype=np.float64)
    cf_24m = np.zeros(n_paths, dtype=np.float64)
    fees_24m = np.zeros(n_paths, dtype=np.float64)
    funded_months_total = np.zeros(n_paths, dtype=np.int32)
    funded_months_dry = np.zeros(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1
        bal = cap
        tdays = 0
        pdays = 0
        cycle_d = 0
        refunded = False
        attempts = 1
        first_ticket = True
        cur_ticket_fee = fee_day0_usd
        max_day_gain = 0.0

        cum_npv = -eff_fee_day0
        cum_cf = -eff_fee_day0
        cum_fees = eff_fee_day0

        f_p1_pass = -1
        f_pass = -1
        f_fail = -1
        f_fail_st = 0
        f_pay1 = -1
        f_fn_in = -1
        f_fn_br = -1
        b_kill = 0
        f_br = 0
        s_halt = 0
        p1_bds = -1.0
        p2_bds = -1.0

        fn_m_days = 0
        fn_m_paid = 0
        tot_fm = 0
        dry_fm = 0
        rec_24 = False

        for d in range(horizon):
            if stage > 0:
                src = idx_matrix[b, d]
                eq_pct = (bal - cap) / cap
                static_dd_pct = max(0.0, -eq_pct)

                # Select exact phase + regime tape matching `v103.mq5 L467-517`
                reg_frac = 1.0
                if stage == 1:
                    if static_dd_pct >= eval_red_dd - 1e-12:
                        net_raw, dd_raw, flg = n_p1_r[src], d_p1_r[src], f_p1_r[src]
                        reg_frac = eval_red_mult
                    elif static_dd_pct >= eval_amber_dd - 1e-12:
                        net_raw, dd_raw, flg = n_p1_a[src], d_p1_a[src], f_p1_a[src]
                        reg_frac = eval_amber_mult
                    elif p1_lock_trigger > 0.0 and eq_pct >= p1_target * p1_lock_trigger - 1e-12:
                        net_raw, dd_raw, flg = n_p1_l[src], d_p1_l[src], f_p1_l[src]
                        reg_frac = p1_lock_frac
                    else:
                        net_raw, dd_raw, flg = n_p1_n[src], d_p1_n[src], f_p1_n[src]
                    ea_daily_stop = eval_p1_kill_daily
                    ea_static_stop = eval_p1_kill_static
                    cur_tgt = p1_target
                elif stage == 2:
                    if static_dd_pct >= eval_red_dd - 1e-12:
                        net_raw, dd_raw, flg = n_p2_r[src], d_p2_r[src], f_p2_r[src]
                        reg_frac = eval_red_mult
                    elif static_dd_pct >= eval_amber_dd - 1e-12:
                        net_raw, dd_raw, flg = n_p2_a[src], d_p2_a[src], f_p2_a[src]
                        reg_frac = eval_amber_mult
                    elif p2_lock_trigger > 0.0 and eq_pct >= p2_target * p2_lock_trigger - 1e-12:
                        net_raw, dd_raw, flg = n_p2_l[src], d_p2_l[src], f_p2_l[src]
                        reg_frac = p2_lock_frac
                    else:
                        net_raw, dd_raw, flg = n_p2_n[src], d_p2_n[src], f_p2_n[src]
                    ea_daily_stop = eval_p2_kill_daily
                    ea_static_stop = eval_p2_kill_static
                    cur_tgt = p2_target
                else:
                    if static_dd_pct >= fn_red_dd - 1e-12:
                        net_raw, dd_raw, flg = n_fn_r[src], d_fn_r[src], f_fn_r[src]
                    elif static_dd_pct >= fn_amber_dd - 1e-12:
                        net_raw, dd_raw, flg = n_fn_a[src], d_fn_a[src], f_fn_a[src]
                    else:
                        net_raw, dd_raw, flg = n_fn_n[src], d_fn_n[src], f_fn_n[src]
                    ea_daily_stop = fn_kill_daily
                    ea_static_stop = fn_kill_static
                    cur_tgt = 0.0

                # `v103.mq5 L793, L808` sizes lots on current ACCOUNT_BALANCE
                bal_scale = (bal / cap) if balance_compounding else 1.0

                # Exact `v103.mq5 L528-543` `InpSizingMode == 1`: `mult = min(mult, base * ddScale)`
                if stage < 3 and eval_sizing_mode == 1:
                    s_head = max(0.0, ea_static_stop - static_dd_pct)
                    b_scale = 1.0
                    if s_head < 0.035:
                        b_scale = min(b_scale, max(0.25, s_head / 0.035))
                    if cur_tgt > 0.0 and eq_pct > 0.0:
                        rem_t = max(0.0, cur_tgt - eq_pct)
                        frac_r = rem_t / cur_tgt
                        if frac_r < 0.35:
                            b_scale = min(b_scale, max(0.35, frac_r / 0.35))
                    if reg_frac > 1e-9 and b_scale < reg_frac:
                        bal_scale *= b_scale / reg_frac

                net = net_raw * bal_scale
                dd = dd_raw * bal_scale

                # Exact `v103.mq5 L971-973` daily DD floor & EA daily stop (Mode 1 FTMO vs Mode 0 The5ers)
                if daily_reset_mode == 1:
                    daily_floor = bal - cap * daily_lim
                    ea_daily_cut = cap * ea_daily_stop if ea_daily_stop > 0.0 else 1e18
                else:
                    # Positions flat at 17:00 NY -> g_dayAnchorEq == bal
                    daily_floor = bal * (1.0 - daily_lim)
                    ea_daily_cut = bal * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

                ea_static_floor = cap * (1.0 - ea_static_stop) if ea_static_stop > 0.0 else -1e18

                # Raw firm breach checked BEFORE EA stop clamp (conservative fail-closed invariant!)
                day_min = bal - dd
                d_hit = day_min < daily_floor - 1e-9
                m_hit = day_min < static_floor - 1e-9

                # Intraday EA daily kill (`L996`): clamps remaining loss with +0.20% execution slip cushion
                if (not d_hit) and (not m_hit) and (dd > ea_daily_cut):
                    b_kill = 1
                    dd_eff = min(dd, ea_daily_cut + cap * 0.0020)
                    net = min(net, -dd_eff)
                    day_min_eff = bal - dd_eff
                    d_hit = day_min_eff < daily_floor - 1e-9
                    m_hit = day_min_eff < static_floor - 1e-9

                # Intraday EA static kill (`L996`): triggers flatten at `ea_static_floor` (+0.20% slip)
                hit_static_kill = False
                if (not d_hit) and (not m_hit) and (bal - dd <= ea_static_floor + 1e-9):
                    b_kill = 1
                    s_halt = 1
                    hit_static_kill = True
                    # Flatten around static kill floor with 0.20% slippage
                    max_loss_to_kill = max(0.0, bal - ea_static_floor) + cap * 0.0020
                    dd_eff = min(dd, max_loss_to_kill)
                    net = min(net, -dd_eff)
                    day_min_eff = bal - dd_eff
                    d_hit = day_min_eff < daily_floor - 1e-9
                    m_hit = day_min_eff < static_floor - 1e-9

                # Also check if end-of-day balance fell <= `ea_static_floor`: in `v103.mq5 L996`,
                # `staticDdPct >= InpKillStaticDdPct` re-arms `g_autoKillActive` on every subsequent day
                # permanently halting the bot -> count honestly as dead/failed ticket (NEVER hide as Pending!).
                perm_static_freeze = False
                if (not d_hit) and (not m_hit):
                    next_bal = bal + net
                    if next_bal <= ea_static_floor + 1e-9 or hit_static_kill:
                        if next_bal <= ea_static_floor + 1e-9:
                            perm_static_freeze = True
                            s_halt = 1
                            b_kill = 1

                if d_hit or m_hit or perm_static_freeze:
                    if d_hit or m_hit:
                        f_br = 1
                    if first_ticket:
                        if stage < 3 and f_fail < 0:
                            f_fail = d + 1
                            f_fail_st = stage
                        elif stage == 3 and f_fn_br < 0:
                            f_fn_br = d + 1
                        first_ticket = False
                    if attempts <= max_retries:
                        attempts += 1
                        cur_ticket_fee = fee_regular_usd
                        cum_npv -= eff_fee_reg * inv_df[d]
                        cum_cf -= eff_fee_reg
                        cum_fees += eff_fee_reg
                        stage = 1
                        bal = cap
                        tdays = 0
                        pdays = 0
                        cycle_d = 0
                        max_day_gain = 0.0
                        refunded = False
                    else:
                        stage = 0
                        wiped_all_tickets[b] = 1
                else:
                    bal += net
                    if net > max_day_gain:
                        max_day_gain = net
                    if flg != 0:
                        tdays += 1
                    if prof_day_thresh_frac > 0.0 and net >= cap * prof_day_thresh_frac - 1e-9:
                        pdays += 1

                    if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days and pdays >= min_prof_days:
                        if first_ticket and f_p1_pass < 0:
                            f_p1_pass = d + 1
                            p1_bds = max_day_gain / (cap * p1_target)
                        stage = 2
                        bal = cap
                        tdays = 0
                        pdays = 0
                        max_day_gain = 0.0
                    elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days and pdays >= min_prof_days:
                        if first_ticket and p2_bds < 0.0:
                            p2_bds = max_day_gain / (cap * p2_target)
                        stage = 3
                        bal = cap
                        tdays = 0
                        pdays = 0
                        cycle_d = 0
                        max_day_gain = 0.0
                        if f_pass < 0:
                            f_pass = d + 1
                        if first_ticket and f_fn_in < 0:
                            f_fn_in = d + 1
                    elif stage == 3:
                        cycle_d += 1
                        fn_m_days += 1
                        if cycle_d >= payout_cycle_days:
                            prof = bal - cap
                            if prof > 1e-6:
                                gross_share = prof * profit_split
                                if gross_share >= min_payout_usd - 1e-9:
                                    net_in = gross_share * (1.0 - withdrawal_fee_pct)
                                    if not refunded and ext_cash_refund_frac > 0.0:
                                        net_in += cur_ticket_fee * ext_cash_refund_frac
                                        refunded = True
                                    cum_npv += net_in * inv_df[d + 1]
                                    cum_cf += net_in
                                    fn_m_paid = 1
                                    if f_pay1 < 0:
                                        f_pay1 = d + 1
                                    bal = cap
                            cycle_d = 0
                        if fn_m_days >= 21:
                            tot_fm += 1
                            if fn_m_paid == 0:
                                dry_fm += 1
                            fn_m_days = 0
                            fn_m_paid = 0

            if (not rec_24) and (d + 1 == 504):
                npv_24m[b] = cum_npv
                cf_24m[b] = cum_cf
                fees_24m[b] = cum_fees
                rec_24 = True

        if not rec_24:
            npv_24m[b] = cum_npv
            cf_24m[b] = cum_cf
            fees_24m[b] = cum_fees
        p1_pass_day[b] = f_p1_pass
        eval_pass_day[b] = f_pass
        eval_fail_day[b] = f_fail
        eval_fail_stage[b] = f_fail_st
        pay1_day[b] = f_pay1
        funded_enter_day[b] = f_fn_in
        funded_breach_day[b] = f_fn_br
        bot_kill_any[b] = b_kill
        firm_breach_any[b] = f_br
        static_halt_any[b] = s_halt
        tickets_used[b] = attempts
        p1_best_day_share[b] = p1_bds
        p2_best_day_share[b] = p2_bds
        funded_months_total[b] = tot_fm
        funded_months_dry[b] = dry_fm

    return (
        p1_pass_day,
        eval_pass_day,
        eval_fail_day,
        eval_fail_stage,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        static_halt_any,
        wiped_all_tickets,
        tickets_used,
        p1_best_day_share,
        p2_best_day_share,
        npv_24m,
        cf_24m,
        fees_24m,
        funded_months_total,
        funded_months_dry,
    )


def wilson_upper_95(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    z = 1.959963984540054
    p = k / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return min(1.0, (center + margin) / denom)


def summarize_lifecycle_mc(
    raw: tuple[np.ndarray, ...],
    *,
    fee_day0_usd: float,
    card_fx_fee_pct: float,
    usd_vnd_rate: float,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> dict[str, Any]:
    """Summarize Law-13/15 lifecycle outputs with strict `Pass + Fail + Pending == 100.00%`."""
    (
        p1_pass_day,
        eval_pass_day,
        eval_fail_day,
        eval_fail_stage,
        pay1_day,
        funded_enter_day,
        funded_breach_day,
        bot_kill_any,
        firm_breach_any,
        static_halt_any,
        wiped_all,
        tickets_used,
        p1_bds,
        p2_bds,
        npv_24m,
        cf_24m,
        fees_24m,
        fn_m_tot,
        fn_m_dry,
    ) = raw
    n = len(eval_pass_day)
    if n < 1:
        raise ValueError("INVALID_MC_PATHS: n_paths must be >= 1")
    eff_fee = float(fee_day0_usd) * (1.0 + float(card_fx_fee_pct))

    monthly: dict[str, dict[str, float]] = {}
    for m in (3, 6, 12, 24):
        cutoff = m * TRADING_DAYS_PER_MONTH
        passed = (eval_pass_day >= 0) & (eval_pass_day <= cutoff)
        failed = (~passed) & (eval_fail_day > 0) & (eval_fail_day <= cutoff)
        pending = (~passed) & (~failed)
        p_pct = 100.0 * float(np.sum(passed)) / n
        f_pct = 100.0 * float(np.sum(failed)) / n
        w_pct = 100.0 * float(np.sum(pending)) / n
        if abs((p_pct + f_pct + w_pct) - 100.0) >= 1e-6:
            raise ValueError(f"Monthly {m}m Pass+Fail+Pending != 100%: {p_pct + f_pct + w_pct}")
        monthly[f"{m}m"] = {
            "pass_pct": round(p_pct, 2),
            "fail_pct": round(f_pct, 2),
            "pending_pct": round(w_pct, 2),
            "sum_pct": round(p_pct + f_pct + w_pct, 2),
        }

    # P1-only pass time (conditional & unconditional capped 730d)
    p1_mask = p1_pass_day > 0
    cal_p1 = np.where(p1_mask, p1_pass_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    p1_uncond = np.minimum(cal_p1, 730.0)
    p1_med_cond = round(float(np.median(cal_p1[p1_mask])), 1) if np.any(p1_mask) else -1.0
    p1_med_uncond = round(float(np.median(p1_uncond)), 1)
    p1_pass_24m_pct = round(100.0 * float(np.sum(p1_mask & (p1_pass_day <= 504))) / n, 2)

    # Full P1+P2 pass time (conditional & unconditional capped 730d)
    pass_mask = eval_pass_day > 0
    cal_pass = np.where(pass_mask, eval_pass_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    pass_uncond = np.minimum(cal_pass, 730.0)
    pass_med_cond = round(float(np.median(cal_pass[pass_mask])), 1) if np.any(pass_mask) else -1.0
    pass_p25_cond = round(float(np.percentile(cal_pass[pass_mask], 25)), 1) if np.any(pass_mask) else -1.0
    pass_p75_cond = round(float(np.percentile(cal_pass[pass_mask], 75)), 1) if np.any(pass_mask) else -1.0
    pass_med_uncond = round(float(np.median(pass_uncond)), 1)

    # First payout timing
    paid_mask = pay1_day > 0
    cal_pay1 = np.where(paid_mask, pay1_day * CALENDAR_DAYS_PER_TRADING_DAY, 1e9)
    pay1_uncond = np.minimum(cal_pay1, 730.0)

    # Best-Day Share (`max_day_profit / phase_target`)
    p1_bds_valid = p1_bds[p1_bds >= 0.0]
    p2_bds_valid = p2_bds[p2_bds >= 0.0]
    both_bds_mask = (p1_bds >= 0.0) & (p2_bds >= 0.0)
    eval_max_bds = np.maximum(p1_bds[both_bds_mask], p2_bds[both_bds_mask]) if np.any(both_bds_mask) else np.empty(0)

    def _bds_stats(arr: np.ndarray) -> dict[str, float]:
        if len(arr) == 0:
            return {"median_pct": -1.0, "p90_pct": -1.0, "p95_pct": -1.0, "pct_le_40": 0.0, "pct_le_50": 0.0}
        return {
            "median_pct": round(100.0 * float(np.median(arr)), 2),
            "p90_pct": round(100.0 * float(np.percentile(arr, 90)), 2),
            "p95_pct": round(100.0 * float(np.percentile(arr, 95)), 2),
            "pct_le_40": round(100.0 * float(np.mean(arr <= 0.40 + 1e-9)), 2),
            "pct_le_50": round(100.0 * float(np.mean(arr <= 0.50 + 1e-9)), 2),
        }

    # Funded 12m breach + Wilson 95% upper bound
    fn_mask = funded_enter_day >= 0
    n_fn = int(np.sum(fn_mask))
    if n_fn > 0:
        fn_in = funded_enter_day[fn_mask]
        fn_br = funded_breach_day[fn_mask]
        br_12m = (fn_br > 0) & ((fn_br - fn_in) <= TRADING_DAYS_PER_YEAR)
        n_br_12m = int(np.sum(br_12m))
        fn_br_pct = 100.0 * n_br_12m / n_fn
        wilson_ub_pct = 100.0 * wilson_upper_95(n_br_12m, n_fn)
        n_cens = int(np.sum((fn_in + TRADING_DAYS_PER_YEAR) > horizon_days))
    else:
        n_br_12m = 0
        fn_br_pct = 0.0
        wilson_ub_pct = 100.0
        n_cens = 0

    tot_fm = int(np.sum(fn_m_tot))
    dry_fm = int(np.sum(fn_m_dry))
    dry_pct = (100.0 * dry_fm / tot_fm) if tot_fm > 0 else 100.0
    ev_npv24 = float(np.mean(npv_24m))
    med_npv24 = float(np.median(npv_24m))
    ev_cf24 = float(np.mean(cf_24m))
    fail_24_frac = monthly["24m"]["fail_pct"] / 100.0
    fail_p1_24m = 100.0 * float(np.sum((eval_fail_day > 0) & (eval_fail_day <= 504) & (eval_fail_stage == 1))) / n
    fail_p2_24m = 100.0 * float(np.sum((eval_fail_day > 0) & (eval_fail_day <= 504) & (eval_fail_stage == 2))) / n

    return {
        "model_tag": "DAILY_APPROX_V103_PARITY",
        "n_paths": n,
        "effective_fee_usd": round(eff_fee, 2),
        "effective_fee_vnd_tr": round(eff_fee * usd_vnd_rate / 1_000_000.0, 2),
        "monthly_pass_fail_pending": monthly,
        "pass_3m_pct": monthly["3m"]["pass_pct"],
        "pass_6m_pct": monthly["6m"]["pass_pct"],
        "pass_12m_pct": monthly["12m"]["pass_pct"],
        "pass_24m_pct": monthly["24m"]["pass_pct"],
        "fail_24m_pct": monthly["24m"]["fail_pct"],
        "fail_p1_24m_pct": round(fail_p1_24m, 2),
        "fail_p2_24m_pct": round(fail_p2_24m, 2),
        "pending_24m_pct": monthly["24m"]["pending_pct"],
        "p1_pass_24m_pct": p1_pass_24m_pct,
        "p1_med_pass_cal_days_cond": p1_med_cond,
        "p1_med_pass_cal_days_uncond": p1_med_uncond,
        "full_med_pass_cal_days_cond": pass_med_cond,
        "full_p25_pass_cal_days_cond": pass_p25_cond,
        "full_p75_pass_cal_days_cond": pass_p75_cond,
        "full_med_pass_cal_days_uncond": pass_med_uncond,
        "cond_med_pay1_cal_days": round(float(np.median(cal_pay1[paid_mask])), 1) if np.any(paid_mask) else -1.0,
        "uncond_med_pay1_cap730_days": round(float(np.median(pay1_uncond)), 1),
        "ev_npv_24m_usd": round(ev_npv24, 2),
        "ev_npv_24m_vnd_tr": round(ev_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "med_npv_24m_usd": round(med_npv24, 2),
        "med_npv_24m_vnd_tr": round(med_npv24 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_undisc_24m_usd": round(ev_cf24, 2),
        "ev_undisc_24m_vnd_tr": round(ev_cf24 * usd_vnd_rate / 1_000_000.0, 2),
        "ev_per_fee_npv24": round(ev_npv24 / max(1.0, eff_fee), 2),
        "p_npv24_le_0_pct": round(100.0 * float(np.mean(npv_24m <= 0.0)), 2),
        "funded_12m_breach_pct": round(fn_br_pct, 2),
        "funded_12m_wilson_ub_pct": round(wilson_ub_pct, 2),
        "funded_entered_count": n_fn,
        "funded_breach_12m_count": n_br_12m,
        "funded_censored_count": n_cens,
        "funded_dry_months_pct": round(dry_pct, 2),
        "bot_auto_kill_pct": round(100.0 * float(np.mean(bot_kill_any > 0)), 2),
        "firm_hard_breach_pct": round(100.0 * float(np.mean(firm_breach_any > 0)), 2),
        "static_kill_halt_pct": round(100.0 * float(np.mean(static_halt_any > 0)), 2),
        "wiped_all_tickets_pct": round(100.0 * float(np.mean(wiped_all > 0)), 2),
        "mean_tickets_used": round(float(np.mean(tickets_used)), 3),
        "iid_ruin_4_tickets_pct": round(100.0 * (fail_24_frac**4), 4),
        "iid_ruin_5_tickets_pct": round(100.0 * (fail_24_frac**5), 4),
        "best_day_share": {
            "p1": _bds_stats(p1_bds_valid),
            "p2": _bds_stats(p2_bds_valid),
            "eval_max": _bds_stats(eval_max_bds),
        },
        "mean_fees_24m_usd": round(float(np.mean(fees_24m)), 2),
    }


# ---------------------------------------------------------------------------
# 5. Pre-Registered `.set`-Only Sprint Candidate Grid (Immutable v1.03 EA)
# ---------------------------------------------------------------------------


def build_sprint_candidates() -> list[SprintCandidate]:
    """Pre-registered `.set`-only candidate grid on immutable `Naqex_Master_Prop7E_v103.mq5`.

    ALL Sprint candidates lock:
      - `eval_total_open_cap_pct <= 3.00%` (`1.25x` gap shock `<= 3.75% <= 4.50%`)
      - Funded strictly locked to `1.0x`, `Amber 3.5% / 0.65x`, `Red 6.0% / 0.40x`,
        `TotalOpenCap = 2.00% <= 2.25%`, `SymCap = 1.00%`, `KillDaily = 2.50%`, `KillStatic = 8.00%` (OPS-2 `<= 8.00%`)
      - Shield B2 `SpreadGuard` ON + Shield B3 `6-CCY +-10m` ON across ALL phases!
    """
    return [
        # Control 0: Official Shield C baseline (Funded 1.25x, exact `FLASHCRASH-PARETO-DEFENSE-V103` params)
        SprintCandidate(
            candidate_id="BASE_V103_SHIELD_C_FN125",
            group="Baseline",
            label="Official v1.03 Shield C (P1 4.0x L70 / P2 3.5x L70 / Fn 1.25x, SymCap 1.75%, KS 8.0/7.5%)",
            p1_mult=4.00,
            p2_mult=3.50,
            p1_lock_trigger=0.70,
            p1_lock_mult=2.50,
            p2_lock_trigger=0.70,
            p2_lock_mult=1.75,
            eval_symcap_pct=1.75,
            eval_usd_cluster_pct=2.25,
            eval_jpy_cluster_pct=2.00,
            eval_idx_cluster_pct=1.75,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.65,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.40,
            eval_p1_kill_daily_pct=3.50,
            eval_p2_kill_daily_pct=3.00,
            eval_p1_kill_static_pct=8.00,
            eval_p2_kill_static_pct=7.50,
            funded_mult=1.25,
            funded_symcap_pct=1.25,
            funded_usd_cluster_pct=1.75,
            funded_jpy_cluster_pct=1.50,
            funded_idx_cluster_pct=1.25,
            funded_total_open_cap_pct=2.25,
            funded_kill_static_pct=7.50,
        ),
        # Control 1: Same Eval as Official Shield C, Funded locked to 1.0x (original KS 8.0/7.5%)
        SprintCandidate(
            candidate_id="BASE_V103_SHIELD_C_FN1X",
            group="Baseline_Fn1x",
            label="v1.03 Shield C Eval (KS 8.0/7.5%) + Funded 1.0x Control",
            p1_mult=4.00,
            p2_mult=3.50,
            p1_lock_trigger=0.70,
            p1_lock_mult=2.50,
            p2_lock_trigger=0.70,
            p2_lock_mult=1.75,
            eval_symcap_pct=1.75,
            eval_usd_cluster_pct=2.25,
            eval_jpy_cluster_pct=2.00,
            eval_idx_cluster_pct=1.75,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.65,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.40,
            eval_p1_kill_daily_pct=3.50,
            eval_p2_kill_daily_pct=3.00,
            eval_p1_kill_static_pct=8.00,
            eval_p2_kill_static_pct=7.50,
            funded_kill_static_pct=7.50,
        ),
        # Tier 1 (Conservative Sprint, ~18%-24% fail): StaticKill unlocked to 9.50%, asymmetric downside brake
        SprintCandidate(
            candidate_id="SPR01_M35_SC175_S0_T",
            group="Sprint_T1",
            label="P1/P2 3.5x | SymCap 1.75% | Amber 3.5%/0.55 Red 6.0%/0.30 | DS 3.75% KS 9.50% | PL OFF",
            p1_mult=3.50,
            p2_mult=3.50,
            p1_lock_trigger=0.00,
            p1_lock_mult=3.50,
            p2_lock_trigger=0.00,
            p2_lock_mult=3.50,
            eval_symcap_pct=1.75,
            eval_usd_cluster_pct=2.25,
            eval_jpy_cluster_pct=2.00,
            eval_idx_cluster_pct=1.75,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.55,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.30,
            eval_p1_kill_daily_pct=3.75,
            eval_p2_kill_daily_pct=3.75,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
        SprintCandidate(
            candidate_id="SPR02_M40_SC200_S0_T",
            group="Sprint_T1",
            label="P1/P2 4.0x | SymCap 2.00% | Amber 3.5%/0.50 Red 6.0%/0.25 | DS 4.00% KS 9.50% | PL OFF",
            p1_mult=4.00,
            p2_mult=4.00,
            p1_lock_trigger=0.00,
            p1_lock_mult=4.00,
            p2_lock_trigger=0.00,
            p2_lock_mult=4.00,
            eval_symcap_pct=2.00,
            eval_usd_cluster_pct=2.50,
            eval_jpy_cluster_pct=2.25,
            eval_idx_cluster_pct=2.00,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.50,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.25,
            eval_p1_kill_daily_pct=4.00,
            eval_p2_kill_daily_pct=4.00,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
        SprintCandidate(
            candidate_id="SPR03_M40_SC225_S0_T",
            group="Sprint_T1",
            label="P1/P2 4.0x | SymCap 2.25% | Amber 3.5%/0.45 Red 6.0%/0.20 | DS 4.00% KS 9.50% | PL OFF",
            p1_mult=4.00,
            p2_mult=4.00,
            p1_lock_trigger=0.00,
            p1_lock_mult=4.00,
            p2_lock_trigger=0.00,
            p2_lock_mult=4.00,
            eval_symcap_pct=2.25,
            eval_usd_cluster_pct=2.75,
            eval_jpy_cluster_pct=2.50,
            eval_idx_cluster_pct=2.25,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.45,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.20,
            eval_p1_kill_daily_pct=4.00,
            eval_p2_kill_daily_pct=4.00,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
        # Tier 2 (Target 20%-30% Fail Budget Sweet Spot): Fast upside 4.5x-5.0x + smart downside brake / SizingMode=1
        SprintCandidate(
            candidate_id="SPR04_M45_SC225_S0_T",
            group="Sprint_T2",
            label="P1/P2 4.5x | SymCap 2.25% | Amber 3.5%/0.50 Red 6.0%/0.25 | DS 4.25% KS 9.50% | PL OFF",
            p1_mult=4.50,
            p2_mult=4.50,
            p1_lock_trigger=0.00,
            p1_lock_mult=4.50,
            p2_lock_trigger=0.00,
            p2_lock_mult=4.50,
            eval_symcap_pct=2.25,
            eval_usd_cluster_pct=2.75,
            eval_jpy_cluster_pct=2.50,
            eval_idx_cluster_pct=2.25,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.50,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.25,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
        SprintCandidate(
            candidate_id="SPR05_M45_SC225_S0_T2",
            group="Sprint_T2",
            label="P1/P2 4.5x | SymCap 2.25% | Amber 3.5%/0.40 Red 6.0%/0.20 | DS 4.25% KS 9.50% | PL OFF",
            p1_mult=4.50,
            p2_mult=4.50,
            p1_lock_trigger=0.00,
            p1_lock_mult=4.50,
            p2_lock_trigger=0.00,
            p2_lock_mult=4.50,
            eval_symcap_pct=2.25,
            eval_usd_cluster_pct=2.75,
            eval_jpy_cluster_pct=2.50,
            eval_idx_cluster_pct=2.25,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.40,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.20,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
        SprintCandidate(
            candidate_id="SPR06_M45_SC225_B1",
            group="Sprint_T2",
            label="P1/P2 4.5x | SymCap 2.25% | SizingMode=1 | Amber 4.5%/0.60 Red 7.0%/0.30 | DS 4.25% KS 9.50%",
            p1_mult=4.50,
            p2_mult=4.50,
            p1_lock_trigger=0.00,
            p1_lock_mult=4.50,
            p2_lock_trigger=0.00,
            p2_lock_mult=4.50,
            eval_symcap_pct=2.25,
            eval_usd_cluster_pct=2.75,
            eval_jpy_cluster_pct=2.50,
            eval_idx_cluster_pct=2.25,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=4.50,
            eval_amber_mult=0.60,
            eval_red_dd_pct=7.00,
            eval_red_mult=0.30,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
            eval_sizing_mode=1,
        ),
        SprintCandidate(
            candidate_id="SPR07_M50_SC225_B1",
            group="Sprint_T2",
            label="P1/P2 5.0x | SymCap 2.25% | SizingMode=1 | Amber 4.5%/0.60 Red 7.0%/0.30 | DS 4.25% KS 9.50%",
            p1_mult=5.00,
            p2_mult=5.00,
            p1_lock_trigger=0.00,
            p1_lock_mult=5.00,
            p2_lock_trigger=0.00,
            p2_lock_mult=5.00,
            eval_symcap_pct=2.25,
            eval_usd_cluster_pct=2.75,
            eval_jpy_cluster_pct=2.50,
            eval_idx_cluster_pct=2.25,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=4.50,
            eval_amber_mult=0.60,
            eval_red_dd_pct=7.00,
            eval_red_mult=0.30,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
            eval_sizing_mode=1,
        ),
        SprintCandidate(
            candidate_id="SPR08_M50_SC250_B1",
            group="Sprint_T2",
            label="P1/P2 5.0x | SymCap 2.50% | SizingMode=1 | Amber 4.0%/0.50 Red 6.5%/0.25 | DS 4.25% KS 9.50%",
            p1_mult=5.00,
            p2_mult=5.00,
            p1_lock_trigger=0.00,
            p1_lock_mult=5.00,
            p2_lock_trigger=0.00,
            p2_lock_mult=5.00,
            eval_symcap_pct=2.50,
            eval_usd_cluster_pct=3.00,
            eval_jpy_cluster_pct=2.75,
            eval_idx_cluster_pct=2.50,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=4.00,
            eval_amber_mult=0.50,
            eval_red_dd_pct=6.50,
            eval_red_mult=0.25,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
            eval_sizing_mode=1,
        ),
        SprintCandidate(
            candidate_id="SPR09_M45_P2_35_B1",
            group="Sprint_T2",
            label="P1 4.5x / P2 3.5x | SymCap 2.25% | SizingMode=1 | Amber 4.5%/0.60 Red 7.0%/0.30 | KS 9.50%",
            p1_mult=4.50,
            p2_mult=3.50,
            p1_lock_trigger=0.00,
            p1_lock_mult=4.50,
            p2_lock_trigger=0.00,
            p2_lock_mult=3.50,
            eval_symcap_pct=2.25,
            eval_usd_cluster_pct=2.75,
            eval_jpy_cluster_pct=2.50,
            eval_idx_cluster_pct=2.25,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=4.50,
            eval_amber_mult=0.60,
            eval_red_dd_pct=7.00,
            eval_red_mult=0.30,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.00,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
            eval_sizing_mode=1,
        ),
        SprintCandidate(
            candidate_id="SPR10_M50_P2_40_B1",
            group="Sprint_T2",
            label="P1 5.0x / P2 4.0x | SymCap 2.50% | SizingMode=1 | Amber 4.0%/0.55 Red 6.5%/0.25 | KS 9.50%",
            p1_mult=5.00,
            p2_mult=4.00,
            p1_lock_trigger=0.00,
            p1_lock_mult=5.00,
            p2_lock_trigger=0.00,
            p2_lock_mult=4.00,
            eval_symcap_pct=2.50,
            eval_usd_cluster_pct=3.00,
            eval_jpy_cluster_pct=2.75,
            eval_idx_cluster_pct=2.50,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=4.00,
            eval_amber_mult=0.55,
            eval_red_dd_pct=6.50,
            eval_red_mult=0.25,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.00,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
            eval_sizing_mode=1,
        ),
        SprintCandidate(
            candidate_id="SPR11_M45_SC250_S0_T",
            group="Sprint_T2",
            label="P1/P2 4.5x | SymCap 2.50% | Amber 3.5%/0.40 Red 6.0%/0.18 | DS 4.25% KS 9.50% | PL OFF",
            p1_mult=4.50,
            p2_mult=4.50,
            p1_lock_trigger=0.00,
            p1_lock_mult=4.50,
            p2_lock_trigger=0.00,
            p2_lock_mult=4.50,
            eval_symcap_pct=2.50,
            eval_usd_cluster_pct=3.00,
            eval_jpy_cluster_pct=2.75,
            eval_idx_cluster_pct=2.50,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.40,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.18,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
        SprintCandidate(
            candidate_id="SPR12_M50_SC250_S0_T",
            group="Sprint_T2",
            label="P1/P2 5.0x | SymCap 2.50% | Amber 3.5%/0.40 Red 6.0%/0.18 | DS 4.25% KS 9.50% | PL80",
            p1_mult=5.00,
            p2_mult=5.00,
            p1_lock_trigger=0.80,
            p1_lock_mult=3.00,
            p2_lock_trigger=0.80,
            p2_lock_mult=2.50,
            eval_symcap_pct=2.50,
            eval_usd_cluster_pct=3.00,
            eval_jpy_cluster_pct=2.75,
            eval_idx_cluster_pct=2.50,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.40,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.18,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
        # Tier 3 (High-Speed Ceiling Probes, 5.5x-6.0x up to hard 3.00% TotalOpenCap)
        SprintCandidate(
            candidate_id="SPR13_M55_SC275_B1",
            group="Sprint_T3",
            label="P1/P2 5.5x | SymCap 2.75% | SizingMode=1 | Amber 3.5%/0.40 Red 6.0%/0.18 | DS 4.25% KS 9.50%",
            p1_mult=5.50,
            p2_mult=5.50,
            p1_lock_trigger=0.00,
            p1_lock_mult=5.50,
            p2_lock_trigger=0.00,
            p2_lock_mult=5.50,
            eval_symcap_pct=2.75,
            eval_usd_cluster_pct=3.00,
            eval_jpy_cluster_pct=3.00,
            eval_idx_cluster_pct=2.75,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.50,
            eval_amber_mult=0.40,
            eval_red_dd_pct=6.00,
            eval_red_mult=0.18,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
            eval_sizing_mode=1,
        ),
        SprintCandidate(
            candidate_id="SPR14_M60_SC300_B1",
            group="Sprint_T3",
            label="P1/P2 6.0x | SymCap 3.00% | SizingMode=1 | Amber 3.0%/0.35 Red 5.5%/0.15 | DS 4.25% KS 9.50%",
            p1_mult=6.00,
            p2_mult=6.00,
            p1_lock_trigger=0.00,
            p1_lock_mult=6.00,
            p2_lock_trigger=0.00,
            p2_lock_mult=6.00,
            eval_symcap_pct=3.00,
            eval_usd_cluster_pct=3.00,
            eval_jpy_cluster_pct=3.00,
            eval_idx_cluster_pct=3.00,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=3.00,
            eval_amber_mult=0.35,
            eval_red_dd_pct=5.50,
            eval_red_mult=0.15,
            eval_p1_kill_daily_pct=4.25,
            eval_p2_kill_daily_pct=4.25,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
            eval_sizing_mode=1,
        ),
        SprintCandidate(
            candidate_id="SPR15_M60_SC300_NOBR",
            group="Sprint_T3",
            label="P1/P2 6.0x | SymCap 3.00% | No Amber/Red Brake (Aggressive Upper Bound Probe)",
            p1_mult=6.00,
            p2_mult=6.00,
            p1_lock_trigger=0.00,
            p1_lock_mult=6.00,
            p2_lock_trigger=0.00,
            p2_lock_mult=6.00,
            eval_symcap_pct=3.00,
            eval_usd_cluster_pct=3.00,
            eval_jpy_cluster_pct=3.00,
            eval_idx_cluster_pct=3.00,
            eval_total_open_cap_pct=3.00,
            eval_amber_dd_pct=9.50,
            eval_amber_mult=1.00,
            eval_red_dd_pct=9.80,
            eval_red_mult=1.00,
            eval_p1_kill_daily_pct=4.50,
            eval_p2_kill_daily_pct=4.50,
            eval_p1_kill_static_pct=9.50,
            eval_p2_kill_static_pct=9.50,
        ),
    ]


# ---------------------------------------------------------------------------
# 6. Exact `.set` Preset Generator for `Naqex_Master_Prop7E_v103.mq5`
# ---------------------------------------------------------------------------


def validate_candidate_invariants(cand: SprintCandidate, *, enforce_funded_1x: bool = True) -> None:
    """Fail-closed invariant validation matching `Naqex_Master_Prop7E_v103.mq5::OnInit` & `v3.5` gates."""
    if not isinstance(cand, SprintCandidate):
        raise ValueError(f"INVALID_CANDIDATE_TYPE: expected SprintCandidate, got {type(cand).__name__}")

    # Vector V1 fail-closed guard across ALL fields of SprintCandidate (reject NaN, +-Inf, and bool-as-number)
    for f in fields(SprintCandidate):
        val = getattr(cand, f.name)
        if f.type == "float":
            _require_finite_number(val, f"{cand.candidate_id}.{f.name}")
        elif f.type == "int":
            _require_strict_int(val, f"{cand.candidate_id}.{f.name}")
        elif f.type == "bool":
            if not isinstance(val, bool):
                raise ValueError(f"INVALID_BOOL_FIELD: {cand.candidate_id}.{f.name} must be bool (got {val!r})")

    if cand.eval_sizing_mode not in (0, 1):
        raise ValueError(f"INVALID_SIZING_MODE: {cand.candidate_id} eval_sizing_mode={cand.eval_sizing_mode!r}")

    for pos_field in (
        "p1_mult",
        "p2_mult",
        "eval_symcap_pct",
        "eval_usd_cluster_pct",
        "eval_jpy_cluster_pct",
        "eval_idx_cluster_pct",
        "eval_total_open_cap_pct",
        "eval_amber_dd_pct",
        "eval_amber_mult",
        "eval_red_dd_pct",
        "eval_red_mult",
        "eval_p1_kill_daily_pct",
        "eval_p2_kill_daily_pct",
        "eval_p1_kill_static_pct",
        "eval_p2_kill_static_pct",
        "funded_mult",
        "funded_symcap_pct",
        "funded_usd_cluster_pct",
        "funded_jpy_cluster_pct",
        "funded_idx_cluster_pct",
        "funded_total_open_cap_pct",
        "funded_amber_dd_pct",
        "funded_amber_mult",
        "funded_red_dd_pct",
        "funded_red_mult",
        "funded_kill_daily_pct",
        "funded_kill_static_pct",
    ):
        if float(getattr(cand, pos_field)) <= 0.0:
            raise ValueError(
                f"NON_POSITIVE_CANDIDATE_PARAM: {cand.candidate_id}.{pos_field}={getattr(cand, pos_field)!r}"
            )
    for nonneg_field in ("p1_lock_trigger", "p2_lock_trigger", "p1_lock_mult", "p2_lock_mult"):
        if float(getattr(cand, nonneg_field)) < 0.0:
            raise ValueError(
                f"NEGATIVE_CANDIDATE_PARAM: {cand.candidate_id}.{nonneg_field}={getattr(cand, nonneg_field)!r}"
            )

    eff_eval = effective_total_open_risk_cap_pct(cand.eval_total_open_cap_pct, HARD_TOTAL_OPEN_CEILING_PCT)
    eff_fn = effective_total_open_risk_cap_pct(cand.funded_total_open_cap_pct, HARD_TOTAL_OPEN_CEILING_PCT)
    if eff_eval > HARD_TOTAL_OPEN_CEILING_PCT + 1e-9:
        raise ValueError(f"EVAL_TOTAL_OPEN_CAP_BREACH: {cand.candidate_id} eff_eval={eff_eval}")
    if eff_fn > FUNDED_MAX_TOTAL_OPEN_CAP_PCT + 1e-9:
        raise ValueError(f"FUNDED_TOTAL_OPEN_CAP_BREACH: {cand.candidate_id} eff_fn={eff_fn} > 2.25%")
    if eff_eval * 1.25 > 4.50 + 1e-9:
        raise ValueError(f"GAP_SHOCK_125X_BREACH: {cand.candidate_id} 1.25x={eff_eval * 1.25:.2f}% > 4.50%")
    if not cand.enable_spread_guard:
        raise ValueError(f"SPREAD_GUARD_DISABLED: {cand.candidate_id}")
    if not cand.use_6ccy_news_10m or cand.news_pad_sec < 600:
        raise ValueError(f"NEWS_GUARD_6CCY_10M_DISABLED: {cand.candidate_id} pad={cand.news_pad_sec}")
    if enforce_funded_1x and cand.group != "Baseline":
        if abs(cand.funded_mult - FUNDED_LOCKED_MULT) > 1e-9:
            raise ValueError(f"FUNDED_NOT_LOCKED_1X: {cand.candidate_id} funded_mult={cand.funded_mult}")
        if abs(cand.funded_amber_dd_pct - 3.50) > 1e-9 or abs(cand.funded_red_dd_pct - 6.00) > 1e-9:
            raise ValueError(f"FUNDED_BRAKE_NOT_TIGHT: {cand.candidate_id}")
        if cand.funded_kill_static_pct > FUNDED_MAX_KILL_STATIC_DD_PCT + 1e-9:
            raise ValueError(
                f"FUNDED_KILL_STATIC_DD_TOO_LOOSE: {cand.candidate_id} "
                f"funded_kill_static_pct={cand.funded_kill_static_pct} > {FUNDED_MAX_KILL_STATIC_DD_PCT:.2f}%"
            )


def render_v103_set_file(
    cand: SprintCandidate,
    *,
    phase: str,
    capital_usd: float = 10_000.0,
    sku_label: str = "FTMO_STD_10K",
) -> str:
    """Render clean MT5 `.set` preset for immutable `Naqex_Master_Prop7E_v103.mq5` with fail-closed defaults."""
    if phase not in ("EVAL", "FUNDED"):
        raise ValueError(f"Unsupported phase for .set rendering: {phase!r}")
    validate_candidate_invariants(cand, enforce_funded_1x=(phase == "FUNDED"))

    if phase == "EVAL":
        sku_code = f"{sku_label}_V103_SPRINT_EVAL"
        target_pct = 10.00
        base_mult = cand.p1_mult
        pl_pct = round(10.0 * cand.p1_lock_trigger, 2) if cand.p1_lock_trigger > 0.0 else 0.00
        pl_mult = cand.p1_lock_mult if cand.p1_lock_trigger > 0.0 else cand.p1_mult
        amber_dd = cand.eval_amber_dd_pct
        amber_mult = cand.eval_amber_mult
        red_dd = cand.eval_red_dd_pct
        red_mult = cand.eval_red_mult
        kill_daily = cand.eval_p1_kill_daily_pct
        kill_static = cand.eval_p1_kill_static_pct
        tot_open = effective_total_open_risk_cap_pct(cand.eval_total_open_cap_pct, HARD_TOTAL_OPEN_CEILING_PCT)
        hard_ceil = HARD_TOTAL_OPEN_CEILING_PCT
        symcap = cand.eval_symcap_pct
        usd_cap = cand.eval_usd_cluster_pct
        jpy_cap = cand.eval_jpy_cluster_pct
        idx_cap = cand.eval_idx_cluster_pct
        sizing_mode = cand.eval_sizing_mode
        p2_pl_pct = round(5.0 * cand.p2_lock_trigger, 2) if cand.p2_lock_trigger > 0.0 else 0.00
        header_note = (
            f"; Naqex MT5 Master_Prop7E v1.03 Sprint Eval Preset ({cand.candidate_id}) | SKU: {sku_code}\n"
            f"; Phase 1 Defaults: Target=10.00% Mult={cand.p1_mult:.2f}x PL={pl_pct:.2f}%->{pl_mult:.2f}x "
            f"KillDaily={cand.eval_p1_kill_daily_pct:.2f}% KillStatic={cand.eval_p1_kill_static_pct:.2f}%\n"
            f"; Phase 2 Overrides: InpTargetProfitPct=5.00 InpBasePhaseMult={cand.p2_mult:.2f} "
            f"InpProfitLockPct={p2_pl_pct:.2f} InpProfitLockMult={cand.p2_lock_mult:.2f} "
            f"InpKillDailyDdPct={cand.eval_p2_kill_daily_pct:.2f} "
            f"InpKillStaticDdPct={cand.eval_p2_kill_static_pct:.2f}\n"
            "; Daily DD Basis: InpDailyResetMode=1 (Europe/Prague DST Midnight Balance / InitialBalance)\n"
            f"; Shield A+B1+B2+B3 ON: TotalOpenCap={tot_open:.2f}% (1.25x gap <= {tot_open * 1.25:.2f}% <= 4.50%), "
            "SpreadGuard=ON, 6-CCY +-10m Red-News=ON (+-135s hard ban)\n"
            "; FAIL-CLOSED DEFAULTS + B8 KILL-SWITCH READY: InpDryRunLogOnly=true, InpShadowCompareMode=true, "
            "InpGuardDryRunLogOnly=true, InpWritePrimaryHeartbeat=true, InpAllowManualHaltFile=true\n"
        )
    else:
        sku_code = f"{sku_label}_V103_FUNDED_1X"
        target_pct = 0.00
        base_mult = FUNDED_LOCKED_MULT
        pl_pct = 0.00
        pl_mult = FUNDED_LOCKED_MULT
        amber_dd = 3.50
        amber_mult = 0.65
        red_dd = 6.00
        red_mult = 0.40
        kill_daily = cand.funded_kill_daily_pct
        kill_static = min(cand.funded_kill_static_pct, FUNDED_MAX_KILL_STATIC_DD_PCT)
        tot_open = min(cand.funded_total_open_cap_pct, FUNDED_MAX_TOTAL_OPEN_CAP_PCT)
        hard_ceil = min(FUNDED_MAX_TOTAL_OPEN_CAP_PCT, HARD_TOTAL_OPEN_CEILING_PCT)
        symcap = cand.funded_symcap_pct
        usd_cap = cand.funded_usd_cluster_pct
        jpy_cap = cand.funded_jpy_cluster_pct
        idx_cap = cand.funded_idx_cluster_pct
        sizing_mode = 0
        header_note = (
            f"; Naqex MT5 Master_Prop7E v1.03 Funded 1.0x Preservation Preset | SKU: {sku_code}\n"
            f"; Strictly Locked Funded Profile: Mult=1.00x Amber=3.50%->0.65x Red=6.00%->0.40x "
            f"KillDaily={kill_daily:.2f}% KillStatic={kill_static:.2f}% (OPS-2 <= 8.00%)\n"
            "; Daily DD Basis: InpDailyResetMode=1 (Europe/Prague DST Midnight Balance / InitialBalance)\n"
            f"; Shield A+B1+B2+B3 ON: TotalOpenCap={tot_open:.2f}% (<= 2.25%, 1.25x gap <= {tot_open * 1.25:.2f}%), "
            "SpreadGuard=ON, 6-CCY +-10m Red-News=ON (+-135s hard ban)\n"
            "; FAIL-CLOSED DEFAULTS + B8 KILL-SWITCH READY: InpDryRunLogOnly=true, InpShadowCompareMode=true, "
            "InpGuardDryRunLogOnly=true, InpWritePrimaryHeartbeat=true, InpAllowManualHaltFile=true\n"
        )

    lines = [
        # Custom PropGuard inputs (`v103.mq5 L26-41`)
        "InpGuardDryRunLogOnly=true",
        f"InpGuardMaxDailyLossPct={kill_daily:.2f}",
        f"InpGuardMaxSymbolRiskPct={symcap:.2f}",
        "InpGuardUseOrchestrator=false",
        "InpGuardMaxSpreadPoints=35.00",
        "InpGuardRolloverStartUTC=21",
        "InpGuardRolloverEndUTC=0",
        "InpGuardEarlyCloseMin=10",
        "InpGuardTesterUtcOffsetH=2",
        "InpGuardEnableRedNews=true",
        "InpGuardRedNewsCsvFile=naqex_red_news_utc.csv",
        f"InpGuardNewsPadSec={cand.news_pad_sec}",
        "InpGuardNewsHardBanSec=135",
        "InpGuardTcaAuditCsvFile=naqex_exec_audit.csv",
        "InpGuardMagicRangeMin=20261120",
        "InpGuardMagicRangeMax=20261199",
        # Safety & Mode inputs (`v103.mq5 L47-50`)
        "InpDryRunLogOnly=true",
        "InpShadowCompareMode=true",
        "InpEnableS6Shadow=false",
        "InpWritePrimaryHeartbeat=true",
        # Contract & Phase inputs (`v103.mq5 L53-68`)
        f"InpContractSku={sku_code}",
        f"InpInitialBalanceUSD={capital_usd:.2f}",
        f"InpTargetProfitPct={target_pct:.2f}",
        "InpHardDailyDdPct=5.00",
        "InpHardStaticDdPct=10.00",
        "InpDailyResetMode=1",
        f"InpSizingMode={sizing_mode}",
        f"InpBasePhaseMult={base_mult:.2f}",
        f"InpProfitLockPct={pl_pct:.2f}",
        f"InpProfitLockMult={pl_mult:.2f}",
        f"InpAmberDdPct={amber_dd:.2f}",
        f"InpAmberMult={amber_mult:.2f}",
        f"InpRedDdPct={red_dd:.2f}",
        f"InpRedMult={red_mult:.2f}",
        f"InpKillDailyDdPct={kill_daily:.2f}",
        f"InpKillStaticDdPct={kill_static:.2f}",
        # Shield A & Shield B1 (`v103.mq5 L71-76`)
        f"InpMaxTotalOpenRiskPct={tot_open:.2f}",
        f"InpHardTotalOpenCeilingPct={hard_ceil:.2f}",
        f"InpMaxSymbolRiskPct={symcap:.2f}",
        f"InpMaxUsdClusterPct={usd_cap:.2f}",
        f"InpMaxJpyClusterPct={jpy_cap:.2f}",
        f"InpMaxIdxClusterPct={idx_cap:.2f}",
        # Shield B2 & Shield B3 (`v103.mq5 L79-84`)
        "InpEnableSpreadGuard=true",
        "InpMaxUsdJpySpreadPoints=25.00",
        "InpMaxGbpUsdSpreadPoints=35.00",
        "InpMaxEurJpySpreadPoints=25.00",
        "InpMaxIndexSpreadPoints=350.00",
        "InpUse6CcyNewsPad10m=true",
        # Multi-Symbol Aliases & Telemetry (`v103.mq5 L87-107`)
        "InpSymUSDJPY=USDJPY",
        "InpSymGBPUSD=GBPUSD",
        "InpSymEURJPY=EURJPY",
        "InpSymUS100=US100.cash",
        "InpSymUS500=US500.cash",
        "InpSymEURUSD=EURUSD",
        "InpSymAUDUSD=AUDUSD",
        "InpSymUSDCAD=USDCAD",
        "InpMaxSlippagePointsFx=35",
        "InpMaxSlippagePointsIdx=450",
        "InpMaxBreakoutTickLagMs=5000",
        "InpHeartbeatSec=15",
        "InpHeartbeatFile=naqex_master_v103_heartbeat.json",
        "InpShadowCsvFile=naqex_master_v103_shadow.csv",
        "InpProfitLockBasisMode=0",
        "InpOpportunityLifecycleMode=1",
        "InpPostCloseRefreshMode=1",
        "InpAllowManualHaltFile=true",
        "InpManualHaltFile=naqex_manual_halt.flag",
        "InpMagicRangeMin=20261120",
        "InpMagicRangeMax=20261199",
    ]
    return header_note + "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 7. Full Study Runner (Candidate Sweep + 7 SSOT SKUs + 4/5 Ticket Ruin + OOS)
# ---------------------------------------------------------------------------


def load_validated_target_skus(firms_catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH) -> dict[str, dict[str, Any]]:
    """Load exact `available_vn = true` target SKUs from SSOT catalog (fail-closed on unavailable/forbidden SKUs)."""
    doc = json.loads(firms_catalog_path.read_text(encoding="utf-8"))
    contracts = doc.get("contracts") or {}
    out: dict[str, dict[str, Any]] = {}
    for sku in TARGET_SKUS:
        if sku in FORBIDDEN_SKUS:
            raise ValueError(f"FORBIDDEN_SKU_REQUESTED: {sku}")
        if sku not in contracts:
            raise ValueError(f"MISSING_SSOT_SKU: {sku} not in {firms_catalog_path}")
        c = contracts[sku]
        if c.get("available_vn") is not True:
            raise ValueError(f"SKU_UNAVAILABLE_VN: {sku} has available_vn={c.get('available_vn')!r}")
        out[sku] = c
    return out


def _contract_daily_reset_mode(contract: dict[str, Any]) -> int:
    mode_str = str(contract.get("daily_dd_anchor_mode") or "")
    if mode_str == "MIDNIGHT_BALANCE_OVER_INITIAL":
        return 1
    return 0


def _payout_cycle_trading_days(contract: dict[str, Any]) -> int:
    cal_days = int(contract.get("payout_cycle_cal_days", 14))
    return max(1, int(round(cal_days / CALENDAR_DAYS_PER_TRADING_DAY)))


def evaluate_candidate_on_contract(
    *,
    cand: SprintCandidate,
    contract: dict[str, Any],
    ext_days: list[str],
    pre_days: list[dict[str, Any]],
    idx_matrix: np.ndarray,
    usd_vnd_rate: float,
    fee_day0_usd: float,
    max_retries: int = 0,
    balance_compounding: bool = True,
    replay_cache: dict[tuple[Any, ...], tuple[np.ndarray, np.ndarray, np.ndarray]] | None = None,
) -> dict[str, Any]:
    """Evaluate one SprintCandidate on one SSOT contract across `idx_matrix`."""
    cap = float(contract["capital_usd"])
    lev_fx = float(contract["leverage_fx"])
    lev_idx = float(contract["leverage_indices"])
    cache = replay_cache if replay_cache is not None else {}

    def _get_stage_tape(
        reg_m: float,
        base_m: float,
        symcap: float,
        u_cap: float,
        j_cap: float,
        i_cap: float,
        tot_cap: float,
        kill_daily: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        key = (
            round(cap, 2),
            round(lev_fx, 2),
            round(lev_idx, 2),
            round(reg_m, 4),
            round(base_m, 4),
            round(symcap, 3),
            round(u_cap, 3),
            round(j_cap, 3),
            round(i_cap, 3),
            round(tot_cap, 3),
            round(kill_daily, 3),
            len(ext_days),
        )
        if key not in cache:
            _, n_a, d_a, f_a = replay_v103_regime_stage(
                ext_days,
                pre_days,
                capital_usd=cap,
                regime_mult=reg_m,
                base_phase_mult=base_m,
                symcap_pct=symcap,
                usd_cluster_cap_pct=u_cap,
                jpy_cluster_cap_pct=j_cap,
                idx_cluster_cap_pct=i_cap,
                total_open_cap_pct=tot_cap,
                kill_daily_dd_pct=kill_daily,
                leverage_fx=lev_fx,
                leverage_indices=lev_idx,
                enable_daily_headroom_taper=True,
            )
            cache[key] = (n_a, d_a, f_a)
        return cache[key]

    e_caps = (
        cand.eval_symcap_pct,
        cand.eval_usd_cluster_pct,
        cand.eval_jpy_cluster_pct,
        cand.eval_idx_cluster_pct,
        cand.eval_total_open_cap_pct,
    )
    f_caps = (
        cand.funded_symcap_pct,
        cand.funded_usd_cluster_pct,
        cand.funded_jpy_cluster_pct,
        cand.funded_idx_cluster_pct,
        cand.funded_total_open_cap_pct,
    )

    p1_n = _get_stage_tape(cand.p1_mult, cand.p1_mult, *e_caps, cand.eval_p1_kill_daily_pct)
    p1_l = _get_stage_tape(
        cand.p1_lock_mult if cand.p1_lock_trigger > 0.0 else cand.p1_mult,
        cand.p1_mult,
        *e_caps,
        cand.eval_p1_kill_daily_pct,
    )
    p1_a = _get_stage_tape(cand.p1_mult * cand.eval_amber_mult, cand.p1_mult, *e_caps, cand.eval_p1_kill_daily_pct)
    p1_r = _get_stage_tape(cand.p1_mult * cand.eval_red_mult, cand.p1_mult, *e_caps, cand.eval_p1_kill_daily_pct)

    p2_n = _get_stage_tape(cand.p2_mult, cand.p2_mult, *e_caps, cand.eval_p2_kill_daily_pct)
    p2_l = _get_stage_tape(
        cand.p2_lock_mult if cand.p2_lock_trigger > 0.0 else cand.p2_mult,
        cand.p2_mult,
        *e_caps,
        cand.eval_p2_kill_daily_pct,
    )
    p2_a = _get_stage_tape(cand.p2_mult * cand.eval_amber_mult, cand.p2_mult, *e_caps, cand.eval_p2_kill_daily_pct)
    p2_r = _get_stage_tape(cand.p2_mult * cand.eval_red_mult, cand.p2_mult, *e_caps, cand.eval_p2_kill_daily_pct)

    fn_n = _get_stage_tape(cand.funded_mult, cand.funded_mult, *f_caps, cand.funded_kill_daily_pct)
    fn_a = _get_stage_tape(
        cand.funded_mult * cand.funded_amber_mult, cand.funded_mult, *f_caps, cand.funded_kill_daily_pct
    )
    fn_r = _get_stage_tape(
        cand.funded_mult * cand.funded_red_mult, cand.funded_mult, *f_caps, cand.funded_kill_daily_pct
    )

    raw = _simulate_v103_prop_lifecycle_numba(
        idx_matrix,
        p1_n[0],
        p1_n[1],
        p1_n[2],
        p1_l[0],
        p1_l[1],
        p1_l[2],
        p1_a[0],
        p1_a[1],
        p1_a[2],
        p1_r[0],
        p1_r[1],
        p1_r[2],
        p2_n[0],
        p2_n[1],
        p2_n[2],
        p2_l[0],
        p2_l[1],
        p2_l[2],
        p2_a[0],
        p2_a[1],
        p2_a[2],
        p2_r[0],
        p2_r[1],
        p2_r[2],
        fn_n[0],
        fn_n[1],
        fn_n[2],
        fn_a[0],
        fn_a[1],
        fn_a[2],
        fn_r[0],
        fn_r[1],
        fn_r[2],
        cap,
        float(fee_day0_usd),
        float(contract["fee_orig_usd"]),
        float(contract["card_fx_fee_frac"]),
        float(contract["withdrawal_fee_frac"]),
        float(contract["fee_refund_external_cash_frac"]),
        float(contract["p1_target_frac"]),
        float(contract["p2_target_frac"]),
        float(contract["daily_loss_limit_frac"]),
        float(contract["static_loss_limit_frac"]),
        _contract_daily_reset_mode(contract),
        int(contract["min_trading_days"]),
        int(contract.get("min_profitable_days", 0)),
        float(contract.get("profitable_day_threshold_frac", 0.0)),
        float(contract["payout_split_frac"]),
        _payout_cycle_trading_days(contract),
        float(contract["min_payout_usd"]),
        float(cand.p1_lock_trigger),
        float(cand.p2_lock_trigger),
        float(cand.p1_lock_mult / max(1e-9, cand.p1_mult)) if cand.p1_lock_trigger > 0.0 else 1.0,
        float(cand.p2_lock_mult / max(1e-9, cand.p2_mult)) if cand.p2_lock_trigger > 0.0 else 1.0,
        float(cand.eval_amber_dd_pct) / 100.0,
        float(cand.eval_amber_mult),
        float(cand.eval_red_dd_pct) / 100.0,
        float(cand.eval_red_mult),
        float(cand.eval_p1_kill_daily_pct) / 100.0,
        float(cand.eval_p2_kill_daily_pct) / 100.0,
        float(cand.eval_p1_kill_static_pct) / 100.0,
        float(cand.eval_p2_kill_static_pct) / 100.0,
        int(cand.eval_sizing_mode),
        float(cand.funded_amber_dd_pct) / 100.0,
        float(cand.funded_red_dd_pct) / 100.0,
        float(cand.funded_kill_daily_pct) / 100.0,
        float(cand.funded_kill_static_pct) / 100.0,
        0.06,
        int(max_retries),
        bool(balance_compounding),
    )
    return summarize_lifecycle_mc(
        raw,
        fee_day0_usd=fee_day0_usd,
        card_fx_fee_pct=float(contract["card_fx_fee_frac"]),
        usd_vnd_rate=usd_vnd_rate,
        horizon_days=int(idx_matrix.shape[1]),
    )


def select_winning_sprint_candidate(
    candidate_results: dict[str, dict[str, Any]],
    *,
    fail_budget_min_pct: float = 15.0,
    fail_budget_max_pct: float = 30.0,
    target_band_min_pct: float = 20.0,
    target_band_max_pct: float = 30.0,
) -> tuple[str, str]:
    """Select the winning `.set`-only Eval Sprint candidate under strict safety & speed-EV criteria.

    Hard filters:
      - Group != Baseline / Baseline_Fn1x (must be Funded 1.0x Sprint candidate)
      - `worst_gap_125x_pct <= 4.50%`
      - `funded_12m_breach_pct < 1.00%`
      - `fail_24m_pct <= fail_budget_max_pct` (never exceeds 30% fail budget)

    Preference:
      1. Prefer candidates inside the `20%..30%` Eval fail budget target band (if any exist);
         otherwise pick from all eligible `<= 30%` Sprint candidates with highest `EV/Fee` + pass speed.
      2. Rank by `ev_per_fee_npv24` (primary), breaking near-ties (`within 0.15x`) by faster
         unconditional P1+P2 median pass time (`-full_med_pass_cal_days_uncond`) and higher `pass_6m_pct`.
    """
    eligible: list[tuple[str, dict[str, Any]]] = []
    for cid, obj in candidate_results.items():
        cfg = obj["config"]
        if cfg["group"] in ("Baseline", "Baseline_Fn1x"):
            continue
        m = obj["ftmo_std_10k_bf_1x"]
        if not obj["shock_eval"]["safe_le_4_50_at_125x"] or not obj["shock_funded"]["safe_le_4_50_at_125x"]:
            continue
        if m["funded_12m_breach_pct"] >= 1.00:
            continue
        if m["fail_24m_pct"] > fail_budget_max_pct + 1e-9:
            continue
        eligible.append((cid, obj))

    if not eligible:
        raise ValueError("NO_ELIGIBLE_SPRINT_CANDIDATE: zero candidates satisfied safety and <=30% fail budget")

    in_target_band = [
        (cid, obj)
        for cid, obj in eligible
        if target_band_min_pct - 1e-9 <= obj["ftmo_std_10k_bf_1x"]["fail_24m_pct"] <= target_band_max_pct + 1e-9
    ]
    pool = in_target_band if in_target_band else eligible
    reason_tag = (
        "IN_20_30_FAIL_BUDGET_BAND"
        if in_target_band
        else f"HIGHEST_EV_SPEED_UNDER_{int(fail_budget_max_pct)}PCT_CAP_PHYSICAL_CEILING"
    )

    # Composite tie-aware ranking: maximize EV/Fee (quantized to 0.10x band -> faster pass wins near-ties!)
    best_ev = max(obj["ftmo_std_10k_bf_1x"]["ev_per_fee_npv24"] for _, obj in pool)
    near_top = [
        (cid, obj)
        for cid, obj in pool
        if obj["ftmo_std_10k_bf_1x"]["ev_per_fee_npv24"] >= best_ev - 0.15
    ]
    winner_id, _ = max(
        near_top,
        key=lambda kv: (
            -kv[1]["ftmo_std_10k_bf_1x"]["full_med_pass_cal_days_uncond"],
            kv[1]["ftmo_std_10k_bf_1x"]["pass_6m_pct"],
            kv[1]["ftmo_std_10k_bf_1x"]["ev_per_fee_npv24"],
        ),
    )
    _ = fail_budget_min_pct
    return winner_id, reason_tag


def run_m1_v103_sprint_study(
    *,
    derived_dir: Path = DEFAULT_DERIVED_DIR,
    m1_cache_dir: Path = DEFAULT_M1_CACHE_DIR,
    cal_523_path: Path = DEFAULT_CAL_523_PATH,
    fx_rates_path: Path = DEFAULT_FX_RATES_PATH,
    firms_catalog_path: Path = DEFAULT_FIRMS_CATALOG_PATH,
    n_paths: int = DEFAULT_N_PATHS,
    seed: int = DEFAULT_SEED,
    skip_m1_spread_scan: bool = False,
    write_presets_dir: Path | None = DEFAULT_PRESETS_DIR,
) -> dict[str, Any]:
    """Execute the full Front-1 M1-V103-SPRINT `.set`-only accelerator optimization."""
    if n_paths < 1:
        raise ValueError(f"INVALID_N_PATHS: n_paths={n_paths} must be >= 1")

    t0 = time.perf_counter()
    data = load_frozen_tapes_direct(derived_dir=derived_dir)
    ext_days: list[str] = data["ext_days"]
    raw_tapes = data["tapes"]
    reset_audit = audit_tape_reset_crossings(raw_tapes)

    fx_doc = json.loads(fx_rates_path.read_text(encoding="utf-8"))
    usd_vnd = float(fx_doc["usd_vnd"])
    skus = load_validated_target_skus(firms_catalog_path)
    c10k = skus["ftmo_standard_10k"]

    cal_523 = load_red_news_calendar_6ccy(cal_523_path)
    if skip_m1_spread_scan:
        spread_calib: dict[str, Any] = {
            "available": False,
            "reason": "skipped_by_flag",
            "calibrated_dev_caps_a": {},
            "entry_spread_pts": {},
        }
    else:
        spread_calib = calibrate_m1_spread_guard(raw_tapes, m1_cache_dir=m1_cache_dir)

    raw_ep = spread_calib.get("entry_spread_pts")
    entry_spread_pts: dict[tuple[str, str], float] | None = raw_ep if isinstance(raw_ep, dict) and raw_ep else None
    raw_caps_a = spread_calib.get("calibrated_dev_caps_a")
    spread_caps_a: dict[str, float] | None = (
        {str(k): float(v) for k, v in raw_caps_a.items()} if isinstance(raw_caps_a, dict) and raw_caps_a else None
    )
    spread_guard_active = bool(spread_calib.get("available") and entry_spread_pts and spread_caps_a)

    # Shield B2 + Shield B3 (6-CCY +-10m) prealigned tapes at 1.00x friction
    guarded_1x, guard_stats_1x = apply_shield_b2_b3_guards(
        raw_tapes,
        red_news_cal=cal_523,
        news_pad_sec=600,
        spread_caps_pts=spread_caps_a if spread_guard_active else None,
        entry_spread_pts=entry_spread_pts if spread_guard_active else None,
    )
    pre_1x = prealign_days_for_tapes(ext_days, guarded_1x)

    idx_full = make_block_bootstrap_indices(len(ext_days), horizon=DEFAULT_HORIZON_DAYS, n_paths=n_paths, seed=seed)

    # 1. Core 100K 1.0x Funded Law-15 Portfolio Metrics (under locked Funded 1.0x Shield C)
    core_100k_1x, _, _, _ = replay_v103_regime_stage(
        ext_days,
        pre_1x,
        capital_usd=100_000.0,
        regime_mult=1.00,
        base_phase_mult=1.00,
        symcap_pct=1.00,
        usd_cluster_cap_pct=1.50,
        jpy_cluster_cap_pct=1.25,
        idx_cluster_cap_pct=1.00,
        total_open_cap_pct=2.00,
        kill_daily_dd_pct=2.50,
        leverage_fx=100.0,
        leverage_indices=50.0,
        enable_daily_headroom_taper=True,
    )

    # 2. Full 10k-path sweep across all pre-registered `.set`-only candidates on FTMO Standard 10K
    candidates = build_sprint_candidates()
    cand_map = {c.candidate_id: c for c in candidates}
    replay_cache_1x: dict[tuple[Any, ...], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    candidates_out: dict[str, Any] = {}

    for cand in candidates:
        validate_candidate_invariants(cand, enforce_funded_1x=(cand.group != "Baseline"))
        shock_eval = compute_honest_gap_shock_pct(
            mult=max(cand.p1_mult, cand.p2_mult),
            symcap_pct=cand.eval_symcap_pct,
            usd_cluster_pct=cand.eval_usd_cluster_pct,
            jpy_cluster_pct=cand.eval_jpy_cluster_pct,
            idx_cluster_pct=cand.eval_idx_cluster_pct,
            total_open_cap_pct=cand.eval_total_open_cap_pct,
        )
        shock_funded = compute_honest_gap_shock_pct(
            mult=cand.funded_mult,
            symcap_pct=cand.funded_symcap_pct,
            usd_cluster_pct=cand.funded_usd_cluster_pct,
            jpy_cluster_pct=cand.funded_jpy_cluster_pct,
            idx_cluster_pct=cand.funded_idx_cluster_pct,
            total_open_cap_pct=cand.funded_total_open_cap_pct,
        )
        # Historical P1 replay diagnostics (empirical worst intraday DD & peak open risk on Dev 2018-2024)
        p1_diag, _, _, _ = replay_v103_regime_stage(
            ext_days,
            pre_1x,
            capital_usd=10_000.0,
            regime_mult=cand.p1_mult,
            base_phase_mult=cand.p1_mult,
            symcap_pct=cand.eval_symcap_pct,
            usd_cluster_cap_pct=cand.eval_usd_cluster_pct,
            jpy_cluster_cap_pct=cand.eval_jpy_cluster_pct,
            idx_cluster_cap_pct=cand.eval_idx_cluster_pct,
            total_open_cap_pct=cand.eval_total_open_cap_pct,
            kill_daily_dd_pct=cand.eval_p1_kill_daily_pct,
            leverage_fx=100.0,
            leverage_indices=50.0,
            enable_daily_headroom_taper=True,
        )

        mc_bf = evaluate_candidate_on_contract(
            cand=cand,
            contract=c10k,
            ext_days=ext_days,
            pre_days=pre_1x,
            idx_matrix=idx_full,
            usd_vnd_rate=usd_vnd,
            fee_day0_usd=float(c10k["fee_promo_usd"]),
            max_retries=0,
            balance_compounding=True,
            replay_cache=replay_cache_1x,
        )
        mc_orig = evaluate_candidate_on_contract(
            cand=cand,
            contract=c10k,
            ext_days=ext_days,
            pre_days=pre_1x,
            idx_matrix=idx_full,
            usd_vnd_rate=usd_vnd,
            fee_day0_usd=float(c10k["fee_orig_usd"]),
            max_retries=0,
            balance_compounding=True,
            replay_cache=replay_cache_1x,
        )
        # True sequential 4-ticket (max_retries=3) and 5-ticket (max_retries=4) bankroll ruin & NPV
        mc_4t = evaluate_candidate_on_contract(
            cand=cand,
            contract=c10k,
            ext_days=ext_days,
            pre_days=pre_1x,
            idx_matrix=idx_full,
            usd_vnd_rate=usd_vnd,
            fee_day0_usd=float(c10k["fee_promo_usd"]),
            max_retries=3,
            balance_compounding=True,
            replay_cache=replay_cache_1x,
        )
        mc_5t = evaluate_candidate_on_contract(
            cand=cand,
            contract=c10k,
            ext_days=ext_days,
            pre_days=pre_1x,
            idx_matrix=idx_full,
            usd_vnd_rate=usd_vnd,
            fee_day0_usd=float(c10k["fee_promo_usd"]),
            max_retries=4,
            balance_compounding=True,
            replay_cache=replay_cache_1x,
        )

        candidates_out[cand.candidate_id] = {
            "config": asdict(cand),
            "shock_eval": shock_eval,
            "shock_funded": shock_funded,
            "p1_dev_replay_10k": p1_diag,
            "ftmo_std_10k_bf_1x": mc_bf,
            "ftmo_std_10k_orig_1x": mc_orig,
            "bankroll_4_ticket_bf_1x": {
                "sequential_ruin_pct": mc_4t["wiped_all_tickets_pct"],
                "iid_ruin_pct": mc_bf["iid_ruin_4_tickets_pct"],
                "pass_12m_pct": mc_4t["pass_12m_pct"],
                "pass_24m_pct": mc_4t["pass_24m_pct"],
                "ev_npv_24m_usd": mc_4t["ev_npv_24m_usd"],
                "ev_npv_24m_vnd_tr": mc_4t["ev_npv_24m_vnd_tr"],
                "med_npv_24m_usd": mc_4t["med_npv_24m_usd"],
                "med_npv_24m_vnd_tr": mc_4t["med_npv_24m_vnd_tr"],
                "mean_tickets_used": mc_4t["mean_tickets_used"],
                "p_npv24_le_0_pct": mc_4t["p_npv24_le_0_pct"],
            },
            "bankroll_5_ticket_bf_1x": {
                "sequential_ruin_pct": mc_5t["wiped_all_tickets_pct"],
                "iid_ruin_pct": mc_bf["iid_ruin_5_tickets_pct"],
                "pass_12m_pct": mc_5t["pass_12m_pct"],
                "pass_24m_pct": mc_5t["pass_24m_pct"],
                "ev_npv_24m_usd": mc_5t["ev_npv_24m_usd"],
                "ev_npv_24m_vnd_tr": mc_5t["ev_npv_24m_vnd_tr"],
                "med_npv_24m_usd": mc_5t["med_npv_24m_usd"],
                "med_npv_24m_vnd_tr": mc_5t["med_npv_24m_vnd_tr"],
                "mean_tickets_used": mc_5t["mean_tickets_used"],
                "p_npv24_le_0_pct": mc_5t["p_npv24_le_0_pct"],
            },
        }

    winner_id, winner_reason = select_winning_sprint_candidate(candidates_out)
    winner_cand = cand_map[winner_id]
    base_fn1x_cand = cand_map["BASE_V103_SHIELD_C_FN1X"]
    base_fn125_cand = cand_map["BASE_V103_SHIELD_C_FN125"]

    # 3. Full 7-SKU SSOT Matrix (`available_vn = true` ONLY) comparing Winner vs Baselines (1.0x & 1.25x)
    #    with direct per-SKU 0.01-lot-floored Funded 1.0x Law-15 replay metrics (NO linear scaling from 100K!)
    sku_matrix: dict[str, Any] = {}
    for sku_id in TARGET_SKUS:
        contract = skus[sku_id]
        fee_promo = float(contract["fee_promo_usd"])
        fee_orig = float(contract["fee_orig_usd"])
        funded_1x_dev_law15, _, _, _ = replay_v103_regime_stage(
            ext_days,
            pre_1x,
            capital_usd=float(contract["capital_usd"]),
            regime_mult=winner_cand.funded_mult,
            base_phase_mult=winner_cand.funded_mult,
            symcap_pct=winner_cand.funded_symcap_pct,
            usd_cluster_cap_pct=winner_cand.funded_usd_cluster_pct,
            jpy_cluster_cap_pct=winner_cand.funded_jpy_cluster_pct,
            idx_cluster_cap_pct=winner_cand.funded_idx_cluster_pct,
            total_open_cap_pct=winner_cand.funded_total_open_cap_pct,
            kill_daily_dd_pct=winner_cand.funded_kill_daily_pct,
            leverage_fx=float(contract["leverage_fx"]),
            leverage_indices=float(contract["leverage_indices"]),
            enable_daily_headroom_taper=True,
        )
        funded_1x_dev_law15["max_dd_pct"] = funded_1x_dev_law15["peak_dd_pct"]
        funded_1x_dev_law15["ev_vnd_per_trade"] = round(float(funded_1x_dev_law15["ev_usd_per_trade"]) * usd_vnd, 0)
        sku_entry: dict[str, Any] = {
            "contract_id": sku_id,
            "display_name": contract["display_name"],
            "firm_id": contract["firm_id"],
            "capital_usd": float(contract["capital_usd"]),
            "available_vn": True,
            "daily_reset_mode": _contract_daily_reset_mode(contract),
            "reset_tz": contract["reset_tz"],
            "p1_target_pct": round(100.0 * float(contract["p1_target_frac"]), 2),
            "p2_target_pct": round(100.0 * float(contract["p2_target_frac"]), 2),
            "min_trading_days": int(contract["min_trading_days"]),
            "min_profitable_days": int(contract.get("min_profitable_days", 0)),
            "profitable_day_threshold_pct": round(100.0 * float(contract.get("profitable_day_threshold_frac", 0.0)), 2),
            "leverage_fx": float(contract["leverage_fx"]),
            "leverage_indices": float(contract["leverage_indices"]),
            "fee_promo_usd": fee_promo,
            "fee_orig_usd": fee_orig,
            "promo_label": contract["promo_label"],
            "execution_status": contract["execution_status"],
            "funded_1x_dev_law15": funded_1x_dev_law15,
            "winner_promo_1x": evaluate_candidate_on_contract(
                cand=winner_cand,
                contract=contract,
                ext_days=ext_days,
                pre_days=pre_1x,
                idx_matrix=idx_full,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=fee_promo,
                max_retries=0,
                balance_compounding=True,
                replay_cache=replay_cache_1x,
            ),
            "winner_4_ticket_promo": None,
            "winner_5_ticket_promo": None,
            "baseline_fn1x_promo_1x": evaluate_candidate_on_contract(
                cand=base_fn1x_cand,
                contract=contract,
                ext_days=ext_days,
                pre_days=pre_1x,
                idx_matrix=idx_full,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=fee_promo,
                max_retries=0,
                balance_compounding=True,
                replay_cache=replay_cache_1x,
            ),
            "baseline_fn125_promo_1x": evaluate_candidate_on_contract(
                cand=base_fn125_cand,
                contract=contract,
                ext_days=ext_days,
                pre_days=pre_1x,
                idx_matrix=idx_full,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=fee_promo,
                max_retries=0,
                balance_compounding=True,
                replay_cache=replay_cache_1x,
            ),
        }
        w4 = evaluate_candidate_on_contract(
            cand=winner_cand,
            contract=contract,
            ext_days=ext_days,
            pre_days=pre_1x,
            idx_matrix=idx_full,
            usd_vnd_rate=usd_vnd,
            fee_day0_usd=fee_promo,
            max_retries=3,
            balance_compounding=True,
            replay_cache=replay_cache_1x,
        )
        w5 = evaluate_candidate_on_contract(
            cand=winner_cand,
            contract=contract,
            ext_days=ext_days,
            pre_days=pre_1x,
            idx_matrix=idx_full,
            usd_vnd_rate=usd_vnd,
            fee_day0_usd=fee_promo,
            max_retries=4,
            balance_compounding=True,
            replay_cache=replay_cache_1x,
        )
        sku_entry["winner_4_ticket_promo"] = {
            "sequential_ruin_pct": w4["wiped_all_tickets_pct"],
            "pass_12m_pct": w4["pass_12m_pct"],
            "pass_24m_pct": w4["pass_24m_pct"],
            "ev_npv_24m_usd": w4["ev_npv_24m_usd"],
            "ev_npv_24m_vnd_tr": w4["ev_npv_24m_vnd_tr"],
            "mean_tickets_used": w4["mean_tickets_used"],
        }
        sku_entry["winner_5_ticket_promo"] = {
            "sequential_ruin_pct": w5["wiped_all_tickets_pct"],
            "pass_12m_pct": w5["pass_12m_pct"],
            "pass_24m_pct": w5["pass_24m_pct"],
            "ev_npv_24m_usd": w5["ev_npv_24m_usd"],
            "ev_npv_24m_vnd_tr": w5["ev_npv_24m_vnd_tr"],
            "mean_tickets_used": w5["mean_tickets_used"],
        }
        if abs(fee_orig - fee_promo) > 1e-6:
            sku_entry["winner_orig_1x"] = evaluate_candidate_on_contract(
                cand=winner_cand,
                contract=contract,
                ext_days=ext_days,
                pre_days=pre_1x,
                idx_matrix=idx_full,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=fee_orig,
                max_retries=0,
                balance_compounding=True,
                replay_cache=replay_cache_1x,
            )
        sku_matrix[sku_id] = sku_entry

    # 4. Friction Sensitivity (`0.66x / 1.00x / 1.50x / 1.75x`) & Cluster A vs Cluster B Stability on FTMO Std 10K
    friction_sensitivity: dict[str, Any] = {}
    for f_lbl, f_val in (("0.66x", 0.66), ("1.00x", 1.00), ("1.50x", 1.50), ("1.75x", 1.75)):
        if abs(f_val - 1.00) < 1e-9:
            pre_f = pre_1x
            rc_f = replay_cache_1x
        else:
            st_f = apply_cost_stress_to_tapes(raw_tapes, f_val)
            g_f, _ = apply_shield_b2_b3_guards(
                st_f,
                red_news_cal=cal_523,
                news_pad_sec=600,
                spread_caps_pts=spread_caps_a if spread_guard_active else None,
                entry_spread_pts=entry_spread_pts if spread_guard_active else None,
            )
            pre_f = prealign_days_for_tapes(ext_days, g_f)
            rc_f = {}
        friction_sensitivity[f_lbl] = {
            "winner": evaluate_candidate_on_contract(
                cand=winner_cand,
                contract=c10k,
                ext_days=ext_days,
                pre_days=pre_f,
                idx_matrix=idx_full,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=float(c10k["fee_promo_usd"]),
                max_retries=0,
                balance_compounding=True,
                replay_cache=rc_f,
            ),
            "baseline_fn1x": evaluate_candidate_on_contract(
                cand=base_fn1x_cand,
                contract=c10k,
                ext_days=ext_days,
                pre_days=pre_f,
                idx_matrix=idx_full,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=float(c10k["fee_promo_usd"]),
                max_retries=0,
                balance_compounding=True,
                replay_cache=rc_f,
            ),
        }

    # Cluster A (2018-2020) vs Cluster B (2021-2024) split stability check
    cluster_stability: dict[str, Any] = {}
    days_a = [d for d in ext_days if d < CLUSTER_A_CUTOFF_DAY]
    days_b = [d for d in ext_days if d >= CLUSTER_A_CUTOFF_DAY]
    for cl_lbl, cl_days in (("cluster_a_2018_2020", days_a), ("cluster_b_2021_2024", days_b)):
        pre_cl = prealign_days_for_tapes(cl_days, guarded_1x)
        idx_cl = make_block_bootstrap_indices(
            len(cl_days), horizon=DEFAULT_HORIZON_DAYS, n_paths=n_paths, seed=seed + 17
        )
        rc_cl: dict[tuple[Any, ...], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        cluster_stability[cl_lbl] = {
            "n_days": len(cl_days),
            "window": f"{cl_days[0]}..{cl_days[-1]}",
            "winner": evaluate_candidate_on_contract(
                cand=winner_cand,
                contract=c10k,
                ext_days=cl_days,
                pre_days=pre_cl,
                idx_matrix=idx_cl,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=float(c10k["fee_promo_usd"]),
                max_retries=0,
                balance_compounding=True,
                replay_cache=rc_cl,
            ),
            "baseline_fn1x": evaluate_candidate_on_contract(
                cand=base_fn1x_cand,
                contract=c10k,
                ext_days=cl_days,
                pre_days=pre_cl,
                idx_matrix=idx_cl,
                usd_vnd_rate=usd_vnd,
                fee_day0_usd=float(c10k["fee_promo_usd"]),
                max_retries=0,
                balance_compounding=True,
                replay_cache=rc_cl,
            ),
        }

    # 5. Generate & Atomically Write Clean Fail-Closed `.set` Presets
    presets_written: dict[str, str] = {}
    if write_presets_dir is not None:
        eval_set_path = write_presets_dir / "FTMO_Std10K_v103_Sprint_Eval.set"
        funded_set_path = write_presets_dir / "FTMO_Std10K_v103_Funded_1x.set"
        _atomic_write_text(eval_set_path, render_v103_set_file(winner_cand, phase="EVAL", capital_usd=10_000.0))
        _atomic_write_text(funded_set_path, render_v103_set_file(winner_cand, phase="FUNDED", capital_usd=10_000.0))
        presets_written = {
            "eval_set": str(eval_set_path),
            "eval_set_sha256": _sha256_file(eval_set_path),
            "funded_set": str(funded_set_path),
            "funded_set_sha256": _sha256_file(funded_set_path),
        }

    # Explicit per-SKU Eval 24m fail band disclosure (selection anchored on ftmo_standard_10k;
    # larger accounts with finer 0.01-lot granularity can sit marginally above 30.00%)
    eval_fail_by_sku: dict[str, Any] = {}
    for sku_id in TARGET_SKUS:
        fail_24 = float(sku_matrix[sku_id]["winner_promo_1x"]["fail_24m_pct"])
        eval_fail_by_sku[sku_id] = {
            "capital_usd": float(sku_matrix[sku_id]["capital_usd"]),
            "eval_24m_fail_pct": fail_24,
            "within_20_30_band": 20.0 - 1e-9 <= fail_24 <= 30.0 + 1e-9,
            "delta_above_30_pct": round(max(0.0, fail_24 - 30.0), 2),
        }
    skus_above_30 = [
        sku_id for sku_id, info in eval_fail_by_sku.items() if info["eval_24m_fail_pct"] > 30.0 + 1e-9
    ]
    anchor_fail = eval_fail_by_sku["ftmo_standard_10k"]["eval_24m_fail_pct"]
    above_desc = (
        ", ".join(
            f"{sid}={eval_fail_by_sku[sid]['eval_24m_fail_pct']:.2f}% "
            f"(+{eval_fail_by_sku[sid]['delta_above_30_pct']:.2f}%)"
            for sid in skus_above_30
        )
        if skus_above_30
        else "none"
    )
    eval_fail_band_disclosure = {
        "selection_anchor_sku": "ftmo_standard_10k",
        "selection_band_pct": [20.0, 30.0],
        "anchor_sku_eval_24m_fail_pct": anchor_fail,
        "anchor_within_20_30_band": eval_fail_by_sku["ftmo_standard_10k"]["within_20_30_band"],
        "skus_marginally_above_30_pct": skus_above_30,
        "by_sku": eval_fail_by_sku,
        "note": (
            f"The 20%-30% Eval fail selection band in select_winning_sprint_candidate() is anchored on "
            f"ftmo_standard_10k ({anchor_fail:.2f}%). Larger accounts with finer 0.01-lot sizing granularity "
            f"exhibit marginally higher Eval 24m fail rates: {above_desc}."
        ),
    }

    spread_calib_public = {k: v for k, v in spread_calib.items() if k != "entry_spread_pts"}
    return {
        "schema": "naqex-offensive3-m1-v103-sprint-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "evidence_stage": "DEV_BACKTEST_2018_2024_CLUSTER_B_VIEWED_NOT_BLIND_DAILY_APPROX_V103_PARITY",
        "dev_window": f"{ext_days[0]}..{ext_days[-1]}",
        "n_dev_days": len(ext_days),
        "max_day": data["max_day"],
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "frozen_tapes_binding_sha256": data["binding_sha256"],
        "frozen_tapes_npz_sha256": data["npz_sha256"],
        "usd_vnd_rate": usd_vnd,
        "n_paths": n_paths,
        "seed": seed,
        "block_len": BLOCK_LEN,
        "horizon_trading_days": DEFAULT_HORIZON_DAYS,
        "official_v103_baseline_ev_per_fee_ref": OFFICIAL_V103_BASELINE_EV_PER_FEE,
        "unified_funded_kill_static_dd_pct": winner_cand.funded_kill_static_pct,
        "spread_guard_active": spread_guard_active,
        "m1_spread_calibration": spread_calib_public,
        "guard_stats_1x": guard_stats_1x,
        "reset_boundary_audit": reset_audit,
        "core_100k_1x_funded_law15": core_100k_1x,
        "winner_candidate_id": winner_id,
        "winner_selection_reason": winner_reason,
        "eval_fail_band_disclosure": eval_fail_band_disclosure,
        "presets_written": presets_written,
        "runtime_seconds": round(time.perf_counter() - t0, 3),
        "candidates": candidates_out,
        "target_skus": list(TARGET_SKUS),
        "sku_matrix": sku_matrix,
        "friction_sensitivity_ftmo_std_10k": friction_sensitivity,
        "cluster_stability_ftmo_std_10k": cluster_stability,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Front 1 (Offensive #3 v3.5): .set-only Prop Challenge Accelerator for immutable PORT_7E v1.03."
    )
    p.add_argument("--derived-dir", type=Path, default=DEFAULT_DERIVED_DIR)
    p.add_argument("--m1-cache-dir", type=Path, default=DEFAULT_M1_CACHE_DIR)
    p.add_argument("--cal-523", type=Path, default=DEFAULT_CAL_523_PATH)
    p.add_argument("--fx-rates", type=Path, default=DEFAULT_FX_RATES_PATH)
    p.add_argument("--firms-catalog", type=Path, default=DEFAULT_FIRMS_CATALOG_PATH)
    p.add_argument("--n-paths", type=int, default=DEFAULT_N_PATHS)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--skip-m1-spread-scan", action="store_true")
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    p.add_argument("--presets-dir", type=Path, default=DEFAULT_PRESETS_DIR)
    p.add_argument("--no-write-presets", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    res = run_m1_v103_sprint_study(
        derived_dir=args.derived_dir,
        m1_cache_dir=args.m1_cache_dir,
        cal_523_path=args.cal_523,
        fx_rates_path=args.fx_rates,
        firms_catalog_path=args.firms_catalog,
        n_paths=args.n_paths,
        seed=args.seed,
        skip_m1_spread_scan=args.skip_m1_spread_scan,
        write_presets_dir=None if args.no_write_presets else args.presets_dir,
    )
    if args.out_json is not None:
        _atomic_write_json(args.out_json, res)

    win_id = res["winner_candidate_id"]
    print(
        f"M1_V103_SPRINT_OK dev={res['dev_window']} n_paths={res['n_paths']} seed={res['seed']} "
        f"holdout_rows={res['holdout_rows_analysed']} order_send={res['order_send_count']} "
        f"winner={win_id} ({res['winner_selection_reason']}) runtime={res['runtime_seconds']}s"
    )
    print(
        f"{'CANDIDATE':<26} | {'EV/Fee':>7} | {'NPV24 USD/VND':>15} | {'P1 Med(C/U)':>12} | "
        f"{'Full Med(C/U)':>14} | {'24m P/F/W':>18} | {'FnBr':>5} | {'BDS90':>5} | {'4T/5T Ruin':>11}"
    )
    for cid, obj in res["candidates"].items():
        m = obj["ftmo_std_10k_bf_1x"]
        r4 = obj["bankroll_4_ticket_bf_1x"]["sequential_ruin_pct"]
        r5 = obj["bankroll_5_ticket_bf_1x"]["sequential_ruin_pct"]
        bds90 = m["best_day_share"]["eval_max"]["p90_pct"]
        mark = "*" if cid == win_id else " "
        print(
            f"{mark}{cid:<25} | {m['ev_per_fee_npv24']:+6.2f}x | "
            f"{m['ev_npv_24m_usd']:+6.1f}/{m['ev_npv_24m_vnd_tr']:+5.2f}tr | "
            f"{m['p1_med_pass_cal_days_cond']:5.0f}/{m['p1_med_pass_cal_days_uncond']:5.0f}d | "
            f"{m['full_med_pass_cal_days_cond']:5.0f}/{m['full_med_pass_cal_days_uncond']:5.0f}d | "
            f"{m['pass_24m_pct']:5.1f}/{m['fail_24m_pct']:4.1f}/{m['pending_24m_pct']:4.1f}% | "
            f"{m['funded_12m_breach_pct']:4.2f}% | {bds90:4.1f}% | {r4:4.2f}/{r5:4.2f}%"
        )

    print("\n=== 7 SSOT VN-AVAILABLE SKUs (WINNER vs BASELINE FN1X) ===")
    for sku_id in res["target_skus"]:
        s = res["sku_matrix"][sku_id]
        w = s["winner_promo_1x"]
        b = s["baseline_fn1x_promo_1x"]
        print(
            f"  {sku_id:<22} | Fee={w['effective_fee_usd']:6.2f} | "
            f"Win EV/Fee={w['ev_per_fee_npv24']:+6.2f}x (Base {b['ev_per_fee_npv24']:+6.2f}x) | "
            f"FullMed(C/U)={w['full_med_pass_cal_days_cond']:5.0f}/{w['full_med_pass_cal_days_uncond']:5.0f}d "
            f"(Base {b['full_med_pass_cal_days_cond']:5.0f}/{b['full_med_pass_cal_days_uncond']:5.0f}d) | "
            f"24m P/F/W={w['pass_24m_pct']:5.1f}/{w['fail_24m_pct']:4.1f}/{w['pending_24m_pct']:4.1f}% | "
            f"FnBr={w['funded_12m_breach_pct']:4.2f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
