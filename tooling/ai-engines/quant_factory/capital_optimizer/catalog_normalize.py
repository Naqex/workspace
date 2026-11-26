"""Strict parsing and normalization helpers for external prop-firm pricing catalogs."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from quant_factory.capital_optimizer.constants import (
    DAILY_DD_ANCHOR_INITIAL_BALANCE,
    DAILY_DD_ANCHOR_PREV_DAY_BALANCE,
    DD_ANCHOR_TAG_BALANCE_VERIFIED,
    DD_ANCHOR_TAG_UNVERIFIED_UNLESS_FLAT,
    DD_EOD_TRAILING,
    DD_INTRADAY_TRAILING,
    DD_STATIC,
)


def _parse_utc_iso(ts: Any) -> datetime:
    """Parse ISO-8601 UTC timestamp string strictly into an aware UTC datetime."""
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError(f"Missing or non-string UTC timestamp: {ts!r}")
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _pct_to_frac(val: Any, default: float = 0.0) -> float:
    """Convert a percentage-point value from `prop_pricing_catalog.json` (e.g. `0.5` -> `0.005`) to a fraction."""
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
    """Classify catalog `daily_dd_anchor` into `initial_balance` vs `prev_day_balance`."""
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
    elif fv <= 0.0:
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
    """Adapt `prop_pricing_catalog.json` (nested `firms -> programs -> tiers`) to canonical format."""
    from quant_factory.capital_optimizer.catalog_tiers import (
        _normalize_pre_normalized_catalog,
        _normalize_tier_row,
    )

    if not isinstance(raw, dict):
        raise ValueError("Pricing catalog root JSON must be an object")

    if "programs" in raw and isinstance(raw["programs"], list) and raw["programs"]:
        return _normalize_pre_normalized_catalog(raw)

    fx_raw = raw.get("fx_rates")
    if not isinstance(fx_raw, dict):
        raise ValueError("Pricing catalog missing required `fx_rates` object")
    usd_vnd = float(fx_raw.get("usd_vnd") or fx_raw.get("USD_VND") or fx_raw.get("usd_to_vnd") or 0.0)
    eur_vnd = float(fx_raw.get("eur_vnd") or fx_raw.get("EUR_VND") or fx_raw.get("eur_to_vnd") or 0.0)
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
            _pct_to_frac(
                fobj.get("payout_rail_fee_pct", fobj.get("withdrawal_fee_pct", default_wd * 100.0)),
                default=default_wd,
            ),
        )
        payout_wd_fee_firm = rail_fee_firm + fx_conv_spread
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
        if not nested_progs:
            continue
        p_iter = (
            [{"program_id": k, **v} for k, v in nested_progs.items()]
            if isinstance(nested_progs, dict)
            else list(nested_progs)
        )
        for pobj in p_iter:
            if not isinstance(pobj, dict):
                raise ValueError(f"Malformed program entry under firm {firm_id}")
            pid = (
                str(pobj.get("program_id") or pobj.get("id") or f"{firm_id}_{pobj.get('name', 'PROG')}")
                .upper()
                .replace(" ", "_")
            )
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
            norm_tiers = [
                _normalize_tier_row(
                    t, pid=pid, firm_id=firm_id, pobj=pobj, prog_anchor_raw=prog_anchor_raw
                )
                for t in raw_tiers
            ]

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
            prog_dd_tag = _dd_rule_verification_tag(firm_id, prog_anchor_raw, prog_anchor_mode)
            fobj_ea = fobj.get("ea_policy")
            ea_pol_str = str(
                pobj.get("ea_policy")
                or (fobj_ea.get("summary") if isinstance(fobj_ea, dict) else fobj_ea)
                or "VERIFY_AT_CHECKOUT"
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
                "dd_rule_verification_tag": prog_dd_tag,
                "dd_rule_verification_note": _dd_rule_verification_note(firm_id, prog_anchor_raw, prog_dd_tag),
                "trail_lock_at_initial": bool(pobj.get("trail_lock_at_initial", False)),
                "locks_at_initial_after_first_payout": bool(
                    pobj.get("locks_at_initial_after_first_payout", False)
                ),
                "best_day_cap_pct": _pct_to_frac(pobj.get("best_day_cap_pct", 0.0), default=0.0),
                "daily_profit_cap_pct": _pct_to_frac(pobj.get("daily_profit_cap_pct", 0.0), default=0.0),
                "min_trading_days": int(pobj.get("min_trading_days", 4 if steps == 2 else 0) or 0),
                "min_profitable_days": min_prof_days,
                "min_profitable_day_pct": min_prof_thr,
                "funded_first_payout_min_prof_days": int(
                    pobj.get("funded_first_payout_min_profitable_days", 0) or 0
                ),
                "funded_first_payout_prof_pct": _pct_to_frac(
                    pobj.get("funded_first_payout_profitable_day_pct", 0.0), default=0.0
                ),
                "fee_refund_pct": fee_ref,
                "refund_payout_milestone": ref_mile,
                "hub_credit_rebate_pct": _pct_to_frac(pobj.get("hub_credit_rebate_pct", 0.0), default=0.0),
                "payout_buffer_retention_pct": _pct_to_frac(
                    pobj.get("payout_buffer_retention_pct", 0.0), default=0.0
                ),
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
                "ea_policy": ea_pol_str,
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
