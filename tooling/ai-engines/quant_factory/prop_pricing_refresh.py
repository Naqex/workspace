"""Prop Firm Pricing Catalog Maintenance & Refresh CLI.

Maintains `tooling/ai-engines/configs/prop_pricing_catalog.json`:
  - `--check-staleness`: verifies catalog freshness (`age_days <= staleness_max_days`, exit 0 FRESH / exit 2 STALE).
  - `--refresh-fx`: fetches live `USD/VND` & `EUR/VND` from open public FX API (`open.er-api.com`)
    WITHOUT touching any firm checkout prices or private checkout overrides.
  - `--apply-override <json>`: merges owner-verified checkout/promo overrides atomically in 1 command.
  - `--summary`: prints full 4-firm fee/capital %, VND cost, execution-evidence badges, staleness badge,
    and structural pricing traps (`25K > 10K`, `200K == 2x 100K`, `Swing 50K+ VN disabled`, `E8 100K > 2x 50K`).

Read-only safety invariants: `ORDER_SEND_COUNT = 0`, `HOLDOUT_ROWS_ANALYSED = 0`.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable
import urllib.request

ORDER_SEND_COUNT = 0
HOLDOUT_ROWS_ANALYSED = 0
MAX_FUTURE_TIMESTAMP_SKEW_DAYS = 1.0

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = AI_ENGINES_DIR / "configs" / "prop_pricing_catalog.json"
DEFAULT_FX_ENDPOINT = "https://open.er-api.com/v6/latest/USD"

ALLOWED_EXECUTION_TAGS = frozenset({
    "MEASURED_DEMO_EXECUTION",
    "TERMS_VERIFIED_EXECUTION_UNMEASURED",
})
ALLOWED_DD_TYPES = frozenset({"static", "eod_trailing", "intraday_trailing"})
ALLOWED_SEASONAL_CONFIDENCE = frozenset({"CONTRACTUAL", "HISTORICAL_PATTERN"})


def parse_utc(ts: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp string into an aware UTC datetime."""
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_utc(dt: datetime | None = None) -> str:
    """Format an aware UTC datetime into canonical ISO-8601 `...Z` format."""
    cur = (dt or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return cur.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_catalog(path: Path | str = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    """Load the prop pricing catalog JSON from disk."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or data.get("schema") != "naqex-prop-pricing-catalog-v1":
        raise ValueError(f"Invalid prop pricing catalog schema in {p}")
    return data


def save_catalog(catalog: dict[str, Any], path: Path | str = DEFAULT_CATALOG_PATH) -> Path:
    """Atomically write the prop pricing catalog JSON to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    payload = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(p)
    return p


def check_staleness(
    catalog: dict[str, Any],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate catalog, FX, per-firm, per-program, and per-tier staleness & future-date validity."""
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    max_days = float(catalog.get("staleness_max_days", 7))
    updated_dt = parse_utc(str(catalog["updated_utc"]))
    age_days = (now - updated_dt).total_seconds() / 86400.0
    catalog_stale = age_days > max_days
    future_items: list[dict[str, Any]] = []
    missing_tier_verified_utc: list[str] = []
    stale_tiers: list[dict[str, Any]] = []

    if age_days < -MAX_FUTURE_TIMESTAMP_SKEW_DAYS:
        future_items.append({"scope": "catalog.updated_utc", "verified_utc": format_utc(updated_dt), "future_by_days": round(-age_days, 3)})

    per_firm: dict[str, dict[str, Any]] = {}
    any_firm_stale = False
    for firm_id, firm in catalog.get("firms", {}).items():
        v_dt = parse_utc(str(firm.get("verified_utc", catalog["updated_utc"])))
        f_age = (now - v_dt).total_seconds() / 86400.0
        f_stale = f_age > max_days
        if f_age < -MAX_FUTURE_TIMESTAMP_SKEW_DAYS:
            future_items.append({"scope": f"firm:{firm_id}", "verified_utc": format_utc(v_dt), "future_by_days": round(-f_age, 3)})
        firm_stale_tiers: list[str] = []
        for prog_id, prog in firm.get("programs", {}).items():
            for tier_key, tier in prog.get("tiers", {}).items():
                raw_tv = tier.get("verified_utc")
                if not isinstance(raw_tv, str) or not raw_tv.strip():
                    missing_tier_verified_utc.append(f"{firm_id}/{prog_id}/{tier_key}")
                    f_stale = True
                    continue
                t_dt = parse_utc(raw_tv)
                t_age = (now - t_dt).total_seconds() / 86400.0
                if t_age < -MAX_FUTURE_TIMESTAMP_SKEW_DAYS:
                    future_items.append({
                        "scope": f"tier:{firm_id}/{prog_id}/{tier_key}",
                        "verified_utc": format_utc(t_dt),
                        "future_by_days": round(-t_age, 3),
                    })
                if t_age > max_days:
                    f_stale = True
                    firm_stale_tiers.append(f"{prog_id}:{tier_key}")
                    stale_tiers.append({
                        "scope": f"tier:{firm_id}/{prog_id}/{tier_key}",
                        "verified_utc": format_utc(t_dt),
                        "age_days": round(t_age, 3),
                    })
        if f_stale:
            any_firm_stale = True
        per_firm[firm_id] = {
            "verified_utc": format_utc(v_dt),
            "age_days": round(f_age, 3),
            "status": "STALE_NEEDS_REFRESH" if f_stale else "FRESH",
            "stale_tiers": firm_stale_tiers,
        }

    fx = catalog.get("fx_rates", {})
    fx_ts = fx.get("fetched_utc", catalog["updated_utc"])
    fx_age = (now - parse_utc(str(fx_ts))).total_seconds() / 86400.0
    if fx_age < -MAX_FUTURE_TIMESTAMP_SKEW_DAYS:
        future_items.append({"scope": "fx_rates.fetched_utc", "verified_utc": str(fx_ts), "future_by_days": round(-fx_age, 3)})
    fx_stale = fx_age > max_days

    overall_stale = catalog_stale or any_firm_stale or fx_stale or bool(future_items) or bool(missing_tier_verified_utc)
    if future_items:
        status_str = "INVALID_FUTURE_TIMESTAMP"
    elif missing_tier_verified_utc:
        status_str = "INVALID_MISSING_TIER_VERIFIED_UTC"
    elif overall_stale:
        status_str = "STALE_NEEDS_REFRESH"
    else:
        status_str = "FRESH"
    return {
        "status": status_str,
        "is_stale": overall_stale,
        "has_future_timestamps": bool(future_items),
        "future_items": future_items,
        "missing_tier_verified_utc": missing_tier_verified_utc,
        "stale_tiers": stale_tiers,
        "age_days": round(age_days, 3),
        "staleness_max_days": max_days,
        "updated_utc": format_utc(updated_dt),
        "checked_utc": format_utc(now),
        "fx_age_days": round(fx_age, 3),
        "fx_status": "STALE_NEEDS_REFRESH" if fx_stale else "FRESH",
        "firms": per_firm,
    }


def fetch_live_fx_rates(
    endpoint: str = DEFAULT_FX_ENDPOINT,
    timeout: float = 10.0,
    urlopen_fn: Callable[..., Any] | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Fetch live USD/VND and EUR/VND rates from an open public FX JSON endpoint."""
    opener = urlopen_fn or urllib.request.urlopen
    req = urllib.request.Request(
        endpoint,
        headers={"User-Agent": "Naqex-PropPricingRefresh/1.0"},
    )
    with opener(req, timeout=timeout) as resp:
        raw = resp.read()
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("result") != "success" or "rates" not in payload:
        raise ValueError(f"Unexpected FX API response from {endpoint}")
    rates = payload["rates"]
    usd_vnd = float(rates["VND"])
    usd_eur = float(rates["EUR"])
    if usd_vnd <= 0 or usd_eur <= 0:
        raise ValueError("FX API returned non-positive rates")
    eur_vnd = round(usd_vnd / usd_eur, 2)
    eur_usd = round(1.0 / usd_eur, 5)

    provider_ts = payload.get("time_last_update_utc")
    provider_iso = format_utc(now_utc)
    if isinstance(provider_ts, str) and provider_ts.strip():
        try:
            dt = datetime.strptime(provider_ts.strip(), "%a, %d %b %Y %H:%M:%S %z")
            provider_iso = format_utc(dt)
        except ValueError:
            provider_iso = provider_ts.strip()

    return {
        "usd_vnd": round(usd_vnd, 2),
        "eur_vnd": eur_vnd,
        "usd_eur": round(usd_eur, 5),
        "eur_usd": eur_usd,
        "source": "open.er-api.com",
        "source_url": endpoint,
        "provider_timestamp_utc": provider_iso,
        "fetched_utc": format_utc(now_utc),
        "rate_status": "LIVE_PUBLIC_API",
    }


def refresh_fx_in_catalog(
    catalog: dict[str, Any],
    *,
    endpoint: str = DEFAULT_FX_ENDPOINT,
    timeout: float = 10.0,
    urlopen_fn: Callable[..., Any] | None = None,
    allow_fallback: bool = False,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Return a copy of `catalog` with updated `fx_rates` only (checkout prices untouched)."""
    updated = deepcopy(catalog)
    existing_fx = updated.get("fx_rates", {})
    fb_usd = float(existing_fx.get("fallback_usd_vnd", 25500.0))
    fb_eur = float(existing_fx.get("fallback_eur_vnd", 27500.0))

    try:
        live = fetch_live_fx_rates(
            endpoint=endpoint,
            timeout=timeout,
            urlopen_fn=urlopen_fn,
            now_utc=now_utc,
        )
        live["fallback_usd_vnd"] = fb_usd
        live["fallback_eur_vnd"] = fb_eur
        updated["fx_rates"] = live
    except Exception as exc:
        if not allow_fallback:
            raise
        updated["fx_rates"] = {
            "usd_vnd": fb_usd,
            "eur_vnd": fb_eur,
            "usd_eur": round(fb_usd / fb_eur, 5),
            "eur_usd": round(fb_eur / fb_usd, 5),
            "source": "offline_fallback",
            "source_url": endpoint,
            "provider_timestamp_utc": existing_fx.get("provider_timestamp_utc", format_utc(now_utc)),
            "fetched_utc": format_utc(now_utc),
            "rate_status": "FALLBACK_OFFLINE",
            "fallback_reason": str(exc),
            "fallback_usd_vnd": fb_usd,
            "fallback_eur_vnd": fb_eur,
        }
    return updated


def apply_override(
    catalog: dict[str, Any],
    override: dict[str, Any],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Merge an owner-verified checkout/promo override into a copy of `catalog`.

    Supported override JSON shape:
    {
      "pricing_source_tag": "LIVE_VN_CHECKOUT_20261202",   // optional
      "verified_utc": "2026-12-02T09:00:00Z",              // optional
      "tier_updates": [
        {
          "firm_id": "ftmo",
          "program_id": "ftmo_2step_standard",
          "tier": "10K",
          "orig_usd": 98.61,                               // optional
          "active_promo_usd": 98.61,                       // optional
          "active_promo_pct": 0.0,                         // optional
          "promo_label": "POST_BF_REGULAR",                // optional
          "available_vn": true,                            // optional
          "unavailable_reason_vn": null                    // optional
        }
      ],
      "vn_transaction_costs": { ... }                      // optional partial merge
    }
    """
    updated = deepcopy(catalog)
    ts = str(override.get("verified_utc") or format_utc(now_utc))
    parse_utc(ts)  # validate ISO-8601

    tier_updates = override.get("tier_updates", [])
    if not isinstance(tier_updates, list):
        raise ValueError("override['tier_updates'] must be a list")

    touched_firms: set[str] = set()
    touched_tiers_by_prog: dict[tuple[str, str], set[str]] = {}
    allowed_tier_fields = {
        "orig_usd",
        "active_promo_usd",
        "active_promo_pct",
        "promo_label",
        "available_vn",
        "unavailable_reason_vn",
        "dd_daily_pct",
        "dd_max_pct",
        "dd_type",
        "verified_utc",
    }

    for item in tier_updates:
        firm_id = item.get("firm_id")
        program_id = item.get("program_id")
        tier_key = item.get("tier")
        if firm_id not in updated["firms"]:
            raise ValueError(f"Unknown firm_id in override: {firm_id!r}")
        firm = updated["firms"][firm_id]
        if program_id not in firm["programs"]:
            raise ValueError(f"Unknown program_id {program_id!r} for firm {firm_id!r}")
        program = firm["programs"][program_id]
        if tier_key not in program["tiers"]:
            raise ValueError(f"Unknown tier {tier_key!r} for program {program_id!r}")
        tier_obj = program["tiers"][tier_key]

        tier_ts = ts
        for k, v in item.items():
            if k in ("firm_id", "program_id", "tier"):
                continue
            if k not in allowed_tier_fields:
                raise ValueError(f"Unsupported tier override field: {k!r}")
            if k == "verified_utc":
                parse_utc(str(v))
                tier_ts = str(v)
                continue
            if k == "dd_type" and v not in ALLOWED_DD_TYPES:
                raise ValueError(f"Invalid dd_type: {v!r}")
            if k in ("orig_usd", "active_promo_usd") and v is not None:
                fv = float(v)
                if isinstance(v, bool) or (not math.isfinite(fv)) or fv <= 0.0:
                    raise ValueError(f"Price field {k} must be finite and positive, got {v!r}")
            if k == "active_promo_pct":
                fv = float(v)
                if isinstance(v, bool) or (not math.isfinite(fv)) or fv < 0.0 or fv > 90.0:
                    raise ValueError(f"active_promo_pct out of bounds [0, 90]: {v!r}")
            if k in ("dd_daily_pct", "dd_max_pct"):
                fv = float(v)
                if isinstance(v, bool) or (not math.isfinite(fv)) or fv <= 0.0:
                    raise ValueError(f"DD field {k} must be finite and positive, got {v!r}")
            tier_obj[k] = v

        orig = tier_obj.get("orig_usd")
        promo = tier_obj.get("active_promo_usd")
        if orig is not None and promo is not None and float(promo) > float(orig) + 1e-9:
            raise ValueError(
                f"active_promo_usd ({promo}) cannot exceed orig_usd ({orig}) "
                f"for {firm_id}/{program_id}/{tier_key}"
            )
        if tier_obj.get("available_vn") is True and (orig is None or promo is None):
            raise ValueError(
                f"available_vn=True requires non-null orig_usd & active_promo_usd "
                f"for {firm_id}/{program_id}/{tier_key}"
            )

        # Strictly stamp ONLY this updated tier's `verified_utc` — NEVER blindly bump untouched sibling tiers!
        tier_obj["verified_utc"] = tier_ts
        touched_tiers_by_prog.setdefault((firm_id, program_id), set()).add(tier_key)
        touched_firms.add(firm_id)

    # Update program["verified_utc"] ONLY if EVERY tier in that program was updated; otherwise preserve oldest tier timestamp!
    for (firm_id, program_id), touched_keys in touched_tiers_by_prog.items():
        prog = updated["firms"][firm_id]["programs"][program_id]
        all_tier_keys = set(prog["tiers"].keys())
        if touched_keys == all_tier_keys:
            tier_dts = [parse_utc(str(prog["tiers"][k]["verified_utc"])) for k in all_tier_keys]
            prog["verified_utc"] = format_utc(min(tier_dts))

    # Update firm["verified_utc"] ONLY if ALL tiers across ALL programs of that firm were updated;
    # still propagate pricing_source_tag when supplied.
    for firm_id in touched_firms:
        firm = updated["firms"][firm_id]
        all_progs_fully_updated = all(
            touched_tiers_by_prog.get((firm_id, pid)) == set(p["tiers"].keys())
            for pid, p in firm["programs"].items()
        )
        if all_progs_fully_updated:
            prog_dts = [parse_utc(str(p["verified_utc"])) for p in firm["programs"].values()]
            firm["verified_utc"] = format_utc(min(prog_dts))
        if override.get("pricing_source_tag"):
            firm["pricing_source_tag"] = str(override["pricing_source_tag"])

    if "vn_transaction_costs" in override:
        if not isinstance(override["vn_transaction_costs"], dict):
            raise ValueError("override['vn_transaction_costs'] must be a dict")
        updated["vn_transaction_costs"].update(override["vn_transaction_costs"])

    updated["updated_utc"] = ts
    return updated


def iter_skus(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all firm/program/tier SKUs with derived Fee/Capital % and VND costs."""
    fx = catalog["fx_rates"]
    usd_vnd = float(fx["usd_vnd"])
    card_fee_mult = 1.0 + float(catalog["vn_transaction_costs"]["card_fx_buy_fee_pct"]) / 100.0
    rows: list[dict[str, Any]] = []

    for firm_id, firm in catalog["firms"].items():
        for program_id, prog in firm["programs"].items():
            tiers_sorted = sorted(
                prog["tiers"].items(),
                key=lambda kv: float(kv[1]["capital_usd"]),
            )
            for tier_key, tier in tiers_sorted:
                cap = float(tier["capital_usd"])
                avail = bool(tier["available_vn"])
                orig = float(tier["orig_usd"]) if tier.get("orig_usd") is not None else None
                active = (
                    float(tier["active_promo_usd"])
                    if tier.get("active_promo_usd") is not None
                    else None
                )
                ratio_orig = round((orig / cap) * 100.0, 4) if (orig is not None and cap > 0) else None
                ratio_active = (
                    round((active / cap) * 100.0, 4) if (active is not None and cap > 0) else None
                )
                vnd_raw = round(active * usd_vnd) if active is not None else None
                vnd_card = round(active * usd_vnd * card_fee_mult) if active is not None else None
                rows.append({
                    "firm_id": firm_id,
                    "firm_name": firm["display_name"],
                    "program_id": program_id,
                    "program_name": prog["display_name"],
                    "challenge_mode": prog["challenge_mode"],
                    "tier": tier_key,
                    "capital_usd": cap,
                    "available_vn": avail,
                    "unavailable_reason_vn": tier.get("unavailable_reason_vn"),
                    "orig_usd": orig,
                    "active_promo_usd": active,
                    "active_promo_pct": float(tier.get("active_promo_pct", 0.0)),
                    "fee_ratio_orig_pct": ratio_orig,
                    "fee_ratio_active_pct": ratio_active,
                    "active_vnd_raw": vnd_raw,
                    "active_vnd_with_card_fee": vnd_card,
                    "fee_refund_pct": float(prog["fee_refund_pct"]),
                    "dd_daily_pct": float(tier.get("dd_daily_pct", prog["dd_daily_pct"])),
                    "dd_max_pct": float(tier.get("dd_max_pct", prog["dd_max_pct"])),
                    "dd_type": str(tier.get("dd_type", prog["dd_type"])),
                    "best_day_cap_pct": prog.get("best_day_cap_pct"),
                    "daily_profit_cap_pct": prog.get("daily_profit_cap_pct"),
                    "min_trading_days": int(prog["min_trading_days"]),
                    "min_profitable_days": int(prog["min_profitable_days"]),
                    "news_rule": prog["news_rule"],
                    "profit_split_pct": float(prog["profit_split_pct"]),
                    "min_payout_usd": float(prog["min_payout_usd"]),
                    "max_allocation_usd": float(prog["max_allocation_usd"]),
                    "payout_rail_fee_pct": float(firm["payout_rail_fee_pct"]),
                    "execution_evidence_tag": firm["execution_evidence_tag"],
                })
    return rows


def detect_pricing_traps(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect structural fee-ratio traps, 2x zero-discount traps, and VN-disabled tiers."""
    traps: list[dict[str, Any]] = []
    for firm_id, firm in catalog["firms"].items():
        for program_id, prog in firm["programs"].items():
            prog_label = (
                prog["display_name"]
                if prog["display_name"].startswith(firm["display_name"])
                else f"{firm['display_name']} {prog['display_name']}"
            )
            tiers_sorted = sorted(
                prog["tiers"].items(),
                key=lambda kv: float(kv[1]["capital_usd"]),
            )
            available: list[tuple[str, float, float, float]] = []
            for tier_key, tier in tiers_sorted:
                cap = float(tier["capital_usd"])
                if not tier.get("available_vn", False):
                    traps.append({
                        "trap_type": "VN_UNAVAILABLE_TIER",
                        "firm_id": firm_id,
                        "program_id": program_id,
                        "tier": tier_key,
                        "detail": (
                            f"{prog_label} {tier_key} "
                            f"disabled on VN checkout ({tier.get('unavailable_reason_vn', 'unavailable')})"
                        ),
                    })
                    continue
                orig = float(tier["orig_usd"])
                active = float(tier["active_promo_usd"])
                available.append((tier_key, cap, orig, active))

            for idx in range(1, len(available)):
                prev_k, prev_cap, prev_orig, prev_act = available[idx - 1]
                cur_k, cur_cap, cur_orig, cur_act = available[idx]
                prev_r_orig = (prev_orig / prev_cap) * 100.0
                cur_r_orig = (cur_orig / cur_cap) * 100.0
                prev_r_act = (prev_act / prev_cap) * 100.0
                cur_r_act = (cur_act / cur_cap) * 100.0

                if cur_r_orig > prev_r_orig + 1e-4 or cur_r_act > prev_r_act + 1e-4:
                    traps.append({
                        "trap_type": "FEE_RATIO_INVERSION_TRAP",
                        "firm_id": firm_id,
                        "program_id": program_id,
                        "tier": cur_k,
                        "compared_to_tier": prev_k,
                        "cur_ratio_orig_pct": round(cur_r_orig, 4),
                        "prev_ratio_orig_pct": round(prev_r_orig, 4),
                        "cur_ratio_active_pct": round(cur_r_act, 4),
                        "prev_ratio_active_pct": round(prev_r_act, 4),
                        "detail": (
                            f"{prog_label}: {cur_k} fee/cap "
                            f"({cur_r_orig:.3f}% orig / {cur_r_act:.3f}% active) > "
                            f"{prev_k} ({prev_r_orig:.3f}% orig / {prev_r_act:.3f}% active)"
                        ),
                    })

                if abs(cur_cap - 2.0 * prev_cap) < 1e-6:
                    if cur_act >= (2.0 * prev_act - 0.05):
                        traps.append({
                            "trap_type": "ZERO_VOLUME_DISCOUNT_2X_TRAP",
                            "firm_id": firm_id,
                            "program_id": program_id,
                            "tier": cur_k,
                            "compared_to_tier": prev_k,
                            "ratio_to_2x_smaller": round(cur_act / (2.0 * prev_act), 6),
                            "detail": (
                                f"{prog_label}: {cur_k} "
                                f"(${cur_act:.2f}) >= 2x {prev_k} (${2.0 * prev_act:.2f}) — "
                                f"zero volume discount while doubling single-bullet ruin risk"
                            ),
                        })
    return traps


def format_summary(
    catalog: dict[str, Any],
    now_utc: datetime | None = None,
) -> str:
    """Format a human-readable summary table of all 4 firms, VND costs, staleness, and traps."""
    stale = check_staleness(catalog, now_utc=now_utc)
    fx = catalog["fx_rates"]
    card_fee_pct = float(catalog["vn_transaction_costs"]["card_fx_buy_fee_pct"])
    lines: list[str] = [
        "=== NAQEX PROP PRICING CATALOG SUMMARY ===",
        f"Schema: {catalog['schema']} | Updated: {catalog['updated_utc']} | "
        f"Staleness: [{stale['status']}] (age={stale['age_days']:.2f}d / max={stale['staleness_max_days']:.0f}d)",
        f"FX ({fx['rate_status']} via {fx['source']}): "
        f"USD/VND={fx['usd_vnd']:,.2f} | EUR/VND={fx['eur_vnd']:,.2f} | "
        f"VN Card FX Buy Fee={card_fee_pct:.1f}%",
        "",
        f"{'Firm':<11} {'Program':<28} {'Tier':<5} {'VN':<4} {'Orig$':>8} {'Act$':>8} "
        f"{'Fee/Cap':>8} {'VND(+2.5%)':>13} {'DD(D/M)':>9} {'Ref%':>5} {'ExecTag'}",
        "-" * 134,
    ]
    for row in iter_skus(catalog):
        vn_flag = "YES" if row["available_vn"] else "NO"
        orig_s = f"{row['orig_usd']:.2f}" if row["orig_usd"] is not None else "N/A"
        act_s = f"{row['active_promo_usd']:.2f}" if row["active_promo_usd"] is not None else "N/A"
        ratio_s = (
            f"{row['fee_ratio_active_pct']:.3f}%"
            if row["fee_ratio_active_pct"] is not None
            else "N/A"
        )
        vnd_s = (
            f"{row['active_vnd_with_card_fee']:,}"
            if row["active_vnd_with_card_fee"] is not None
            else "DISABLED_VN"
        )
        dd_s = f"{row['dd_daily_pct']:.1f}/{row['dd_max_pct']:.0f}"
        exec_short = "MEASURED_DEMO" if row["execution_evidence_tag"] == "MEASURED_DEMO_EXECUTION" else "UNMEASURED_EXEC"
        lines.append(
            f"{row['firm_name']:<11} {row['program_id']:<28} {row['tier']:<5} {vn_flag:<4} "
            f"{orig_s:>8} {act_s:>8} {ratio_s:>8} {vnd_s:>13} {dd_s:>9} "
            f"{row['fee_refund_pct']:>4.0f}% {exec_short}"
        )

    traps = detect_pricing_traps(catalog)
    lines.append("")
    lines.append(f"=== DETECTED PRICING TRAPS & VN CONSTRAINTS ({len(traps)}) ===")
    for t in traps:
        lines.append(f"  - [{t['trap_type']}] {t['detail']}")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Maintain and inspect the Naqex 4-firm prop pricing catalog."
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Path to prop_pricing_catalog.json",
    )
    parser.add_argument(
        "--check-staleness",
        action="store_true",
        help="Check catalog freshness (exit 0 FRESH, exit 2 STALE_NEEDS_REFRESH).",
    )
    parser.add_argument(
        "--refresh-fx",
        action="store_true",
        help="Refresh live USD/VND & EUR/VND from open public FX API without altering checkout prices.",
    )
    parser.add_argument(
        "--allow-fx-fallback",
        action="store_true",
        help="If --refresh-fx cannot reach the network, tag and write offline fallback FX rates.",
    )
    parser.add_argument(
        "--apply-override",
        type=Path,
        default=None,
        help="Path to override JSON file to merge into catalog atomically.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print formatted 4-firm fee/capital %, VND cost, staleness badge, and pricing traps.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    catalog = load_catalog(args.catalog)
    modified = False

    if args.refresh_fx:
        catalog = refresh_fx_in_catalog(catalog, allow_fallback=args.allow_fx_fallback)
        modified = True

    if args.apply_override is not None:
        override_data = json.loads(args.apply_override.read_text(encoding="utf-8"))
        catalog = apply_override(catalog, override_data)
        modified = True

    if modified:
        save_catalog(catalog, args.catalog)

    if args.summary:
        print(format_summary(catalog))

    if args.check_staleness:
        status = check_staleness(catalog)
        print(json.dumps(status, indent=2))
        return 2 if status["is_stale"] else 0

    if not (args.refresh_fx or args.apply_override is not None or args.summary or args.check_staleness):
        print(format_summary(catalog))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
