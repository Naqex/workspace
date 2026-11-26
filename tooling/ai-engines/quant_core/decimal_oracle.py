"""ZERO-shared-import independent Decimal accounting oracle for prop lifecycle verification.

STRICT ISOLATION GUARANTEE:
This module imports ONLY Python standard-library modules (`dataclasses`, `decimal`, `typing`).
It MUST NEVER import `prop_sim`, `prop_engine`, `schemas`, `numpy`, or `numba`.
It replays daily `(net, dd, flg, open_positions)` sequences using exact `decimal.Decimal`
arithmetic from first principles and verifies penny-exact parity against any simulator output.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_ZERO = Decimal("0")
_ONE = Decimal("1")
_BASE_SCALE_REF = Decimal("10000")
_EPS = Decimal("1e-9")
_PAYOUT_MIN_EPS = Decimal("1e-6")
_PAUSE_SLIP = Decimal("0.001")
_EA_STOP_SLIP = Decimal("0.0025")
_CENT = Decimal("0.01")


def _dec(val: Decimal | int | float | str) -> Decimal:
    if isinstance(val, bool):
        raise ValueError("bool is not a valid Decimal numeric value")
    if isinstance(val, Decimal):
        out = val
    else:
        out = Decimal(str(val))
    if not out.is_finite():
        raise ValueError(f"non-finite Decimal value: {val!r}")
    return out


def _quantize_cent(val: Decimal) -> Decimal:
    return val.quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class DailyObservation:
    """Single day's unscaled 10K-reference PnL, intraday DD, trade flag, and EOD open positions."""

    net: Decimal
    dd: Decimal
    flg: int
    open_positions: int = 0
    net_core: Decimal | None = None
    dd_core: Decimal | None = None
    flg_core: int | None = None
    open_positions_core: int | None = None

    @classmethod
    def from_tuple(cls, row: tuple[Decimal | int | float | str, ...]) -> DailyObservation:
        if len(row) == 3:
            net_v, dd_v, flg_v = row
            return cls(net=_dec(net_v), dd=_dec(dd_v), flg=int(flg_v), open_positions=0)
        if len(row) == 4:
            net_v, dd_v, flg_v, open_v = row
            return cls(net=_dec(net_v), dd=_dec(dd_v), flg=int(flg_v), open_positions=int(open_v))
        raise ValueError(f"expected 3-tuple or 4-tuple (net, dd, flg[, open_positions]), got len {len(row)}")


@dataclass(frozen=True, slots=True)
class DecimalOracleParams:
    """Independent exact-Decimal contract & risk-brake specification."""

    steps: int = 2
    capital_usd: Decimal = Decimal("10000")
    fee_usd: Decimal = Decimal("98.61")
    fee_refund_ratio: Decimal = Decimal("1")
    p1_target_frac: Decimal = Decimal("0.10")
    p2_target_frac: Decimal = Decimal("0.05")
    daily_loss_limit_frac: Decimal = Decimal("0.05")
    static_loss_limit_frac: Decimal = Decimal("0.10")
    daily_pause_only: bool = False
    min_days: int = 4
    min_prof_day_frac: Decimal = Decimal("0")
    funded_cap_mult: Decimal = Decimal("1")
    payout_split_frac: Decimal = Decimal("0.80")
    payout_cycle_days: int = 10
    max_retries: int = 2
    retry_discounts: tuple[Decimal, ...] = (Decimal("1"),)
    p1_mult: Decimal = Decimal("4.00")
    p2_mult: Decimal = Decimal("3.50")
    funded_mult: Decimal = Decimal("1.25")
    amber_dd_frac: Decimal = Decimal("0.035")
    amber_mult: Decimal = Decimal("0.65")
    red_dd_frac: Decimal = Decimal("0.060")
    red_mult: Decimal = Decimal("0.40")
    ea_daily_stop_frac: Decimal = Decimal("0.035")
    p1_profit_lock_trigger_frac: Decimal = Decimal("0.070")
    p1_profit_lock_mult: Decimal = Decimal("2.50")
    p2_profit_lock_trigger_frac: Decimal = Decimal("0.035")
    p2_profit_lock_mult: Decimal = Decimal("1.75")
    funded_profit_lock_trigger_frac: Decimal = Decimal("0")
    funded_profit_lock_mult: Decimal = Decimal("1.25")
    require_flat_for_pass: bool = True


