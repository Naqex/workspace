"""V3 explicit `flat_at_reset_verified` audit & `00:00` rollover floating-equity stress sensitivity.

Models exact firm daily-DD reset semantics across:
  - FTMO Standard (`balance`-anchored at `00:00 Europe/Prague`),
  - The5ers High Stakes (`max(balance, equity)` at `00:00 MT5 EET/EEST`),
  - IC Funded (`equity` at `00:00 GMT+2/+3` server reset, plus conservative `max(balance, equity)` bound).
"""

from __future__ import annotations

import calendar
import math
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np

from quant_factory.capital_optimizer.calibration import calibrate_safe_multipliers_for_rule
from quant_factory.capital_optimizer.catalog import (
    _daily_dd_anchor_code,
    _dd_type_code,
    _find_program_by_hint,
    get_program_tier,
)
from quant_factory.capital_optimizer.constants import (
    CORE7_IDS,
    DEFAULT_DISCOUNT_RATE,
    HOLDOUT_CUTOFF_DAY,
    HOLDOUT_CUTOFF_UTC_TS,
    ROLLOVER_ANCHOR_BALANCE,
    ROLLOVER_ANCHOR_EQUITY,
    ROLLOVER_ANCHOR_MAX_BAL_EQ,
    ROLLOVER_SHOCK_PROBE_LEVELS_PCT,
)
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache
from quant_factory.capital_optimizer.simulator import _simulate_single_ticket_rules_numba
from quant_factory.capital_optimizer.summaries import summarize_single_ticket_mc

_RESET_CLOCKS: tuple[tuple[str, str, int], ...] = (
    ("UTC_0000", "UTC", 0),
    ("PRAGUE_0000", "Europe/Prague", 1),
    ("MT5_EET_0000", "Europe/Athens", 2),
)


def _last_sunday_0100_utc(year: int, month: int) -> datetime:
    last_day = calendar.monthrange(year, month)[1]
    dt = datetime(year, month, last_day, 1, 0, tzinfo=UTC)
    days_back = (dt.weekday() + 1) % 7  # Sunday == 6 -> 0; Monday == 0 -> 1
    return dt - timedelta(days=days_back)


def _eu_dst_tz(dt_utc: datetime, base_offset_hours: int) -> timezone:
    """Pure-Python EU DST fallback (`CET/CEST` or `EET/EEST`) if `tzdata` is absent on Windows."""
    if base_offset_hours == 0:
        return UTC
    start_dst = _last_sunday_0100_utc(dt_utc.year, 3)
    end_dst = _last_sunday_0100_utc(dt_utc.year, 10)
    offset_h = base_offset_hours + (1 if start_dst <= dt_utc < end_dst else 0)
    return timezone(timedelta(hours=offset_h))


def _load_clock_tz(iana_name: str) -> ZoneInfo | None:
    if iana_name == "UTC":
        return None
    try:
        return ZoneInfo(iana_name)
    except ZoneInfoNotFoundError:
        return None


def _to_local_dt(ts_utc: int, tz_obj: ZoneInfo | None, base_offset_hours: int) -> datetime:
    dt_utc = datetime.fromtimestamp(int(ts_utc), UTC)
    if base_offset_hours == 0:
        return dt_utc
    if tz_obj is not None:
        return dt_utc.astimezone(tz_obj)
    return dt_utc.astimezone(_eu_dst_tz(dt_utc, base_offset_hours))


def _minutes_before_next_midnight(dt_local: datetime, tz_obj: ZoneInfo | None, base_offset_hours: int) -> float:
    next_date = dt_local.date() + timedelta(days=1)
    if base_offset_hours == 0:
        next_mid = datetime(next_date.year, next_date.month, next_date.day, 0, 0, tzinfo=UTC)
    elif tz_obj is not None:
        next_mid = datetime(next_date.year, next_date.month, next_date.day, 0, 0, tzinfo=tz_obj)
    else:
        approx_utc = dt_local.astimezone(UTC) + timedelta(hours=24 - dt_local.hour)
        next_mid = datetime(
            next_date.year,
            next_date.month,
            next_date.day,
            0,
            0,
            tzinfo=_eu_dst_tz(approx_utc, base_offset_hours),
        )
    return (next_mid.timestamp() - dt_local.timestamp()) / 60.0


