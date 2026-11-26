"""Single-source Numba + pure-Python prop-challenge lifecycle simulator.

Fixes BOTH critical defects in legacy `quant_factory/prop_engine.py`:
  1. Checks raw daily and static breaches BEFORE applying `ea_daily_stop` cut
     (`cur_base * 0.0025` slippage cushion), while accurately preserving
     `daily_pause_only` mode (daily pause caps day loss without breaching daily limit,
     still checking static floor strictly).
  2. Eliminates the infinite-mulligan bug: when breached and `attempts > max_retries`,
     transitions to `stage = 0` (DEAD — zero trading on subsequent days) while STILL
     recording `cf12[b] = payouts - fees` cleanly at `d + 1 == 252`.

Also supports:
  - Relative `AMBER/RED` drawdown scaling (`phase_mult * amber_mult` / `phase_mult * red_mult`)
  - Per-phase `ProfitLock` step-down (`min(dd_brake_mult, profit_lock_mult)`)
  - `require_flat_for_pass=True` (never passes a phase or pays out while `open_positions > 0`)
  - Identical Numba-JIT (`@njit(cache=True)`) and pure-Python execution backends
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numba import njit
from numpy.typing import NDArray

STAGE_DEAD: int = 0
STAGE_P1: int = 1
STAGE_P2: int = 2
STAGE_FUNDED: int = 3

_EPS: float = 1e-9


@dataclass(frozen=True, slots=True)
class PropSimParams:
    """Declarative parameter bundle for `simulate_lifecycle`."""

    steps: int = 2
    capital_usd: float = 10000.0
    fee_usd: float = 98.61
    fee_refund_ratio: float = 1.0
    p1_target_frac: float = 0.10
    p2_target_frac: float = 0.05
    daily_loss_limit_frac: float = 0.05
    static_loss_limit_frac: float = 0.10
    daily_pause_only: bool = False
    min_days: int = 4
    min_prof_day_frac: float = 0.0
    funded_cap_mult: float = 1.0
    payout_split_frac: float = 0.80
    payout_cycle_days: int = 10
    max_retries: int = 2
    retry_discounts: tuple[float, ...] = (1.0,)
    p1_mult: float = 4.00
    p2_mult: float = 3.50
    funded_mult: float = 1.25
    amber_dd_frac: float = 0.035
    amber_mult: float = 0.65
    red_dd_frac: float = 0.060
    red_mult: float = 0.40
    ea_daily_stop_frac: float = 0.035
    p1_profit_lock_trigger_frac: float = 0.070
    p1_profit_lock_mult: float = 2.50
    p2_profit_lock_trigger_frac: float = 0.035
    p2_profit_lock_mult: float = 1.75
    funded_profit_lock_trigger_frac: float = 0.0
    funded_profit_lock_mult: float = 1.25
    require_flat_for_pass: bool = True


@dataclass(frozen=True, slots=True)
class PropSimOutputs:
    """Per-path outputs from `simulate_lifecycle`."""

    pass_days: NDArray[np.int32]
    pay1_days: NDArray[np.int32]
    dead_days: NDArray[np.int32]
    final_stage: NDArray[np.int8]
    cf12: NDArray[np.float64]
    cf_terminal: NDArray[np.float64]
    max_oop: NDArray[np.float64]
    total_fees: NDArray[np.float64]
    total_payouts: NDArray[np.float64]
    final_balance: NDArray[np.float64]
    br1: NDArray[np.int8]
    br2: NDArray[np.int8]
    brf: NDArray[np.int8]
    attempts: NDArray[np.int32]


def _simulate_lifecycle_impl(
    idx_matrix: NDArray[np.int32],
    nets_p1: NDArray[np.float64],
    dds_p1: NDArray[np.float64],
    flg_p1: NDArray[np.int8],
    open_pos_p1: NDArray[np.int32],
    nets_core: NDArray[np.float64],
    dds_core: NDArray[np.float64],
    flg_core: NDArray[np.int8],
    open_pos_core: NDArray[np.int32],
    steps: int,
    cap: float,
    fee: float,
    fee_refund_ratio: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    static_lim: float,
    daily_pause_only: bool,
    min_days: int,
    min_prof_day: float,
    funded_cap_mult: float,
    split: float,
    payout_cycle: int,
    max_retries: int,
    retry_disc: NDArray[np.float64],
    p1_mult: float,
    p2_mult: float,
    funded_mult: float,
    amber_dd: float,
    amber_mult: float,
    red_dd: float,
    red_mult: float,
    ea_daily_stop: float,
    p1_pl_trig: float,
    p1_pl_mult: float,
    p2_pl_trig: float,
    p2_pl_mult: float,
    funded_pl_trig: float,
    funded_pl_mult: float,
    require_flat_for_pass: bool,
) -> tuple[
    NDArray[np.int32],
    NDArray[np.int32],
    NDArray[np.int32],
    NDArray[np.int8],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.int8],
    NDArray[np.int8],
    NDArray[np.int8],
    NDArray[np.int32],
]:
    n_paths = idx_matrix.shape[0]
    horizon = idx_matrix.shape[1]
    scale = cap / 10000.0
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)

    pass_days = np.full(n_paths, -1, dtype=np.int32)
    pay1_days = np.full(n_paths, -1, dtype=np.int32)
    dead_days = np.full(n_paths, -1, dtype=np.int32)
    final_stage = np.zeros(n_paths, dtype=np.int8)
    cf12 = np.zeros(n_paths, dtype=np.float64)
    cf_terminal = np.zeros(n_paths, dtype=np.float64)
    max_oop_arr = np.zeros(n_paths, dtype=np.float64)
    total_fees_arr = np.zeros(n_paths, dtype=np.float64)
    total_payouts_arr = np.zeros(n_paths, dtype=np.float64)
    final_bal_arr = np.zeros(n_paths, dtype=np.float64)
    br1 = np.zeros(n_paths, dtype=np.int8)
    br2 = np.zeros(n_paths, dtype=np.int8)
    brf = np.zeros(n_paths, dtype=np.int8)
    tix = np.ones(n_paths, dtype=np.int32)

    n_disc = retry_disc.shape[0]

    for b in range(n_paths):
        stage = 1 if steps >= 1 else 3
        bal = cap * funded_cap_mult if stage == 3 else cap
        tdays = 0
        attempts = 1
        fees = fee
        refunded = False
        payouts = 0.0
        cycle_d = 0
        max_oop = fee
        f_pass = -1
        f_pay = -1
        f_dead = -1
        had_br1 = 0
        had_br2 = 0
        had_brf = 0

        for d in range(horizon):
            if stage == 0:
                # DEAD: zero trading on subsequent days, but STILL record cf12 cleanly at day 252!
                if d + 1 == 252:
                    cf12[b] = payouts - fees
                continue

            src = idx_matrix[b, d]
            cur_base = cap * funded_cap_mult if stage == 3 else cap
            eq_pct = (bal - cur_base) / cur_base

            # Phase base mult + RELATIVE AMBER/RED brake + ProfitLock
            phase_mult = p1_mult if stage == 1 else (p2_mult if stage == 2 else funded_mult)
            dd_brake_mult = phase_mult
            use_p1_book = stage == 1 and eq_pct > -amber_dd
            if eq_pct <= -red_dd:
                dd_brake_mult = phase_mult * red_mult
                use_p1_book = False
            elif eq_pct <= -amber_dd:
                dd_brake_mult = phase_mult * amber_mult
                use_p1_book = False

            pl_mult = phase_mult
            if stage == 1 and p1_pl_trig > 0.0 and eq_pct >= p1_pl_trig:
                if p1_pl_mult < pl_mult:
                    pl_mult = p1_pl_mult
            elif stage == 2 and p2_pl_trig > 0.0 and eq_pct >= p2_pl_trig:
                if p2_pl_mult < pl_mult:
                    pl_mult = p2_pl_mult
            elif stage == 3 and funded_pl_trig > 0.0 and eq_pct >= funded_pl_trig:
                if funded_pl_mult < pl_mult:
                    pl_mult = funded_pl_mult

            m = dd_brake_mult if dd_brake_mult < pl_mult else pl_mult
            eff_scale = scale * (funded_cap_mult if stage == 3 else 1.0)

            if use_p1_book:
                raw_net = nets_p1[src] * eff_scale * m
                raw_dd = dds_p1[src] * eff_scale * m
                flg = flg_p1[src]
                open_pos = open_pos_p1[src]
            else:
                raw_net = nets_core[src] * eff_scale * m
                raw_dd = dds_core[src] * eff_scale * m
                flg = flg_core[src]
                open_pos = open_pos_core[src]

            cur_daily_cap = cur_base * daily_lim
            cur_static_floor = cur_base * (1.0 - static_lim)
            cur_ea_cut = cur_base * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

            eff_dd = raw_dd
            eff_net = raw_net

            if daily_pause_only:
                # Daily pause mode: raw static breach checked first; daily cap pauses without breaching daily rule
                breached = (bal - raw_dd) <= cur_static_floor + 1e-9
                if (not breached) and raw_dd >= cur_daily_cap:
                    cap_dd = cur_daily_cap + cur_base * 0.001
                    eff_dd = raw_dd if raw_dd < cap_dd else cap_dd
                    eff_net = raw_net if raw_net < -cur_daily_cap else -cur_daily_cap
                    breached = (bal - eff_dd) <= cur_static_floor + 1e-9
            else:
                # BUG (a) FIX: Check RAW daily & static breaches BEFORE applying ea_daily_stop cut!
                breached = (raw_dd >= cur_daily_cap - 1e-9) or ((bal - raw_dd) <= cur_static_floor + 1e-9)
                if (not breached) and ea_daily_stop > 0.0 and raw_dd > cur_ea_cut:
                    cut_dd = cur_ea_cut + cur_base * 0.0025
                    eff_dd = raw_dd if raw_dd < cut_dd else cut_dd
                    eff_net = raw_net if raw_net < -cur_ea_cut else -cur_ea_cut
                    breached = (eff_dd >= cur_daily_cap - 1e-9) or ((bal - eff_dd) <= cur_static_floor + 1e-9)

            if breached:
                if stage == 1:
                    had_br1 = 1
                elif stage == 2:
                    had_br2 = 1
                elif stage == 3:
                    had_brf = 1

                if attempts <= max_retries:
                    disc_idx = attempts - 1
                    if disc_idx >= n_disc:
                        disc_idx = n_disc - 1
                    attempts += 1
                    fees += fee * retry_disc[disc_idx]
                    stage = 1 if steps >= 1 else 3
                    bal = cap * funded_cap_mult if stage == 3 else cap
                    tdays = 0
                    refunded = False
                    cycle_d = 0
                else:
                    # BUG (b) FIX: Out of retries -> stage = 0 (DEAD), zero future trading!
                    stage = 0
                    bal = 0.0
                    tdays = 0
                    cycle_d = 0
                    if f_dead < 0:
                        f_dead = d + 1
            else:
                bal += eff_net
                if min_prof_day > 0.0:
                    if eff_net >= cur_base * min_prof_day - 1e-9:
                        tdays += 1
                elif flg != 0:
                    tdays += 1

                is_flat_ok = (not require_flat_for_pass) or (open_pos == 0)

                if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days and is_flat_ok:
                    if steps == 1:
                        stage = 3
                        bal = cap * funded_cap_mult
                        tdays = 0
                        cycle_d = 0
                        if f_pass < 0:
                            f_pass = d + 1
                    else:
                        stage = 2
                        bal = cap
                        tdays = 0
                elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days and is_flat_ok:
                    stage = 3
                    bal = cap * funded_cap_mult
                    tdays = 0
                    cycle_d = 0
                    if f_pass < 0:
                        f_pass = d + 1
                elif stage == 3:
                    cycle_d += 1
                    if cycle_d >= payout_cycle:
                        if bal > cur_base + 1e-6:
                            if is_flat_ok:
                                pay = (bal - cur_base) * split
                                if not refunded:
                                    pay += fee * fee_refund_ratio
                                    refunded = True
                                payouts += pay
                                if f_pay < 0:
                                    f_pay = d + 1
                                bal = cur_base
                                cycle_d = 0
                        else:
                            cycle_d = 0

            if fees - payouts > max_oop:
                max_oop = fees - payouts
            if d + 1 == 252:
                cf12[b] = payouts - fees

        pass_days[b] = f_pass
        pay1_days[b] = f_pay
        dead_days[b] = f_dead
        final_stage[b] = stage
        cf_terminal[b] = payouts - fees
        max_oop_arr[b] = max_oop
        total_fees_arr[b] = fees
        total_payouts_arr[b] = payouts
        final_bal_arr[b] = bal
        br1[b] = had_br1
        br2[b] = had_br2
        brf[b] = had_brf
        tix[b] = attempts

    return (
        pass_days,
        pay1_days,
        dead_days,
        final_stage,
        cf12,
        cf_terminal,
        max_oop_arr,
        total_fees_arr,
        total_payouts_arr,
        final_bal_arr,
        br1,
        br2,
        brf,
        tix,
    )


simulate_lifecycle_python = _simulate_lifecycle_impl
simulate_lifecycle_numba = njit(cache=True)(_simulate_lifecycle_impl)


def _check_finite_float(val: Any, name: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"{name} must be a finite float (not bool), got {type(val).__name__}")
    out = float(val)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite, got {val!r}")
    return out


def _check_strict_int(val: Any, name: str) -> int:
    if type(val) is not int:
        raise ValueError(f"{name} must be a strict int (not bool/float), got {type(val).__name__}")
    return val


def _validate_sim_params(params: PropSimParams) -> None:
    steps = _check_strict_int(params.steps, "steps")
    if steps not in (0, 1, 2):
        raise ValueError(f"steps must be 0, 1, or 2, got {steps}")
    if _check_strict_int(params.min_days, "min_days") < 0:
        raise ValueError("min_days must be >= 0")
    if _check_strict_int(params.payout_cycle_days, "payout_cycle_days") < 1:
        raise ValueError("payout_cycle_days must be >= 1")
    if _check_strict_int(params.max_retries, "max_retries") < 0:
        raise ValueError("max_retries must be >= 0")
    if type(params.daily_pause_only) is not bool:
        raise ValueError("daily_pause_only must be bool")
    if type(params.require_flat_for_pass) is not bool:
        raise ValueError("require_flat_for_pass must be bool")

    cap = _check_finite_float(params.capital_usd, "capital_usd")
    if cap <= 0.0:
        raise ValueError("capital_usd must be > 0")
    fcm = _check_finite_float(params.funded_cap_mult, "funded_cap_mult")
    if fcm <= 0.0:
        raise ValueError("funded_cap_mult must be > 0")
    fee = _check_finite_float(params.fee_usd, "fee_usd")
    if fee < 0.0:
        raise ValueError("fee_usd must be >= 0")
    frr = _check_finite_float(params.fee_refund_ratio, "fee_refund_ratio")
    if not (0.0 <= frr <= 1.0):
        raise ValueError("fee_refund_ratio must be in [0.0, 1.0]")

    p1t = _check_finite_float(params.p1_target_frac, "p1_target_frac")
    p2t = _check_finite_float(params.p2_target_frac, "p2_target_frac")
    if p1t < 0.0 or p2t < 0.0:
        raise ValueError("p1_target_frac and p2_target_frac must be >= 0")
    dlim = _check_finite_float(params.daily_loss_limit_frac, "daily_loss_limit_frac")
    slim = _check_finite_float(params.static_loss_limit_frac, "static_loss_limit_frac")
    if not (0.0 < dlim <= slim <= 1.0):
        raise ValueError("must satisfy 0 < daily_loss_limit_frac <= static_loss_limit_frac <= 1")
    mpd = _check_finite_float(params.min_prof_day_frac, "min_prof_day_frac")
    if not (0.0 <= mpd <= 1.0):
        raise ValueError("min_prof_day_frac must be in [0.0, 1.0]")
    split = _check_finite_float(params.payout_split_frac, "payout_split_frac")
    if not (0.0 <= split <= 1.0):
        raise ValueError("payout_split_frac must be in [0.0, 1.0]")

    for m_name, m_val in (
        ("p1_mult", params.p1_mult),
        ("p2_mult", params.p2_mult),
        ("funded_mult", params.funded_mult),
        ("p1_profit_lock_mult", params.p1_profit_lock_mult),
        ("p2_profit_lock_mult", params.p2_profit_lock_mult),
        ("funded_profit_lock_mult", params.funded_profit_lock_mult),
    ):
        if _check_finite_float(m_val, m_name) <= 0.0:
            raise ValueError(f"{m_name} must be > 0")

    add = _check_finite_float(params.amber_dd_frac, "amber_dd_frac")
    rdd = _check_finite_float(params.red_dd_frac, "red_dd_frac")
    amult = _check_finite_float(params.amber_mult, "amber_mult")
    rmult = _check_finite_float(params.red_mult, "red_mult")
    if not (0.0 < add < rdd <= 1.0):
        raise ValueError("must satisfy 0 < amber_dd_frac < red_dd_frac <= 1")
    if not (0.0 < rmult <= amult <= 1.0):
        raise ValueError("must satisfy 0 < red_mult <= amber_mult <= 1")
    if _check_finite_float(params.ea_daily_stop_frac, "ea_daily_stop_frac") < 0.0:
        raise ValueError("ea_daily_stop_frac must be >= 0")

    for t_name, t_val in (
        ("p1_profit_lock_trigger_frac", params.p1_profit_lock_trigger_frac),
        ("p2_profit_lock_trigger_frac", params.p2_profit_lock_trigger_frac),
        ("funded_profit_lock_trigger_frac", params.funded_profit_lock_trigger_frac),
    ):
        if _check_finite_float(t_val, t_name) < 0.0:
            raise ValueError(f"{t_name} must be >= 0")

    for idx_d, disc in enumerate(params.retry_discounts):
        if _check_finite_float(disc, f"retry_discounts[{idx_d}]") < 0.0:
            raise ValueError(f"retry_discounts[{idx_d}] must be >= 0")


def simulate_lifecycle(
    idx_matrix: NDArray[np.int32],
    nets_p1: NDArray[np.float64],
    dds_p1: NDArray[np.float64],
    flg_p1: NDArray[np.int8],
    nets_core: NDArray[np.float64],
    dds_core: NDArray[np.float64],
    flg_core: NDArray[np.int8],
    params: PropSimParams,
    *,
    open_pos_p1: NDArray[np.int32] | None = None,
    open_pos_core: NDArray[np.int32] | None = None,
    backend: Literal["numba", "python"] = "numba",
) -> PropSimOutputs:
    """Run prop lifecycle simulation using either Numba JIT or pure-Python backend."""
    _validate_sim_params(params)

    raw_idx = np.asarray(idx_matrix)
    if raw_idx.dtype == np.bool_ or not np.issubdtype(raw_idx.dtype, np.integer):
        raise ValueError("idx_matrix must have an integer dtype (not bool/float)")
    if raw_idx.ndim != 2 or raw_idx.shape[0] < 1 or raw_idx.shape[1] < 1:
        raise ValueError(f"idx_matrix must be non-empty 2D, got shape {raw_idx.shape}")
    idx_c = np.ascontiguousarray(raw_idx, dtype=np.int32)

    for raw_name, raw_arr in (
        ("nets_p1", nets_p1),
        ("dds_p1", dds_p1),
        ("nets_core", nets_core),
        ("dds_core", dds_core),
    ):
        a = np.asarray(raw_arr)
        if a.dtype == np.bool_:
            raise ValueError(f"{raw_name} must be numeric, not bool")
        if a.ndim != 1 or a.shape[0] < 1:
            raise ValueError(f"{raw_name} must be non-empty 1D, got shape {a.shape}")

    n1 = np.ascontiguousarray(nets_p1, dtype=np.float64)
    d1 = np.ascontiguousarray(dds_p1, dtype=np.float64)
    f1 = np.ascontiguousarray(flg_p1, dtype=np.int8)
    op1 = (
        np.zeros(n1.shape[0], dtype=np.int32)
        if open_pos_p1 is None
        else np.ascontiguousarray(open_pos_p1, dtype=np.int32)
    )
    nc = np.ascontiguousarray(nets_core, dtype=np.float64)
    dc = np.ascontiguousarray(dds_core, dtype=np.float64)
    fc = np.ascontiguousarray(flg_core, dtype=np.int8)
    opc = (
        np.zeros(nc.shape[0], dtype=np.int32)
        if open_pos_core is None
        else np.ascontiguousarray(open_pos_core, dtype=np.int32)
    )
    rdisc = np.ascontiguousarray(params.retry_discounts if params.retry_discounts else (1.0,), dtype=np.float64)

    if not (n1.shape == d1.shape == f1.shape == op1.shape):
        raise ValueError("P1 arrays (nets_p1, dds_p1, flg_p1, open_pos_p1) must have identical 1D lengths")
    if not (nc.shape == dc.shape == fc.shape == opc.shape):
        raise ValueError("Core arrays (nets_core, dds_core, flg_core, open_pos_core) must have identical 1D lengths")

    for arr_name, arr in (("nets_p1", n1), ("dds_p1", d1), ("nets_core", nc), ("dds_core", dc), ("retry_disc", rdisc)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{arr_name} contains NaN or Inf")
    if np.any(d1 < 0.0) or np.any(dc < 0.0):
        raise ValueError("intraday drawdowns (dds_p1, dds_core) must be >= 0")
    if np.any(op1 < 0) or np.any(opc < 0):
        raise ValueError("open position counts (open_pos_p1, open_pos_core) must be >= 0")

    max_valid_idx = min(n1.shape[0], nc.shape[0])
    if int(np.min(idx_c)) < 0 or int(np.max(idx_c)) >= max_valid_idx:
        raise ValueError(
            f"idx_matrix entries must lie in [0, {max_valid_idx - 1}], got [{int(np.min(idx_c))}, {int(np.max(idx_c))}]"
        )

    if backend not in ("numba", "python"):
        raise ValueError(f"backend must be 'numba' or 'python', got {backend!r}")

    fn = simulate_lifecycle_numba if backend == "numba" else simulate_lifecycle_python
    res = fn(
        idx_c,
        n1,
        d1,
        f1,
        op1,
        nc,
        dc,
        fc,
        opc,
        int(params.steps),
        float(params.capital_usd),
        float(params.fee_usd),
        float(params.fee_refund_ratio),
        float(params.p1_target_frac),
        float(params.p2_target_frac),
        float(params.daily_loss_limit_frac),
        float(params.static_loss_limit_frac),
        bool(params.daily_pause_only),
        int(params.min_days),
        float(params.min_prof_day_frac),
        float(params.funded_cap_mult),
        float(params.payout_split_frac),
        int(params.payout_cycle_days),
        int(params.max_retries),
        rdisc,
        float(params.p1_mult),
        float(params.p2_mult),
        float(params.funded_mult),
        float(params.amber_dd_frac),
        float(params.amber_mult),
        float(params.red_dd_frac),
        float(params.red_mult),
        float(params.ea_daily_stop_frac),
        float(params.p1_profit_lock_trigger_frac),
        float(params.p1_profit_lock_mult),
        float(params.p2_profit_lock_trigger_frac),
        float(params.p2_profit_lock_mult),
        float(params.funded_profit_lock_trigger_frac),
        float(params.funded_profit_lock_mult),
        bool(params.require_flat_for_pass),
    )
    return PropSimOutputs(
        pass_days=res[0],
        pay1_days=res[1],
        dead_days=res[2],
        final_stage=res[3],
        cf12=res[4],
        cf_terminal=res[5],
        max_oop=res[6],
        total_fees=res[7],
        total_payouts=res[8],
        final_balance=res[9],
        br1=res[10],
        br2=res[11],
        brf=res[12],
        attempts=res[13],
    )


def simulate_single_path(
    nets: NDArray[np.float64] | list[float],
    dds: NDArray[np.float64] | list[float],
    flgs: NDArray[np.int8] | list[int],
    params: PropSimParams,
    *,
    open_positions: NDArray[np.int32] | list[int] | None = None,
    backend: Literal["numba", "python"] = "numba",
) -> dict[str, int | float | bool]:
    """Convenience single-path wrapper (identical P1/Core tape) for direct oracle parity checks."""
    n_arr = np.asarray(nets, dtype=np.float64)
    d_arr = np.asarray(dds, dtype=np.float64)
    f_arr = np.asarray(flgs, dtype=np.int8)
    op_arr = (
        np.zeros(n_arr.shape[0], dtype=np.int32)
        if open_positions is None
        else np.asarray(open_positions, dtype=np.int32)
    )
    idx = np.arange(n_arr.shape[0], dtype=np.int32)[None, :]
    out = simulate_lifecycle(
        idx,
        n_arr,
        d_arr,
        f_arr,
        n_arr,
        d_arr,
        f_arr,
        params,
        open_pos_p1=op_arr,
        open_pos_core=op_arr,
        backend=backend,
    )
    return {
        "pass_day": int(out.pass_days[0]),
        "first_payout_day": int(out.pay1_days[0]),
        "dead_day": int(out.dead_days[0]),
        "final_stage": int(out.final_stage[0]),
        "cf12_usd": float(out.cf12[0]),
        "cf_terminal_usd": float(out.cf_terminal[0]),
        "max_oop_usd": float(out.max_oop[0]),
        "total_fees_usd": float(out.total_fees[0]),
        "total_payouts_usd": float(out.total_payouts[0]),
        "final_balance_usd": float(out.final_balance[0]),
        "breached_p1": bool(out.br1[0] != 0),
        "breached_p2": bool(out.br2[0] != 0),
        "breached_funded": bool(out.brf[0] != 0),
        "attempts": int(out.attempts[0]),
    }


__all__ = [
    "PropSimOutputs",
    "PropSimParams",
    "STAGE_DEAD",
    "STAGE_FUNDED",
    "STAGE_P1",
    "STAGE_P2",
    "simulate_lifecycle",
    "simulate_lifecycle_numba",
    "simulate_lifecycle_python",
    "simulate_single_path",
]
