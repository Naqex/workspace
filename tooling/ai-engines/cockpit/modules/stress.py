"""Black-Swan stress matrix, Multi-Prop budget parser, and VND/USD risk calculator."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cockpit.modules.helpers import _parse_float_token, _safe_read_json, as_dict, as_list
from cockpit.modules.state import _STRESS_CACHE_LOCK, ORDER_SEND_COUNT, ROOT, get_stress_md_cache
from quant_factory.treasury_ledger import DEFAULT_USD_VND_RATE, compute_prop_own_crossover


def _interpolate_red_team_curve(curve: list[dict[str, Any]], mult: float) -> dict[str, float]:
    """Piecewise-linear interpolation on Red-Team cost stress grid (1.0x..3.0x), extrapolating gently below 1.0x."""
    if not curve:
        return {"cost_mult": mult, "ann_pct": 0.0, "peak_dd_pct": 0.0, "calmar": 0.0, "net_usd": 0.0}
    pts = sorted(curve, key=lambda x: float(x["cost_mult"]))
    xs = [float(p["cost_mult"]) for p in pts]
    m = max(0.5, min(3.5, float(mult)))

    if m <= xs[0]:
        if len(xs) >= 2:
            t = (m - xs[0]) / max(1e-9, xs[1] - xs[0])
            p0, p1 = pts[0], pts[1]
            ann = float(p0["ann_pct"]) + t * (float(p1["ann_pct"]) - float(p0["ann_pct"]))
            dd = max(1.0, float(p0["peak_dd_pct"]) + t * (float(p1["peak_dd_pct"]) - float(p0["peak_dd_pct"])))
            net = float(p0["net_usd"]) + t * (float(p1["net_usd"]) - float(p0["net_usd"]))
            return {
                "cost_mult": round(m, 2),
                "ann_pct": round(ann, 2),
                "peak_dd_pct": round(dd, 2),
                "calmar": round(ann / dd, 2),
                "net_usd": round(net, 2),
            }
        p0 = pts[0]
        return {
            "cost_mult": round(m, 2),
            "ann_pct": float(p0["ann_pct"]),
            "peak_dd_pct": float(p0["peak_dd_pct"]),
            "calmar": float(p0["calmar"]),
            "net_usd": float(p0["net_usd"]),
        }

    if m >= xs[-1]:
        if len(xs) >= 2:
            p0, p1 = pts[-2], pts[-1]
            t = (m - xs[-1]) / max(1e-9, xs[-1] - xs[-2])
            ann = float(p1["ann_pct"]) + t * (float(p1["ann_pct"]) - float(p0["ann_pct"]))
            dd = max(1.0, float(p1["peak_dd_pct"]) + t * (float(p1["peak_dd_pct"]) - float(p0["peak_dd_pct"])))
            net = float(p1["net_usd"]) + t * (float(p1["net_usd"]) - float(p0["net_usd"]))
            return {
                "cost_mult": round(m, 2),
                "ann_pct": round(ann, 2),
                "peak_dd_pct": round(dd, 2),
                "calmar": round(ann / dd, 2),
                "net_usd": round(net, 2),
            }
        p1 = pts[-1]
        return {
            "cost_mult": round(m, 2),
            "ann_pct": float(p1["ann_pct"]),
            "peak_dd_pct": float(p1["peak_dd_pct"]),
            "calmar": float(p1["calmar"]),
            "net_usd": float(p1["net_usd"]),
        }

    for i in range(len(xs) - 1):
        if xs[i] <= m <= xs[i + 1]:
            t = (m - xs[i]) / max(1e-9, xs[i + 1] - xs[i])
            p0, p1 = pts[i], pts[i + 1]
            ann = float(p0["ann_pct"]) + t * (float(p1["ann_pct"]) - float(p0["ann_pct"]))
            dd = float(p0["peak_dd_pct"]) + t * (float(p1["peak_dd_pct"]) - float(p0["peak_dd_pct"]))
            net = float(p0["net_usd"]) + t * (float(p1["net_usd"]) - float(p0["net_usd"]))
            return {
                "cost_mult": round(m, 2),
                "ann_pct": round(ann, 2),
                "peak_dd_pct": round(dd, 2),
                "calmar": round(ann / max(0.01, dd), 2),
                "net_usd": round(net, 2),
            }
    return pts[0]


def _parse_stress_and_multiprop_md(md_path: Path) -> dict[str, Any] | None:
    """Parse verified Wave-2 Cycle 3B Black-Swan & Multi-Prop report tables (cached by mtime)."""
    if not md_path.is_file():
        return None
    mtime = md_path.stat().st_mtime
    cache_key = str(md_path.resolve())
    cache_map = get_stress_md_cache()
    with _STRESS_CACHE_LOCK:
        cached = cache_map.get(cache_key)
        if cached is not None and cached[0] == mtime:
            return cached[1]

    txt = md_path.read_text(encoding="utf-8", errors="replace")
    gen_m = re.search(r"\*\*Generated UTC:\*\*\s*`([^`]+)`", txt)
    generated_utc = gen_m.group(1) if gen_m else None

    # Parse 1A/1B/1C Multi-Prop budget tables (500 / 1,500 / 3,000 USD)
    budgets: dict[int, list[dict[str, Any]]] = {500: [], 1500: [], 3000: []}
    alloc_stress: dict[str, dict[str, Any]] = {}
    section = ""

    for raw_ln in txt.splitlines():
        ln = raw_ln.strip()
        if ln.startswith("### 1A."):
            section = "b500"
            continue
        if ln.startswith("### 1B."):
            section = "b1500"
            continue
        if ln.startswith("### 1C."):
            section = "b3000"
            continue
        if ln.startswith("### 1D."):
            section = "b1d"
            continue
        if ln.startswith("### 2A."):
            section = "s2a"
            continue
        if ln.startswith("### 2B."):
            section = "s2b"
            continue
        if ln.startswith("## 3."):
            section = "done"
            continue

        if (
            not ln.startswith("|")
            or ln.startswith("|---")
            or ln.startswith("| Architecture")
            or ln.startswith("| Allocator")
        ):
            continue
        cols = [c.strip() for c in ln.strip("|").split("|")]

        if section in ("b500", "b1500", "b3000") and len(cols) >= 10:
            bkey = {"b500": 500, "b1500": 1500, "b3000": 3000}[section]
            budgets[bkey].append({
                "architecture": cols[0],
                "profile": cols[1],
                "wipeout_pct": _parse_float_token(cols[2]) or 0.0,
                "sustain_pct": _parse_float_token(cols[3]) or 0.0,
                "double_fail_pct": _parse_float_token(cols[4]) or 0.0,
                "p95_corr_dd_pct": _parse_float_token(cols[5]) or 0.0,
                "fees_24m_usd": _parse_float_token(cols[6]) or 0.0,
                "wealth_24m_med_usd": _parse_float_token(cols[7]) or 0.0,
                "ev_per_fee": _parse_float_token(cols[8]) or 0.0,
                "ob_60m_raw": cols[9],
            })
        elif section == "s2a" and len(cols) >= 8:
            aname = cols[0]
            h30_50 = [x.strip() for x in cols[4].split("/")]
            c95_99 = [x.strip() for x in cols[5].split("/")]
            w20_60 = [x.strip() for x in cols[1].split("/")]
            alloc_stress[aname] = {
                "allocator": aname,
                "hist_20d_dd_pct": _parse_float_token(w20_60[0]) or 0.0,
                "hist_60d_dd_pct": _parse_float_token(w20_60[1]) if len(w20_60) > 1 else 0.0,
                "rate2022_ftx_dd_pct": _parse_float_token(cols[2]) or 0.0,
                "cex_weight_pct": _parse_float_token(cols[3]) or 0.0,
                "cex_haircut_30_pct": _parse_float_token(h30_50[0]) or 0.0,
                "cex_haircut_50_pct": _parse_float_token(h30_50[1]) if len(h30_50) > 1 else 0.0,
                "corr085_p95_dd_pct": _parse_float_token(c95_99[0]) or 0.0,
                "corr085_p99_dd_pct": _parse_float_token(c95_99[1]) if len(c95_99) > 1 else 0.0,
                "worst_1d_p99_pct": _parse_float_token(cols[6]) or 0.0,
                "slip_3x_cagr_raw": cols[7],
            }
        elif section == "s2b" and len(cols) >= 3:
            aname = cols[0]
            if aname in alloc_stress:
                alloc_stress[aname]["worst_case_dd_pct"] = _parse_float_token(cols[1]) or 0.0
                alloc_stress[aname]["dominant_shock"] = cols[2]

    if not alloc_stress and not any(budgets.values()):
        return None

    parsed = {
        "source": "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md",
        "generated_utc": generated_utc,
        "multi_prop_budgets": budgets,
        "black_swan_allocators": list(alloc_stress.values()),
    }
    with _STRESS_CACHE_LOCK:
        cache_map[cache_key] = (mtime, parsed)
    return parsed


def build_stress_payload(
    root: Path = ROOT,
    *,
    capital_usd: float = 50_000.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Build Black-Swan VND/USD loss matrix & Multi-Prop budget wipeout comparison scaled to any capital tier."""
    cap_usd = max(1_000.0, float(capital_usd))
    fx = max(1_000.0, float(usd_vnd_rate))
    cap_vnd = cap_usd * fx

    md_path = root / "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md"
    parsed = _parse_stress_and_multiprop_md(md_path)
    if parsed is None:
        return {
            "schema": "naqex-cockpit-stress-v1",
            "generated_utc": datetime.now(UTC).isoformat(),
            "order_send_count": ORDER_SEND_COUNT,
            "status": "pending",
            "available": False,
            "capital_usd": round(cap_usd, 2),
            "capital_vnd": round(cap_vnd, 0),
            "usd_vnd_rate": fx,
            "black_swan_matrix": [],
            "multi_prop_budgets": {},
        }

    # Owner PROFILE.md comfort thresholds by VND tier
    if cap_vnd >= 1_000_000_000.0:
        green_cap, amber_cap = 5.5, 10.0
    elif cap_vnd >= 100_000_000.0:
        green_cap, amber_cap = 10.0, 15.0
    else:
        green_cap, amber_cap = 15.0, 20.0

    def _scaled_loss(pct: float) -> dict[str, float]:
        usd = cap_usd * (pct / 100.0)
        return {
            "pct": round(pct, 2),
            "usd": round(usd, 2),
            "vnd_m": round((usd * fx) / 1_000_000.0, 1),
        }

    matrix: list[dict[str, Any]] = []
    for row in parsed["black_swan_allocators"]:
        wc_pct = float(row.get("worst_case_dd_pct") or max(row["cex_haircut_50_pct"], row["corr085_p99_dd_pct"]))
        if wc_pct <= green_cap:
            verdict = "COMFORT_GREEN"
        elif wc_pct <= amber_cap:
            verdict = "CAUTION_AMBER"
        else:
            verdict = "BREACH_RED"
        matrix.append({
            "allocator": row["allocator"],
            "cex_weight_pct": row["cex_weight_pct"],
            "dominant_shock": row.get("dominant_shock", "CEX_-50%_Haircut"),
            "verdict": verdict,
            "cex_30": _scaled_loss(row["cex_haircut_30_pct"]),
            "cex_50": _scaled_loss(row["cex_haircut_50_pct"]),
            "corr085_p99": _scaled_loss(row["corr085_p99_dd_pct"]),
            "rate2022_ftx": _scaled_loss(row["rate2022_ftx_dd_pct"]),
            "worst_case": _scaled_loss(wc_pct),
            "worst_1d_p99_pct": row["worst_1d_p99_pct"],
            "slip_3x_cagr_raw": row["slip_3x_cagr_raw"],
        })

    # Compact headline highlights for 500 / 1,500 / 3,000 USD Multi-Prop comparison
    mp_highlights: list[dict[str, Any]] = []
    for b_usd in (500, 1500, 3000):
        rows_b = parsed["multi_prop_budgets"].get(b_usd, [])
        for r in rows_b:
            if (r["architecture"] in ("DUAL_2FIRM_STAGGER_42D", "DUAL_2FIRM_SYNC", "LADDER_STAGGER_SCALE")) and (
                (r["architecture"] == "DUAL_2FIRM_STAGGER_42D" and r["profile"] == "Balanced")
                or (r["architecture"] == "DUAL_2FIRM_SYNC" and r["profile"] == "Sprint")
                or (r["architecture"] == "LADDER_STAGGER_SCALE" and r["profile"] == "Balanced")
            ):
                mp_highlights.append({"budget_usd": b_usd, **r})

    return {
        "schema": "naqex-cockpit-stress-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "report_generated_utc": parsed["generated_utc"],
        "source": parsed["source"],
        "order_send_count": ORDER_SEND_COUNT,
        "status": "AVAILABLE",
        "available": True,
        "capital_usd": round(cap_usd, 2),
        "capital_vnd": round(cap_vnd, 0),
        "capital_vnd_m": round(cap_vnd / 1_000_000.0, 1),
        "usd_vnd_rate": fx,
        "cex_group_cap_recommendation": {
            "max_combined_cex_pct": 25.0,
            "capped_cex50_loss": _scaled_loss(12.5),
            "capped_cex30_loss": _scaled_loss(7.5),
        },
        "black_swan_matrix": matrix,
        "multi_prop_highlights": mp_highlights,
        "multi_prop_budgets": {str(k): v for k, v in parsed["multi_prop_budgets"].items()},
    }


