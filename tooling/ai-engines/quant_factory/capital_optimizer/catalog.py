"""Fail-closed pricing catalog loader, freshness checker, pricing-trap detector, and Step 5 summary loader."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_core.io_utils import sha256_bytes, sha256_file

from quant_factory.capital_optimizer.catalog_defaults import build_default_pricing_catalog
from quant_factory.capital_optimizer.catalog_normalize import (
    _cal_days_to_trading_days,
    _daily_dd_anchor_code,
    _dd_rule_verification_note,
    _dd_rule_verification_tag,
    _dd_type_code,
    _normalize_external_catalog,
    _parse_daily_dd_anchor,
    _parse_dd_type,
    _parse_refund_milestone,
    _parse_utc_iso,
    _pct_to_frac,
    _require_finite_float,
)
from quant_factory.capital_optimizer.constants import (
    CONTROL_VARIANT_DEFAULT,
    DEFAULT_CATALOG_PATH,
    DEFAULT_STEP5_REPORT_PATH,
    MAX_FUTURE_TIMESTAMP_SKEW_DAYS,
    PRIMARY_VARIANT_DEFAULT,
)

__all__ = [
    "build_default_pricing_catalog",
    "check_catalog_freshness",
    "detect_pricing_traps",
    "get_program_tier",
    "load_pricing_catalog",
    "load_step5_c00_c10_summary",
    "_cal_days_to_trading_days",
    "_daily_dd_anchor_code",
    "_dd_rule_verification_note",
    "_dd_rule_verification_tag",
    "_dd_type_code",
    "_find_program_by_hint",
    "_normalize_external_catalog",
    "_parse_daily_dd_anchor",
    "_parse_dd_type",
    "_parse_refund_milestone",
    "_parse_utc_iso",
    "_pct_to_frac",
    "_pick_tier_near",
    "_require_finite_float",
]


def check_catalog_freshness(
    catalog: dict[str, Any],
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Enforce catalog, FX, per-program, and strict per-tier `verified_utc` freshness & future-date guards."""
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
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
    """Fail-closed pricing catalog loader with per-tier `verified_utc`, finite-price, and future-date guards."""
    p = Path(path) if path is not None else DEFAULT_CATALOG_PATH
    if p is not None and p.is_file():
        try:
            raw_bytes = p.read_bytes()
            raw = json.loads(raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Corrupt JSON in pricing catalog {p}: {exc}") from exc
        norm = _normalize_external_catalog(raw)
        norm["source_path"] = str(p)
        norm["source_sha256"] = sha256_bytes(raw_bytes)
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
                    f"{freshness['staleness_max_days']}d freshness limit "
                    f"(max_age={freshness['max_age_days']}d): {scopes}"
                )
            freshness["override_used"] = True
            freshness["status"] = "STALE_OVERRIDDEN_HISTORICAL_AUDIT"
        norm["freshness_report"] = freshness
        return norm

    if not allow_fallback:
        raise FileNotFoundError(f"Pricing catalog not found (fail-closed, allow_fallback=False): {p}")

    fb = build_default_pricing_catalog()
    fb["source_path"] = "BUILTIN_DEFAULT_FALLBACK"
    fb["source_sha256"] = "FALLBACK"
    fb["freshness_report"] = (
        check_catalog_freshness(fb, now_utc=now_utc)
        if enforce_freshness
        else {
            "status": "SKIPPED_FALLBACK",
            "is_stale": False,
            "override_used": True,
        }
    )
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
    """Verify VN checkout traps (`25K` fee-ratio trap, `200K == 2x 100K`, `Swing >= 50K unavailable`)."""
    std_prog = next(
        (
            p
            for p in catalog["programs"]
            if p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Standard"
        ),
        None,
    )
    swing_prog = next(
        (
            p
            for p in catalog["programs"]
            if p["firm_id"] == "FTMO" and p["steps"] == 2 and p["profile_mode"] == "Swing"
        ),
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
        blocked = [
            c
            for c in (50_000.0, 100_000.0, 200_000.0)
            if c in by_cap_sw and not by_cap_sw[c].get("available_vn", True)
        ]
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
    """Ingest Step 5 `C00 vs C10` report; lock v2 primary variant to `C10_NEWS_ON` with `C00` control."""
    p = path or DEFAULT_STEP5_REPORT_PATH
    fallback_7yr = DEFAULT_STEP5_REPORT_PATH.parent / "step5_7yr_dev_c00_vs_c10_report.json"
    chosen = p if (p is not None and Path(p).is_file()) else (fallback_7yr if fallback_7yr.is_file() else None)
    if chosen is not None:
        chosen_path = Path(chosen)
        raw = json.loads(chosen_path.read_text(encoding="utf-8"))
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
        return {
            "loaded": True,
            "is_full_mt5_plus_7yr": bool(mt5_pairs),
            "source_path": str(chosen_path),
            "source_sha256": sha256_file(chosen_path),
            "verdict": verdict,
            "primary_variant": PRIMARY_VARIANT_DEFAULT,
            "control_variant": CONTROL_VARIANT_DEFAULT,
            "active_variants": [PRIMARY_VARIANT_DEFAULT, CONTROL_VARIANT_DEFAULT, "C10"],
            "primary_variant_rationale": (
                "Step 5/6 MT5 Model=4 & Astra R10 confirmed C10_NEWS_ON "
                "(C10 sizing/ProfitLock + Red-News ON all phases) "
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


def _find_program_by_hint(
    catalog: dict[str, Any],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any] | None:
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