def resolve_rollover_anchor_mode(program_tier: dict[str, Any]) -> tuple[int, str]:
    """Classify firm contract rollover DD rule into Balance, `max(balance, equity)`, or Equity."""
    raw = str(program_tier.get("daily_dd_anchor_raw") or program_tier.get("daily_dd_anchor") or "").lower()
    fid = str(program_tier.get("firm_id") or "").upper()
    norm = str(program_tier.get("daily_dd_anchor") or "").lower()
    if "max_" in raw or "balance_or_equity" in raw or "THE5ERS" in fid:
        return ROLLOVER_ANCHOR_MAX_BAL_EQ, "MAX_BALANCE_OR_EQUITY"
    if "equity_reset" in raw or "IC_FUNDED" in fid:
        return ROLLOVER_ANCHOR_EQUITY, "EQUITY_AT_RESET"
    if norm == "prev_day_balance":
        return ROLLOVER_ANCHOR_MAX_BAL_EQ, "MAX_BALANCE_OR_EQUITY"
    return ROLLOVER_ANCHOR_BALANCE, "BALANCE_ANCHORED"


def _require_finite_float(
    val: Any,
    name: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    strict_min: bool = False,
    strict_max: bool = False,
) -> float:
    if isinstance(val, bool):
        raise ValueError(f"INVALID_INPUT_BOOL: {name} must be finite float, got bool")
    try:
        x = float(val)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_INPUT_FLOAT: {name}={val!r}") from exc
    if not math.isfinite(x):
        raise ValueError(f"INVALID_INPUT_NON_FINITE: {name}={val!r}")
    if min_val is not None and (x <= min_val if strict_min else x < min_val):
        raise ValueError(f"INVALID_INPUT_RANGE: {name}={x} violates min {min_val}")
    if max_val is not None and (x >= max_val if strict_max else x > max_val):
        raise ValueError(f"INVALID_INPUT_RANGE: {name}={x} violates max {max_val}")
    return x


def _require_strict_int(val: Any, name: str, *, min_val: int | None = None) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(f"INVALID_INPUT_INT: {name} must be int (not bool), got {type(val).__name__}")
    if min_val is not None and val < min_val:
        raise ValueError(f"INVALID_INPUT_RANGE: {name}={val} < {min_val}")
    return int(val)