def compute_vnd_risk_calculator(
    *,
    capital_vnd: float = 250_000_000.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
    prop_nominal_usd: float = 10_000.0,
    risk_profile: str = "balanced",
    cost_mult: float = 1.0,
    root: Path = ROOT,
) -> dict[str, Any]:
    """VND/USD Absolute Risk, Red-Team Stress & Prop->Own-Book Calculator calibrated to `knowledge/owner/PROFILE.md`."""
    cap_vnd = max(0.0, float(capital_vnd))
    fx = max(1_000.0, float(usd_vnd_rate))
    cap_usd = cap_vnd / fx
    prop_nom = max(0.0, float(prop_nominal_usd))
    cm = max(0.5, min(3.5, float(cost_mult)))

    # Profile risk multipliers (synced with M2.2 & Holdout Funded Safe)
    profiles: dict[str, dict[str, Any]] = {
        "conservative": {
            "label": "Funded Safe (1.0x)",
            "mult": 1.0,
            "exp_cagr_pct": 10.5,
            "exp_peak_dd_pct": 6.5,
            "daily_dd_pct": 1.5,
            "risk_per_trade_pct": 0.50,
        },
        "balanced": {
            "label": "Quant Pod Balanced (4-Sleeve)",
            "mult": 1.0,
            "exp_cagr_pct": 18.0,
            "exp_peak_dd_pct": 8.0,
            "daily_dd_pct": 1.8,
            "risk_per_trade_pct": 0.50,
        },
        "p1_balanced": {
            "label": "Prop P1 Balanced (4.0x)",
            "mult": 4.0,
            "exp_cagr_pct": 30.0,
            "exp_peak_dd_pct": 9.2,
            "daily_dd_pct": 4.2,
            "risk_per_trade_pct": 1.50,
        },
        "p1_sprint": {
            "label": "Prop P1 Sprint (4.75x)",
            "mult": 4.75,
            "exp_cagr_pct": 36.0,
            "exp_peak_dd_pct": 9.5,
            "daily_dd_pct": 4.3,
            "risk_per_trade_pct": 1.75,
        },
    }
    prof = profiles.get(risk_profile.lower(), profiles["balanced"])

    # Pull real Red-Team stress curve if available
    red_team = as_dict(_safe_read_json(root / "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.json"))
    t1 = as_dict(red_team.get("test1_cost_stress"))
    p_curve_map = as_dict(t1.get("portfolio_curve"))
    p_be_map = as_dict(t1.get("portfolio_breakeven"))
    p7_curve = as_list(p_curve_map.get("PORT_7E"))
    p9_curve = as_list(p_curve_map.get("PORT_9E"))
    p7_interp = _interpolate_red_team_curve(p7_curve, cm)
    p9_interp = _interpolate_red_team_curve(p9_curve, cm)
    p7_be = float(as_dict(p_be_map.get("PORT_7E")).get("breakeven_mult", 2.26))
    p9_be = float(as_dict(p_be_map.get("PORT_9E")).get("breakeven_mult", 2.23))

    # Calibrate comfort band directly from knowledge/owner/PROFILE.md §3:
    # - Small test capital (< 100M VND): tolerates up to 15-20% DD
    # - Medium-large capital (100M - 1B VND): treats 15%-20% DD as too high (target <= 10%)
    # - Very large capital (>= 1B VND): treats 5% DD as significant (target <= 5-7%)
    exp_peak_dd = float(prof["exp_peak_dd_pct"])
    eff_dd_pct = exp_peak_dd if cm <= 1.0 else max(exp_peak_dd, float(p7_interp.get("peak_dd_pct", exp_peak_dd)))
    if cap_vnd >= 1_000_000_000.0:
        tier_label = "Vốn rất lớn (>= 1 tỷ VND — PROFILE.md: 5% DD đã đáng kể)"
        green_cap, amber_cap = 5.5, 8.0
    elif cap_vnd >= 100_000_000.0:
        tier_label = "Vốn trung–lớn (100 triệu – 1 tỷ VND — PROFILE.md: 15%–20% DD là quá cao)"
        green_cap, amber_cap = 10.0, 14.5
    else:
        tier_label = "Vốn thử nghiệm nhỏ (< 100 triệu VND — chịu được DD cao hơn)"
        green_cap, amber_cap = 15.0, 20.0

    if eff_dd_pct <= green_cap:
        comfort_verdict = "COMFORT_GREEN"
    elif eff_dd_pct <= amber_cap:
        comfort_verdict = "CAUTION_AMBER"
    else:
        comfort_verdict = "OVER_TOLERANCE_RED"

    one_r_usd = cap_usd * (float(prof["risk_per_trade_pct"]) / 100.0)
    daily_dd_usd = cap_usd * (float(prof["daily_dd_pct"]) / 100.0)
    peak_dd_usd = cap_usd * (eff_dd_pct / 100.0)
    giveback_2r_usd = one_r_usd * 2.0  # Behavioral check for profit-giveback discomfort!
    exp_annual_own_usd = cap_usd * (float(prof["exp_cagr_pct"]) / 100.0)

    crossover = compute_prop_own_crossover(
        own_book_equity_usd=cap_usd,
        active_prop_nominal_usd=prop_nom,
        prop_expected_ann_ret=max(0.0, p7_interp.get("ann_pct", 7.73) / 100.0) if p7_curve else 0.10,
        own_pod_expected_ann_ret=float(prof["exp_cagr_pct"]) / 100.0,
        avg_prop_split=0.80,
        firm_counterparty_haircut=0.10,
        annual_prop_fees_usd=210.0 if prop_nom > 0 else 0.0,
        usd_vnd_rate=fx,
    )

    # 4-sleeve own-book allocation breakdown (ERC_Capped35 baseline)
    sleeve_weights: list[dict[str, Any]] = [
        {"sleeve": "S1_PROP_FX_IDX", "label": "FX/Idx Intraday (PORT_7E)", "weight_pct": 24.0},
        {"sleeve": "S2_CRYPTO_SPOT", "label": "Crypto Spot Top-15 (F4_4H_EMA)", "weight_pct": 16.6},
        {"sleeve": "S3A_FUND_CARRY", "label": "Funding Carry 2xBuf (Cap <=20% live)", "weight_pct": 20.0},
        {"sleeve": "S3B_MACRO_ETF", "label": "18-Yr Macro ETF (M5_VOL_PARITY)", "weight_pct": 39.4},
    ]
    for sw in sleeve_weights:
        u = cap_usd * float(sw["weight_pct"]) / 100.0
        sw["usd"] = round(u, 2)
        sw["vnd"] = round(u * fx, 0)

    per_engine_stress = []
    for eng in as_list(t1.get("per_engine")):
        if not isinstance(eng, dict):
            continue
        c1 = float(eng.get("cost_1x_usd", 0.0))
        n1 = float(eng.get("net_1x_usd", 0.0))
        est_net = n1 - (cm - 1.0) * c1
        per_engine_stress.append({
            "engine": eng["engine"],
            "n_trades": eng["n_trades"],
            "breakeven_mult": eng["breakeven_mult"],
            "est_net_usd": round(est_net, 2),
            "survives": est_net > 0.0,
        })

    return {
        "schema": "naqex-vnd-risk-calculator-v1",
        "order_send_count": ORDER_SEND_COUNT,
        "inputs": {
            "capital_vnd": round(cap_vnd, 0),
            "capital_usd": round(cap_usd, 2),
            "usd_vnd_rate": fx,
            "prop_nominal_usd": round(prop_nom, 2),
            "risk_profile": risk_profile,
            "profile_label": prof["label"],
            "cost_mult": round(cm, 2),
        },
        "absolute_pain_table": {
            "one_r_stop_usd": round(one_r_usd, 2),
            "one_r_stop_vnd": round(one_r_usd * fx, 0),
            "profit_giveback_2r_usd": round(giveback_2r_usd, 2),
            "profit_giveback_2r_vnd": round(giveback_2r_usd * fx, 0),
            "daily_dd_usd": round(daily_dd_usd, 2),
            "daily_dd_vnd": round(daily_dd_usd * fx, 0),
            "expected_peak_dd_pct": round(eff_dd_pct, 2),
            "expected_peak_dd_usd": round(peak_dd_usd, 2),
            "expected_peak_dd_vnd": round(peak_dd_usd * fx, 0),
            "expected_annual_return_usd": round(exp_annual_own_usd, 2),
            "expected_annual_return_vnd": round(exp_annual_own_usd * fx, 0),
        },
        "owner_profile_assessment": {
            "capital_tier": tier_label,
            "green_dd_cap_pct": green_cap,
            "amber_dd_cap_pct": amber_cap,
            "verdict": comfort_verdict,
        },
        "red_team_stress": {
            "cost_mult": round(cm, 2),
            "PORT_7E": {**p7_interp, "breakeven_mult": p7_be, "headroom_mult": round(p7_be - cm, 2)},
            "PORT_9E": {**p9_interp, "breakeven_mult": p9_be, "headroom_mult": round(p9_be - cm, 2)},
            "per_engine": per_engine_stress,
        },
        "crossover": crossover,
        "own_book_sleeve_allocation": sleeve_weights,
    }