@dataclass(frozen=True, slots=True)
class OracleDayTrace:
    day: int
    stage_before: int
    stage_after: int
    mult: Decimal
    raw_net: Decimal
    raw_dd: Decimal
    eff_net: Decimal
    eff_dd: Decimal
    breached: bool
    bal_after: Decimal
    fees_cum: Decimal
    payouts_cum: Decimal
    event: str


@dataclass(frozen=True, slots=True)
class OracleReplayResult:
    pass_day: int
    first_payout_day: int
    dead_day: int
    final_stage: int
    cf12_usd: Decimal
    cf_terminal_usd: Decimal
    max_oop_usd: Decimal
    total_fees_usd: Decimal
    total_payouts_usd: Decimal
    final_balance_usd: Decimal
    breached_p1: bool
    breached_p2: bool
    breached_funded: bool
    attempts: int
    trace: tuple[OracleDayTrace, ...]


def replay_prop_lifecycle_decimal(
    days: Sequence[DailyObservation | tuple[Decimal | int | float | str, ...]],
    params: DecimalOracleParams,
) -> OracleReplayResult:
    """Independently replay a daily observation stream using exact `Decimal` arithmetic."""
    cap = _dec(params.capital_usd)
    fee = _dec(params.fee_usd)
    fee_refund_ratio = _dec(params.fee_refund_ratio)
    p1_target = _dec(params.p1_target_frac)
    p2_target = _dec(params.p2_target_frac)
    daily_lim = _dec(params.daily_loss_limit_frac)
    static_lim = _dec(params.static_loss_limit_frac)
    min_prof_day = _dec(params.min_prof_day_frac)
    funded_cap_mult = _dec(params.funded_cap_mult)
    split = _dec(params.payout_split_frac)
    retry_disc = tuple(_dec(x) for x in (params.retry_discounts or (_ONE,)))
    p1_mult = _dec(params.p1_mult)
    p2_mult = _dec(params.p2_mult)
    funded_mult = _dec(params.funded_mult)
    amber_dd = _dec(params.amber_dd_frac)
    amber_mult = _dec(params.amber_mult)
    red_dd = _dec(params.red_dd_frac)
    red_mult = _dec(params.red_mult)
    ea_daily_stop = _dec(params.ea_daily_stop_frac)
    p1_pl_trig = _dec(params.p1_profit_lock_trigger_frac)
    p1_pl_mult = _dec(params.p1_profit_lock_mult)
    p2_pl_trig = _dec(params.p2_profit_lock_trigger_frac)
    p2_pl_mult = _dec(params.p2_profit_lock_mult)
    funded_pl_trig = _dec(params.funded_profit_lock_trigger_frac)
    funded_pl_mult = _dec(params.funded_profit_lock_mult)

    if type(params.steps) is not int or params.steps not in (0, 1, 2):
        raise ValueError(f"steps must be 0, 1, or 2, got {params.steps!r}")
    if type(params.min_days) is not int or params.min_days < 0:
        raise ValueError("min_days must be a non-negative integer")
    if type(params.payout_cycle_days) is not int or params.payout_cycle_days < 1:
        raise ValueError("payout_cycle_days must be an integer >= 1")
    if type(params.max_retries) is not int or params.max_retries < 0:
        raise ValueError("max_retries must be a non-negative integer")
    if cap <= _ZERO:
        raise ValueError("capital_usd must be > 0")
    if funded_cap_mult <= _ZERO:
        raise ValueError("funded_cap_mult must be > 0")
    if fee < _ZERO:
        raise ValueError("fee_usd must be >= 0")
    if not (_ZERO <= fee_refund_ratio <= _ONE):
        raise ValueError("fee_refund_ratio must be in [0, 1]")
    if p1_target < _ZERO or p2_target < _ZERO:
        raise ValueError("p1_target_frac and p2_target_frac must be >= 0")
    if not (_ZERO < daily_lim <= static_lim <= _ONE):
        raise ValueError("must satisfy 0 < daily_loss_limit_frac <= static_loss_limit_frac <= 1")
    if not (_ZERO <= min_prof_day <= _ONE):
        raise ValueError("min_prof_day_frac must be in [0, 1]")
    if not (_ZERO <= split <= _ONE):
        raise ValueError("payout_split_frac must be in [0, 1]")
    if any(x < _ZERO for x in retry_disc):
        raise ValueError("retry_discounts must be >= 0")
    if any(x <= _ZERO for x in (p1_mult, p2_mult, funded_mult, p1_pl_mult, p2_pl_mult, funded_pl_mult)):
        raise ValueError("phase and profit-lock multipliers must be > 0")
    if not (_ZERO < amber_dd < red_dd <= _ONE):
        raise ValueError("must satisfy 0 < amber_dd_frac < red_dd_frac <= 1")
    if not (_ZERO < red_mult <= amber_mult <= _ONE):
        raise ValueError("must satisfy 0 < red_mult <= amber_mult <= 1")
    if ea_daily_stop < _ZERO or p1_pl_trig < _ZERO or p2_pl_trig < _ZERO or funded_pl_trig < _ZERO:
        raise ValueError("ea_daily_stop_frac and profit-lock trigger fracs must be >= 0")

    scale = cap / _BASE_SCALE_REF
    p1_goal = cap * (_ONE + p1_target)
    p2_goal = cap * (_ONE + p2_target)

    stage = 1 if params.steps >= 1 else 3
    bal = cap * funded_cap_mult if stage == 3 else cap
    tdays = 0
    attempts = 1
    fees = fee
    refunded = False
    payouts = _ZERO
    cycle_d = 0
    max_oop = fee
    cf12 = _ZERO
    f_pass = -1
    f_pay = -1
    f_dead = -1
    had_br1 = False
    had_br2 = False
    had_brf = False
    trace: list[OracleDayTrace] = []

    for d, raw_item in enumerate(days):
        obs = raw_item if isinstance(raw_item, DailyObservation) else DailyObservation.from_tuple(raw_item)
        obs_net = _dec(obs.net)
        obs_dd = _dec(obs.dd)
        if obs_dd < _ZERO:
            raise ValueError(f"day {d + 1}: obs.dd must be >= 0, got {obs_dd}")
        if type(obs.open_positions) is not int or obs.open_positions < 0:
            raise ValueError(f"day {d + 1}: obs.open_positions must be a non-negative integer")
        obs_net_core = obs_net if obs.net_core is None else _dec(obs.net_core)
        obs_dd_core = obs_dd if obs.dd_core is None else _dec(obs.dd_core)
        if obs_dd_core < _ZERO:
            raise ValueError(f"day {d + 1}: obs.dd_core must be >= 0, got {obs_dd_core}")
        obs_open_core = obs.open_positions if obs.open_positions_core is None else obs.open_positions_core
        if type(obs_open_core) is not int or obs_open_core < 0:
            raise ValueError(f"day {d + 1}: obs.open_positions_core must be a non-negative integer")

        stage_before = stage
        if stage == 0:
            if d + 1 == 252:
                cf12 = payouts - fees
            trace.append(
                OracleDayTrace(
                    day=d + 1,
                    stage_before=0,
                    stage_after=0,
                    mult=_ZERO,
                    raw_net=_ZERO,
                    raw_dd=_ZERO,
                    eff_net=_ZERO,
                    eff_dd=_ZERO,
                    breached=False,
                    bal_after=bal,
                    fees_cum=fees,
                    payouts_cum=payouts,
                    event="DEAD_NO_TRADE",
                )
            )
            continue

        cur_base = cap * funded_cap_mult if stage == 3 else cap
        eq_pct = (bal - cur_base) / cur_base

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
        if stage == 1 and p1_pl_trig > _ZERO and eq_pct >= p1_pl_trig:
            pl_mult = min(pl_mult, p1_pl_mult)
        elif stage == 2 and p2_pl_trig > _ZERO and eq_pct >= p2_pl_trig:
            pl_mult = min(pl_mult, p2_pl_mult)
        elif stage == 3 and funded_pl_trig > _ZERO and eq_pct >= funded_pl_trig:
            pl_mult = min(pl_mult, funded_pl_mult)

        mult = min(dd_brake_mult, pl_mult)
        eff_scale = scale * (funded_cap_mult if stage == 3 else _ONE)

        if use_p1_book:
            src_net = obs_net
            src_dd = obs_dd
            src_flg = obs.flg
            src_open = obs.open_positions
        else:
            src_net = obs_net_core
            src_dd = obs_dd_core
            src_flg = obs.flg if obs.flg_core is None else obs.flg_core
            src_open = obs_open_core

        raw_net = src_net * eff_scale * mult
        raw_dd = src_dd * eff_scale * mult

        cur_daily_cap = cur_base * daily_lim
        cur_static_floor = cur_base * (_ONE - static_lim)
        cur_ea_cut = cur_base * ea_daily_stop if ea_daily_stop > _ZERO else Decimal("1e18")

        eff_dd = raw_dd
        eff_net = raw_net

        if params.daily_pause_only:
            breached = (bal - raw_dd) <= cur_static_floor + _EPS
            if (not breached) and raw_dd >= cur_daily_cap:
                eff_dd = min(raw_dd, cur_daily_cap + cur_base * _PAUSE_SLIP)
                eff_net = min(raw_net, -cur_daily_cap)
                breached = (bal - eff_dd) <= cur_static_floor + _EPS
        else:
            breached = (raw_dd >= cur_daily_cap - _EPS) or ((bal - raw_dd) <= cur_static_floor + _EPS)
            if (not breached) and ea_daily_stop > _ZERO and raw_dd > cur_ea_cut:
                eff_dd = min(raw_dd, cur_ea_cut + cur_base * _EA_STOP_SLIP)
                eff_net = min(raw_net, -cur_ea_cut)
                breached = (eff_dd >= cur_daily_cap - _EPS) or ((bal - eff_dd) <= cur_static_floor + _EPS)

        event = "TRADE"
        if breached:
            if stage == 1:
                had_br1 = True
            elif stage == 2:
                had_br2 = True
            elif stage == 3:
                had_brf = True

            if attempts <= params.max_retries:
                disc_idx = min(attempts - 1, len(retry_disc) - 1)
                attempts += 1
                fees += fee * retry_disc[disc_idx]
                stage = 1 if params.steps >= 1 else 3
                bal = cap * funded_cap_mult if stage == 3 else cap
                tdays = 0
                refunded = False
                cycle_d = 0
                event = "BREACH_RETRY"
            else:
                stage = 0
                bal = _ZERO
                tdays = 0
                cycle_d = 0
                if f_dead < 0:
                    f_dead = d + 1
                event = "BREACH_DEAD"
        else:
            bal += eff_net
            if min_prof_day > _ZERO:
                if eff_net >= cur_base * min_prof_day - _EPS:
                    tdays += 1
            elif src_flg != 0:
                tdays += 1

            is_flat_ok = (not params.require_flat_for_pass) or (src_open == 0)

            if stage == 1 and bal >= p1_goal - _EPS and tdays >= params.min_days and is_flat_ok:
                if params.steps == 1:
                    stage = 3
                    bal = cap * funded_cap_mult
                    tdays = 0
                    cycle_d = 0
                    if f_pass < 0:
                        f_pass = d + 1
                    event = "PASS_TO_FUNDED"
                else:
                    stage = 2
                    bal = cap
                    tdays = 0
                    event = "PASS_P1_TO_P2"
            elif stage == 2 and bal >= p2_goal - _EPS and tdays >= params.min_days and is_flat_ok:
                stage = 3
                bal = cap * funded_cap_mult
                tdays = 0
                cycle_d = 0
                if f_pass < 0:
                    f_pass = d + 1
                event = "PASS_P2_TO_FUNDED"
            elif stage == 3:
                cycle_d += 1
                if cycle_d >= params.payout_cycle_days:
                    if bal > cur_base + _PAYOUT_MIN_EPS:
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
                            event = "PAYOUT"
                        else:
                            event = "PAYOUT_DEFERRED_OPEN_POS"
                    else:
                        cycle_d = 0

        if fees - payouts > max_oop:
            max_oop = fees - payouts
        if d + 1 == 252:
            cf12 = payouts - fees

        trace.append(
            OracleDayTrace(
                day=d + 1,
                stage_before=stage_before,
                stage_after=stage,
                mult=mult,
                raw_net=raw_net,
                raw_dd=raw_dd,
                eff_net=eff_net,
                eff_dd=eff_dd,
                breached=breached,
                bal_after=bal,
                fees_cum=fees,
                payouts_cum=payouts,
                event=event,
            )
        )

    return OracleReplayResult(
        pass_day=f_pass,
        first_payout_day=f_pay,
        dead_day=f_dead,
        final_stage=stage,
        cf12_usd=cf12,
        cf_terminal_usd=payouts - fees,
        max_oop_usd=max_oop,
        total_fees_usd=fees,
        total_payouts_usd=payouts,
        final_balance_usd=bal,
        breached_p1=had_br1,
        breached_p2=had_br2,
        breached_funded=had_brf,
        attempts=attempts,
        trace=tuple(trace),
    )