def verify_tapes_flat_at_reset(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    *,
    engine_ids: tuple[str, ...] = CORE7_IDS,
    min_safe_buffer_minutes: float = 15.0,
) -> dict[str, Any]:
    """Fail-closed audit verifying every M1 trade closes strictly before `00:00` UTC, Prague, and MT5 EET/EEST."""
    min_safe_buf = _require_finite_float(min_safe_buffer_minutes, "min_safe_buffer_minutes", min_val=0.0)
    clocks = [(label, _load_clock_tz(iana), off_h) for label, iana, off_h in _RESET_CLOCKS]

    total_trades = 0
    invalid_trades = 0
    crossing_by_clock: dict[str, int] = {lbl: 0 for lbl, _, _ in clocks}
    min_buf_by_clock: dict[str, float] = {lbl: float("inf") for lbl, _, _ in clocks}
    max_exit_hm_by_clock: dict[str, tuple[int, int]] = {lbl: (0, 0) for lbl, _, _ in clocks}
    per_engine: dict[str, dict[str, Any]] = {}
    violations_sample: list[dict[str, Any]] = []

    for eng in engine_ids:
        eng_map = tapes.get(eng) or {}
        eng_n = 0
        eng_invalid = 0
        eng_cross = {lbl: 0 for lbl, _, _ in clocks}
        eng_min_buf = {lbl: float("inf") for lbl, _, _ in clocks}
        eng_max_hm = {lbl: (0, 0) for lbl, _, _ in clocks}

        for dk, item in sorted(eng_map.items()):
            ds = str(dk)
            if ds >= HOLDOUT_CUTOFF_DAY or int(ds[:4]) > 2024:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION: tape {eng} contains holdout date {ds}")
            if not isinstance(item, tuple) or len(item) < 2:
                invalid_trades += 1
                eng_invalid += 1
                continue
            row, stamps = item[0], item[1]
            if not isinstance(row, dict):
                invalid_trades += 1
                eng_invalid += 1
                continue
            ent_raw = row.get("entry")
            ext_raw = row.get("exit")
            if ent_raw is None or ext_raw is None or isinstance(ent_raw, bool) or isinstance(ext_raw, bool):
                invalid_trades += 1
                eng_invalid += 1
                if len(violations_sample) < 10:
                    violations_sample.append({"engine": eng, "day": ds, "reason": "MISSING_ENTRY_OR_EXIT"})
                continue
            try:
                ent_f = float(ent_raw)
                ext_f = float(ext_raw)
            except (TypeError, ValueError):
                invalid_trades += 1
                eng_invalid += 1
                continue
            if (not math.isfinite(ent_f)) or (not math.isfinite(ext_f)) or ent_f <= 0 or ext_f < ent_f:
                invalid_trades += 1
                eng_invalid += 1
                if len(violations_sample) < 10:
                    violations_sample.append({"engine": eng, "day": ds, "reason": "INVALID_TIMESTAMP_ORDER"})
                continue
            ent_ts = int(ent_f)
            ext_ts = int(ext_f)
            if ent_ts >= HOLDOUT_CUTOFF_UTC_TS or ext_ts >= HOLDOUT_CUTOFF_UTC_TS:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION: tape {eng} day {ds} timestamp >= 2025-01-01Z")
            if stamps is not None and len(stamps) > 0:
                st_arr = np.asarray(stamps, dtype=np.int64)
                max_st = int(np.max(st_arr))
                min_st = int(np.min(st_arr))
                if max_st >= HOLDOUT_CUTOFF_UTC_TS:
                    raise ValueError(f"HOLDOUT_LOCK_VIOLATION: tape {eng} day {ds} stamp >= 2025-01-01Z")
                if min_st <= 0:
                    invalid_trades += 1
                    eng_invalid += 1
                    if len(violations_sample) < 10:
                        violations_sample.append({"engine": eng, "day": ds, "reason": "INVALID_STAMP_NON_POSITIVE"})
                    continue
                eff_ext_ts = max(ext_ts, max_st)
            else:
                eff_ext_ts = ext_ts

            total_trades += 1
            eng_n += 1
            for lbl, tz_obj, off_h in clocks:
                dt_ent = _to_local_dt(ent_ts, tz_obj, off_h)
                dt_ext = _to_local_dt(eff_ext_ts, tz_obj, off_h)
                crossed = dt_ext.date() != dt_ent.date()
                if crossed:
                    crossing_by_clock[lbl] += 1
                    eng_cross[lbl] += 1
                    buf_min = 0.0
                    if len(violations_sample) < 10:
                        violations_sample.append(
                            {
                                "engine": eng,
                                "day": ds,
                                "clock": lbl,
                                "entry_local": dt_ent.isoformat(),
                                "exit_local": dt_ext.isoformat(),
                                "reason": "CROSSED_MIDNIGHT_RESET",
                            }
                        )
                else:
                    buf_min = _minutes_before_next_midnight(dt_ext, tz_obj, off_h)
                if buf_min < min_buf_by_clock[lbl]:
                    min_buf_by_clock[lbl] = buf_min
                if buf_min < eng_min_buf[lbl]:
                    eng_min_buf[lbl] = buf_min
                hm = (dt_ext.hour, dt_ext.minute)
                if hm > max_exit_hm_by_clock[lbl]:
                    max_exit_hm_by_clock[lbl] = hm
                if hm > eng_max_hm[lbl]:
                    eng_max_hm[lbl] = hm

        per_engine[eng] = {
            "trades_checked": eng_n,
            "invalid_trades": eng_invalid,
            "crossing_by_clock": eng_cross,
            "min_buffer_minutes_by_clock": {
                lbl: (round(v, 1) if math.isfinite(v) else None) for lbl, v in eng_min_buf.items()
            },
            "max_exit_hm_by_clock": {lbl: f"{h:02d}:{m:02d}" for lbl, (h, m) in eng_max_hm.items()},
        }

    all_clocks_clean = total_trades > 0 and invalid_trades == 0 and all(cnt == 0 for cnt in crossing_by_clock.values())
    ftmo_ok = total_trades > 0 and invalid_trades == 0 and crossing_by_clock["PRAGUE_0000"] == 0
    mt5_ok = total_trades > 0 and invalid_trades == 0 and crossing_by_clock["MT5_EET_0000"] == 0

    tight_warnings: list[str] = []
    for lbl, buf_m in min_buf_by_clock.items():
        if math.isfinite(buf_m) and buf_m < min_safe_buf:
            tight_warnings.append(
                f"{lbl}: minimum flat buffer before 00:00 reset is only {buf_m:.1f} min "
                f"(< {min_safe_buf:.0f} min safety margin; summer DST rollover risk!)"
            )

    return {
        "flat_at_reset_verified": bool(all_clocks_clean),
        "flat_at_reset_verified_by_firm": {
            "FTMO": bool(ftmo_ok),
            "THE5ERS": bool(mt5_ok),
            "IC_FUNDED": bool(mt5_ok),
        },
        "holdout_rows_analysed": 0,
        "total_trades_checked": int(total_trades),
        "invalid_trades": int(invalid_trades),
        "crossing_trades_by_clock": crossing_by_clock,
        "min_buffer_minutes_by_clock": {
            lbl: (round(v, 1) if math.isfinite(v) else None) for lbl, v in min_buf_by_clock.items()
        },
        "max_exit_hm_by_clock": {lbl: f"{h:02d}:{m:02d}" for lbl, (h, m) in max_exit_hm_by_clock.items()},
        "tight_buffer_warnings": tight_warnings,
        "violations_sample": violations_sample,
        "per_engine": per_engine,
    }


