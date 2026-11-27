"""Tier-level and pre-normalized catalog validation helpers."""

from __future__ import annotations

import math
from typing import Any

from quant_factory.capital_optimizer.catalog_normalize import (
    _dd_rule_verification_note,
    _dd_rule_verification_tag,
    _parse_daily_dd_anchor,
    _parse_dd_type,
    _parse_utc_iso,
    _pct_to_frac,
    _require_finite_float,
)


def _normalize_pre_normalized_catalog(raw: dict[str, Any]) -> dict[str, Any]:
    out = dict(raw)
    out["is_fallback"] = bool(raw.get("is_fallback", False))
    fx_in = out.get("fx_rates") or {}
    if isinstance(fx_in, dict) and "usd_vnd" in fx_in:
        _require_finite_float(fx_in.get("usd_vnd"), "fx_rates.usd_vnd")
    norm_progs = []
    top_ts = out.get("updated_utc")
    for p in out["programs"]:
        p_copy = dict(p)
        p_copy["verified_utc"] = p_copy.get("verified_utc") or top_ts
        p_copy["daily_dd_anchor_raw"] = str(
            p_copy.get("daily_dd_anchor_raw") or p_copy.get("daily_dd_anchor") or "initial_balance"
        )
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
                orig_v = _require_finite_float(
                    t_copy.get("orig_usd"), f"{p_copy.get('program_id')}:{cap_lbl}.orig_usd"
                )
                promo_raw = t_copy.get("active_promo_usd")
                promo_v = _require_finite_float(
                    promo_raw if promo_raw is not None else orig_v,
                    f"{p_copy.get('program_id')}:{cap_lbl}.active_promo_usd",
                )
                if promo_v > orig_v + 1e-9:
                    raise ValueError(
                        f"Available tier {p_copy.get('program_id')} {cap_lbl} has "
                        f"active_promo_usd ({promo_v}) > orig_usd ({orig_v})"
                    )
            else:
                if t_copy.get("orig_usd") is not None:
                    _require_finite_float(
                        t_copy.get("orig_usd"),
                        f"{p_copy.get('program_id')}:{cap_lbl}.orig_usd",
                        allow_zero=True,
                    )
                if t_copy.get("active_promo_usd") is not None:
                    _require_finite_float(
                        t_copy.get("active_promo_usd"),
                        f"{p_copy.get('program_id')}:{cap_lbl}.active_promo_usd",
                        allow_zero=True,
                    )
            t_ver = t_copy.get("verified_utc")
            if not isinstance(t_ver, str) or not t_ver.strip():
                raise ValueError(
                    f"MISSING_TIER_VERIFIED_UTC: tier {p_copy.get('program_id')}:{cap_lbl} "
                    "must declare its own verified_utc"
                )
            _parse_utc_iso(t_ver)
            tiers_out.append(t_copy)
        p_copy["tiers"] = tiers_out
        norm_progs.append(p_copy)
    out["programs"] = norm_progs
    return out


def _normalize_tier_row(
    t: Any,
    *,
    pid: str,
    firm_id: str,
    pobj: dict[str, Any],
    prog_anchor_raw: str,
) -> dict[str, Any]:
    if not isinstance(t, dict):
        raise ValueError(f"Malformed tier entry under {pid}")
    cap_raw = t.get("capital_usd")
    if cap_raw is None:
        cap_raw = t.get("account_size_usd") if t.get("account_size_usd") is not None else t.get("size_usd")
    cap = _require_finite_float(cap_raw, f"{pid}.capital_usd")
    cap_lbl = f"{int(round(cap / 1000.0))}K"
    avail_vn = bool(t.get("available_vn", True))
    orig_raw = (
        t.get("orig_usd")
        if t.get("orig_usd") is not None
        else (t.get("regular_usd") if t.get("regular_usd") is not None else t.get("price_usd"))
    )
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
        orig = (
            _require_finite_float(orig_raw, f"{pid}:{cap_lbl}.orig_usd", allow_zero=True)
            if orig_raw is not None
            else 0.0
        )
        promo = (
            _require_finite_float(promo_raw, f"{pid}:{cap_lbl}.active_promo_usd", allow_zero=True)
            if promo_raw is not None
            else 0.0
        )
    ppct_raw = t.get("active_promo_pct")
    if ppct_raw is not None:
        _require_finite_float(ppct_raw, f"{pid}:{cap_lbl}.active_promo_pct", allow_zero=True)
    ppct = _pct_to_frac(
        ppct_raw if ppct_raw is not None else (((1.0 - promo / orig) * 100.0) if orig > 0 else 0.0),
        default=0.0,
    )
    if not math.isfinite(ppct):
        raise ValueError(f"NON_FINITE_PRICE_ERROR: {pid}:{cap_lbl}.active_promo_pct={ppct!r}")
    tier_verified = t.get("verified_utc")
    if not isinstance(tier_verified, str) or not tier_verified.strip():
        raise ValueError(f"MISSING_TIER_VERIFIED_UTC: tier {pid}:{cap_lbl} must declare its own verified_utc")
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
    return tier_row