def assert_penny_parity(
    oracle: OracleReplayResult,
    sim_result: Mapping[str, int | float | bool | Decimal],
    *,
    cent_tolerance: Decimal = Decimal("0.01"),
) -> None:
    """Assert exact discrete state + penny-exact USD parity between oracle and simulator."""
    diffs: list[str] = []

    exact_fields = (
        ("pass_day", oracle.pass_day),
        ("first_payout_day", oracle.first_payout_day),
        ("dead_day", oracle.dead_day),
        ("final_stage", oracle.final_stage),
        ("breached_p1", oracle.breached_p1),
        ("breached_p2", oracle.breached_p2),
        ("breached_funded", oracle.breached_funded),
        ("attempts", oracle.attempts),
    )
    for key, expected in exact_fields:
        actual = sim_result.get(key)
        if actual != expected:
            diffs.append(f"{key}: oracle={expected!r} vs sim={actual!r}")

    money_fields = (
        ("cf12_usd", oracle.cf12_usd),
        ("cf_terminal_usd", oracle.cf_terminal_usd),
        ("max_oop_usd", oracle.max_oop_usd),
        ("total_fees_usd", oracle.total_fees_usd),
        ("total_payouts_usd", oracle.total_payouts_usd),
        ("final_balance_usd", oracle.final_balance_usd),
    )
    tol = _dec(cent_tolerance)
    for key, expected in money_fields:
        raw_actual = sim_result.get(key)
        if raw_actual is None or isinstance(raw_actual, bool):
            diffs.append(f"{key}: missing or invalid sim value {raw_actual!r}")
            continue
        actual_dec = _dec(raw_actual)
        err = abs(expected - actual_dec)
        if err > tol or abs(_quantize_cent(expected) - _quantize_cent(actual_dec)) > tol:
            diffs.append(f"{key}: oracle={expected:.6f} vs sim={actual_dec:.6f} (diff={err:.6f} > {tol})")

    if diffs:
        raise AssertionError("Decimal oracle parity mismatch:\n  - " + "\n  - ".join(diffs))


__all__ = [
    "DailyObservation",
    "DecimalOracleParams",
    "OracleDayTrace",
    "OracleReplayResult",
    "assert_penny_parity",
    "replay_prop_lifecycle_decimal",
]