def _resolve_the5ers_20k_target(
    catalog: dict[str, Any],
    the5ers_prog: dict[str, Any],
) -> list[tuple[str, dict[str, Any], float, str]]:
    """Build The5ers `5K`, `20K` (exact or legacy-vs-25K proxy), and live `25K` targets."""
    targets: list[tuple[str, dict[str, Any], float, str]] = []
    caps_avail = {float(t["capital_usd"]) for t in the5ers_prog["tiers"] if t.get("available_vn", True)}

    if 5_000.0 in caps_avail:
        _, m5 = get_program_tier(catalog, the5ers_prog["program_id"], 5_000.0)
        targets.append(("The5ers High Stakes 5K", m5, 5_000.0, "LIVE_CATALOG_TIER"))

    if 20_000.0 in caps_avail:
        _, m20 = get_program_tier(catalog, the5ers_prog["program_id"], 20_000.0)
        targets.append(("The5ers High Stakes 20K", m20, 20_000.0, "LIVE_CATALOG_TIER"))
    elif 5_000.0 in caps_avail:
        # 2026 live The5ers catalog replaced legacy 20K with 25K; run exact 20K M1 lot-rounded replay
        # under identical 5%/10% High Stakes Classic rules ($165 legacy fee) AND also include live 25K!
        _, m_base = get_program_tier(catalog, the5ers_prog["program_id"], 5_000.0)
        m20_legacy = {
            **m_base,
            "capital_usd": 20_000.0,
            "orig_usd": 165.0,
            "active_promo_usd": 165.0,
            "active_promo_pct": 0.0,
            "dd_daily_pct": 0.05,
            "dd_max_pct": 0.10,
        }
        targets.append(
            (
                "The5ers High Stakes 20K (Legacy SKU)",
                m20_legacy,
                20_000.0,
                "LEGACY_20K_SKU_MODEL_ASSUMPTION",
            )
        )
        if 25_000.0 in caps_avail:
            _, m25 = get_program_tier(catalog, the5ers_prog["program_id"], 25_000.0)
            targets.append(("The5ers High Stakes 25K (Live 2026 SKU)", m25, 25_000.0, "LIVE_CATALOG_TIER"))

    return targets


def run_rollover_reset_sensitivity(
    *,
    catalog: dict[str, Any],
    cache: ExactTierReplayCache,
    idx_matrix: np.ndarray,
    horizon_days: int,
    primary_var: str,
    use_promo_prices: bool,
    usd_vnd: float,
    card_fx_fee: float,
    flat_at_reset_audit: dict[str, Any],
    shock_levels_pct: tuple[float, ...] = ROLLOVER_SHOCK_PROBE_LEVELS_PCT,
    friction_mult: float = 1.00,
    calibrated_cache: dict[tuple[str, float, str, float], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare midnight rollover floating-equity stress across FTMO 10K, The5ers 5K/20K, and IC Funded 10K."""
    horizon_days = _require_strict_int(horizon_days, "horizon_days", min_val=1)
    usd_vnd = _require_finite_float(usd_vnd, "usd_vnd", min_val=0.0, strict_min=True)
    card_fx_fee = _require_finite_float(card_fx_fee, "card_fx_fee", min_val=0.0, max_val=1.0, strict_max=True)
    friction_mult = _require_finite_float(friction_mult, "friction_mult", min_val=0.0, strict_min=True)
    if not shock_levels_pct:
        raise ValueError("INVALID_INPUT_EMPTY: shock_levels_pct must be non-empty")
    validated_shocks = tuple(
        _require_finite_float(s, "shock_levels_pct", min_val=-1.0, max_val=1.0, strict_min=True, strict_max=True)
        for s in shock_levels_pct
    )
    shock_levels_pct = validated_shocks

    ftmo_std = _find_program_by_hint(
        catalog, lambda p: p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"
    )
    the5ers_hs = _find_program_by_hint(
        catalog, lambda p: "THE5ERS" in p["firm_id"] and "CLASSIC" in p["program_id"]
    ) or _find_program_by_hint(catalog, lambda p: "THE5ERS" in p["firm_id"])
    ic_funded = _find_program_by_hint(catalog, lambda p: "IC_FUNDED" in p["firm_id"])

    target_specs: list[tuple[str, dict[str, Any], float, str, int, str]] = []
    if ftmo_std is not None:
        _, m_f10 = get_program_tier(catalog, ftmo_std["program_id"], 10_000.0)
        rm, rn = resolve_rollover_anchor_mode(m_f10)
        target_specs.append(("FTMO 2-Step Standard 10K", m_f10, 10_000.0, "LIVE_CATALOG_TIER", rm, rn))

    if the5ers_hs is not None:
        for lbl, merged, cap, src_tag in _resolve_the5ers_20k_target(catalog, the5ers_hs):
            rm, rn = resolve_rollover_anchor_mode(merged)
            target_specs.append((lbl, merged, cap, src_tag, rm, rn))

    if ic_funded is not None:
        _, m_ic10 = get_program_tier(catalog, ic_funded["program_id"], 10_000.0)
        target_specs.append(
            (
                "IC Funded 2-Step Pro 10K (Equity Reset)",
                m_ic10,
                10_000.0,
                "LIVE_CATALOG_TIER",
                ROLLOVER_ANCHOR_EQUITY,
                "EQUITY_AT_RESET",
            )
        )
        target_specs.append(
            (
                "IC Funded 2-Step Pro 10K (Conservative max(Bal,Eq) Bound)",
                m_ic10,
                10_000.0,
                "CONSERVATIVE_MAX_BOUND",
                ROLLOVER_ANCHOR_MAX_BAL_EQ,
                "MAX_BALANCE_OR_EQUITY",
            )
        )

    firm_flat_map = flat_at_reset_audit.get("flat_at_reset_verified_by_firm") or {}
    rows: list[dict[str, Any]] = []

    for label, merged, cap, src_tag, r_mode, r_name in target_specs:
        pid = str(merged["program_id"])
        fid = str(merged["firm_id"])
        cal = (calibrated_cache or {}).get((pid, cap, primary_var, friction_mult))
        if cal is None:
            cal = calibrate_safe_multipliers_for_rule(
                cache,
                idx_matrix,
                program_tier=merged,
                variant=primary_var,
                friction_mult=friction_mult,
                card_fx_fee_pct=card_fx_fee,
                discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                usd_vnd_rate=usd_vnd,
            )
        st_arrs = cache.build_stage_tuple(
            capital_usd=cap,
            p1_mult=cal["p1_mult"],
            p1_lock_mult=cal["p1_lock_mult"],
            p2_mult=cal["p2_mult"],
            p2_lock_mult=cal["p2_lock_mult"],
            funded_mult=cal["funded_mult"],
            amber_mult=cal["amber_mult"],
            red_mult=cal["red_mult"],
            p1_symcap=cal["p1_symcap"],
            p2_symcap=cal["p2_symcap"],
            fn_symcap=cal["fn_symcap"],
            profile_mode=str(merged.get("profile_mode", "Standard")),
            p1_news=cal["p1_news"],
            p2_news=cal["p2_news"],
            fn_news=cal["fn_news"],
            friction_mult=friction_mult,
            steps=int(merged["steps"]),
        )
        fee_orig = float(merged["orig_usd"])
        fee_day0 = float(merged["active_promo_usd"] if use_promo_prices else fee_orig)
        payout_wd = float(merged.get("payout_withdrawal_fee_pct", merged.get("withdrawal_fee_pct", 0.015)))
        ref_wd = float(merged.get("refund_withdrawal_fee_pct", 0.0))
        anchor_code = _daily_dd_anchor_code(merged.get("daily_dd_anchor", "initial_balance"))
        firm_flat_base = bool(firm_flat_map.get(fid, flat_at_reset_audit.get("flat_at_reset_verified", False)))

        tier_shock_pairs: list[tuple[float, dict[str, Any]]] = []
        base_0_summary: dict[str, Any] | None = None
        for shock in shock_levels_pct:
            res = _simulate_single_ticket_rules_numba(
                idx_matrix,
                *st_arrs,
                steps=int(merged["steps"]),
                cap=cap,
                fee_day0_usd=fee_day0,
                fee_regular_usd=fee_orig,
                card_fx_fee_pct=card_fx_fee,
                withdrawal_fee_pct=payout_wd,
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
                p1_lock_trigger=cal["p1_lock_trigger"],
                p2_lock_trigger=cal["p2_lock_trigger"],
                amber_dd=cal["amber_dd"],
                red_dd=cal["red_dd"],
                p1_ea_stop=cal["p1_ea_stop"],
                p2_ea_stop=cal["p2_ea_stop"],
                fn_ea_stop=cal["fn_ea_stop"],
                start_day_offset=0,
                discount_rate_annual=DEFAULT_DISCOUNT_RATE,
                max_retries=0,
                refund_payout_milestone=int(merged.get("refund_payout_milestone", 1)),
                payout_buffer_retention_pct=float(merged.get("payout_buffer_retention_pct", 0.0)),
                locks_at_initial_after_first_payout=bool(merged.get("locks_at_initial_after_first_payout", False)),
                min_payout_profit_pct=float(merged.get("min_payout_profit_pct", 0.0)),
                funded_first_payout_min_prof_days=int(merged.get("funded_first_payout_min_prof_days", 0)),
                funded_first_payout_prof_pct=float(merged.get("funded_first_payout_prof_pct", 0.0)),
                daily_profit_cap_pct=float(merged.get("daily_profit_cap_pct", 0.0)),
                refund_withdrawal_fee_pct=ref_wd,
                daily_dd_anchor_mode=anchor_code,
                midnight_floating_shock_pct=float(shock),
                rollover_anchor_mode=r_mode,
            )
            summ = summarize_single_ticket_mc(
                res,
                fee_usd=fee_day0,
                fee_regular_usd=fee_orig,
                card_fx_fee_pct=card_fx_fee,
                usd_vnd_rate=usd_vnd,
                horizon_days=horizon_days,
                refund_withdrawal_fee_pct=ref_wd,
            )
            if abs(shock) < 1e-12:
                base_0_summary = summ
            tier_shock_pairs.append((float(shock), summ))

        for shock, summ in tier_shock_pairs:
            b0 = base_0_summary or summ
            rows.append(
                {
                    "label": label,
                    "firm_id": fid,
                    "program_id": pid,
                    "capital_usd": cap,
                    "tier_source_tag": src_tag,
                    "execution_evidence_tag": merged.get(
                        "execution_evidence_tag", "TERMS_VERIFIED_EXECUTION_UNMEASURED"
                    ),
                    "daily_dd_anchor_raw": merged.get("daily_dd_anchor_raw", "initial_balance"),
                    "rollover_anchor_mode": r_mode,
                    "rollover_anchor_rule": r_name,
                    "midnight_floating_shock_pct": round(float(shock) * 100.0, 2),
                    "flat_at_reset_verified": bool(firm_flat_base) if abs(shock) < 1e-12 else False,
                    "pass_24m_pct": summ["pass_24m_pct"],
                    "fail_eval_24m_pct": summ["fail_eval_24m_pct"],
                    "pending_eval_24m_pct": summ["pending_eval_24m_pct"],
                    "firm_hard_breach_pct": summ["firm_hard_breach_pct"],
                    "firm_hard_breach_daily_pct": summ["firm_hard_breach_daily_pct"],
                    "firm_hard_breach_maxdd_pct": summ["firm_hard_breach_maxdd_pct"],
                    "funded_12m_breach_pct": summ["funded_12m_breach"]["breach_12m_pct"],
                    "bot_auto_kill_pct": summ["bot_auto_kill_pct"],
                    "ev_npv_24m_usd": summ["ev_npv_24m_usd"],
                    "ev_npv_24m_vnd_tr": summ["ev_npv_24m_vnd_tr"],
                    "med_npv_24m_vnd_tr": summ["med_npv_24m_vnd_tr"],
                    "p_net_le_0_24m_pct": summ["p_net_le_0_24m_pct"],
                    "ev_per_fee_npv24": summ["ev_per_fee_npv24"],
                    "delta_npv24_vs_flat_usd": round(summ["ev_npv_24m_usd"] - b0["ev_npv_24m_usd"], 2),
                    "delta_npv24_vs_flat_vnd_tr": round(summ["ev_npv_24m_vnd_tr"] - b0["ev_npv_24m_vnd_tr"], 2),
                    "delta_daily_breach_pp": round(
                        summ["firm_hard_breach_daily_pct"] - b0["firm_hard_breach_daily_pct"], 2
                    ),
                    "delta_pass_24m_pp": round(summ["pass_24m_pct"] - b0["pass_24m_pct"], 2),
                }
            )

    return {
        "variant": primary_var,
        "friction_x": friction_mult,
        "n_paths": int(len(idx_matrix)),
        "shock_levels_pct": [round(float(s) * 100.0, 2) for s in shock_levels_pct],
        "flat_at_reset_verified": bool(flat_at_reset_audit.get("flat_at_reset_verified", False)),
        "flat_at_reset_verified_by_firm": dict(firm_flat_map),
        "tight_buffer_warnings": list(flat_at_reset_audit.get("tight_buffer_warnings", [])),
        "rows": rows,
    }
