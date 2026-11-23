"""M8.2 — Pass 32: Leave-One-Out (LOO) Engine Pruning & Causal Allocation/Regime-Conditioning Audit (DEV < 2025 ONLY!).

STRICT SEALED DEVELOPMENT & GOVERNANCE BOUNDARIES:
  - Asserts NATIVE_FTMO_HOLDOUT_LOCK.json SHA integrity on startup (`holdout_rows_analysed = 0`, `OrderSend = 0`).
  - Loads frozen Dev 9-engine tapes via `build_or_load_frozen_tapes(force_rebuild=False)` (max day < 2025-01-01).
  - NEVER modifies `PORTFOLIO-REGISTRY.json` or frozen `PORT_7E` / `PORT_9E`; any winner is proposed strictly as a
    v2 research candidate only.
  - HARD CAP: M_TOTAL_CAP = 20 (`len(variants) <= 20`).
  - Strict split: Cluster A (`2018-2021`) for ALL weight fitting, LOO pruning, and volatility-target calibration ->
    Blind Cluster B (`2022-2024`) for out-of-sample Calmar, MaxDD, Ann%, and 2,000-path FTMO Swing P1 pass speed!
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from math import fsum
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_firm_config,
    load_registry,
)
from quant_factory.portfolio_allocator import weights_erc, weights_hrp
from quant_factory.prop_engine import (
    evaluate_firm_profile,
    make_block_bootstrap_indices,
    replay_portfolio_m1,
)

M_TOTAL_CAP = 20
SEED = 20261124
CLUSTER_A_PREFIXES = ("2018", "2019", "2020", "2021")
CLUSTER_B_PREFIXES = ("2022", "2023", "2024")


def _extract_daily_series(days_sorted: list[str], exits: list[dict[str, Any]], initial: float = 10000.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    by_day = {e["day"]: e for e in exits}
    n = len(days_sorted)
    nets = np.zeros(n, dtype=np.float64)
    dds = np.zeros(n, dtype=np.float64)
    flgs = np.zeros(n, dtype=np.int8)
    prev_cash = float(initial)
    for i, dk in enumerate(days_sorted):
        e = by_day.get(dk)
        if e is not None:
            nets[i] = float(e["net_usd"])
            dds[i] = max(0.0, prev_cash - float(e["day_equity_minimum"]))
            flgs[i] = 1
            prev_cash = float(e["cash"])
    return nets, dds, flgs


def _causal_vol_throttle(
    days_sorted: list[str],
    nets: np.ndarray,
    dds: np.ndarray,
    *,
    fit_cutoff_day: str = "2022-01-01",
    window: int = 20,
    lo: float = 0.55,
    hi: float = 1.35,
) -> tuple[np.ndarray, np.ndarray]:
    """Strictly causal 20-day Moreira-Muir vol-regime throttle fitted ONLY on days < fit_cutoff_day."""
    idx_split = sum(1 for d in days_sorted if d < fit_cutoff_day)
    target_vol = float(np.std(nets[:max(60, idx_split)], ddof=1))
    out_n = nets.copy()
    out_d = dds.copy()
    if target_vol <= 1e-9:
        return out_n, out_d
    for i in range(window, len(nets)):
        rv = float(np.std(nets[i - window:i], ddof=1))
        if rv > 1e-6:
            mult = float(np.clip(target_vol / rv, lo, hi))
            out_n[i] = nets[i] * mult
            out_d[i] = dds[i] * mult
    return out_n, out_d


def _metrics_from_net_dd(nets: np.ndarray, dds: np.ndarray, n_years: float, initial: float = 10000.0) -> dict[str, Any]:
    bal = float(initial)
    peak = float(initial)
    max_dd = 0.0
    max_daily = 0.0
    for net, dd in zip(nets, dds):
        day_min = bal - float(dd)
        if peak - day_min > max_dd:
            max_dd = peak - day_min
        if float(dd) > max_daily:
            max_daily = float(dd)
        bal += float(net)
        if bal > peak:
            peak = bal
    ann_pct = 100.0 * ((bal - initial) / max(1e-6, n_years)) / initial
    dd_pct = 100.0 * max_dd / initial
    daily_pct = 100.0 * max_daily / initial
    calmar = (ann_pct / dd_pct) if dd_pct > 1e-9 else 0.0
    sd = float(np.std(nets / initial, ddof=1)) if len(nets) > 2 else 0.0
    sharpe = (float(np.mean(nets / initial)) / sd * np.sqrt(252.0)) if sd > 1e-12 else 0.0
    return {
        "net_usd": round(bal - initial, 2),
        "ann_pct": round(ann_pct, 2),
        "peak_dd_pct": round(dd_pct, 2),
        "daily_loss_pct": round(daily_pct, 2),
        "calmar": round(calmar, 3),
        "sharpe": round(sharpe, 3),
    }


def _causal_cluster_a_weights(
    method: str,
    eng_ids: list[str],
    days_a: list[str],
    tapes: dict[str, Any],
    total_budget: float,
    eng_daily_a_mat: np.ndarray,
    eng_dd_a: dict[str, float],
) -> dict[str, float]:
    """Fit portfolio risk weights STRICTLY on Cluster A (2018-2021) data (zero Cluster B leakage!)."""
    k = len(eng_ids)
    if method == "EQUAL":
        return {e: total_budget / k for e in eng_ids}
    if method == "INV_DD":
        inv = {e: 1.0 / max(0.30, eng_dd_a[e]) for e in eng_ids}
        s = fsum(inv.values())
        return {e: total_budget * inv[e] / s for e in eng_ids}
    if method == "HRP":
        w = weights_hrp(eng_daily_a_mat)
        return {e: float(total_budget * w[i]) for i, e in enumerate(eng_ids)}
    if method == "ERC":
        w = weights_erc(eng_daily_a_mat)
        return {e: float(total_budget * w[i]) for i, e in enumerate(eng_ids)}
    raise ValueError(f"Unknown causal weight method: {method}")


def run_pass32(*, cache_dir: Path | None = None, jobs_root: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    reg = load_registry()
    kwargs = {"force_rebuild": False}
    if cache_dir is not None:
        kwargs["cache_dir"] = cache_dir
    if jobs_root is not None:
        kwargs["jobs_root"] = jobs_root
    warm = build_or_load_frozen_tapes(**kwargs)
    tapes = warm["tapes"]
    ext_days = sorted(warm["ext_days"])
    assert max(ext_days) < "2025-01-01", f"HOLDOUT_CONTAMINATION:{max(ext_days)}"

    days_a = [d for d in ext_days if d[:4] in CLUSTER_A_PREFIXES]
    days_b = [d for d in ext_days if d[:4] in CLUSTER_B_PREFIXES]
    idx_a = np.array([d[:4] in CLUSTER_A_PREFIXES for d in ext_days])
    idx_b = np.array([d[:4] in CLUSTER_B_PREFIXES for d in ext_days])

    core7 = list(reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"])
    turbo9 = list(reg["frozen_portfolios"]["PORT_9E_P28_TURBO"]["engines"])
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7_base = {e: base_r[e] for e in core7}
    risks9_base = {e: base_r[e] for e in turbo9}
    budget7 = fsum(risks7_base.values())
    budget9 = fsum(risks9_base.values())

    # Check if Pass 31 produced any Red-Team-approved survivor (read-only)
    p31_summary_path = ROOT / ".runtime" / "quant-pod-returns" / "pass31_redteam_summary.json"
    p31_survivors = []
    if p31_summary_path.exists():
        p31_data = json.loads(p31_summary_path.read_text(encoding="utf-8"))
        p31_survivors = list(p31_data.get("passed_ids", []))

    # ==========================================================================
    # PART 1: STANDALONE & LEAVE-ONE-OUT (LOO) ENGINE CONTRIBUTION AUDIT (9E)
    # ==========================================================================
    m9_a, ex9_a = replay_portfolio_m1(days_a, tapes, risks9_base, 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=0.010)
    m9_b, ex9_b = replay_portfolio_m1(days_b, tapes, risks9_base, 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=0.010)

    eng_daily_a: dict[str, np.ndarray] = {}
    eng_dd_a: dict[str, float] = {}
    loo_rows: list[dict[str, Any]] = []

    for e in turbo9:
        sa, ex_sa = replay_portfolio_m1(days_a, tapes, {e: 0.005}, 10000.0, profile_mode="Swing")
        sb, _ = replay_portfolio_m1(days_b, tapes, {e: 0.005}, 10000.0, profile_mode="Swing")
        n_sa, _, _ = _extract_daily_series(days_a, ex_sa, 10000.0)
        eng_daily_a[e] = n_sa / 10000.0
        eng_dd_a[e] = max(0.30, float(sa["peak_dd_pct"]))

        # Leave-One-Out replay on PORT_9E (removing engine `e`)
        sub_risks = {k: v for k, v in risks9_base.items() if k != e}
        la, ex_la = replay_portfolio_m1(days_a, tapes, sub_risks, 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=0.010)
        lb, _ = replay_portfolio_m1(days_b, tapes, sub_risks, 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=0.010)
        n_la, _, _ = _extract_daily_series(days_a, ex_la, 10000.0)
        corr_rest_a = float(np.corrcoef(n_sa, n_la)[0, 1]) if (np.std(n_sa) > 1e-12 and np.std(n_la) > 1e-12) else 0.0

        # Positive delta_calmar means REMOVING e HURTS portfolio (so e is valuable!); negative means e was a drag!
        loo_rows.append({
            "engine": e,
            "role": "CORE_7E" if e in core7 else "SATELLITE",
            "trades_a": sum(1 for dk in days_a if dk in tapes[e]),
            "trades_b": sum(1 for dk in days_b if dk in tapes[e]),
            "standalone_a": {"ann_pct": sa["ann_pct"]["all"], "peak_dd_pct": sa["peak_dd_pct"], "calmar": sa["calmar"]},
            "standalone_b": {"ann_pct": sb["ann_pct"]["all"], "peak_dd_pct": sb["peak_dd_pct"], "calmar": sb["calmar"]},
            "corr_vs_rest_a": round(corr_rest_a, 4),
            "loo_contrib_calmar_a": round(float(m9_a["calmar"]) - float(la["calmar"]), 3),
            "loo_contrib_calmar_b": round(float(m9_b["calmar"]) - float(lb["calmar"]), 3),
            "loo_contrib_ann_b": round(float(m9_b["ann_pct"]["all"]) - float(lb["ann_pct"]["all"]), 2),
            "loo_contrib_dd_b": round(float(m9_b["peak_dd_pct"]) - float(lb["peak_dd_pct"]), 2),
        })

    # Strictly CAUSAL Cluster-A ranking for LOO pruning (ZERO peeking at Cluster B!)
    ranked_a = sorted(loo_rows, key=lambda r: (r["loo_contrib_calmar_a"], r["standalone_a"]["calmar"]), reverse=True)
    top7_causal_a = [r["engine"] for r in ranked_a[:7]]
    top6_causal_a = [r["engine"] for r in ranked_a[:6]]
    pruned_drop2_a = [r["engine"] for r in ranked_a[7:]]
    pruned_drop3_a = [r["engine"] for r in ranked_a[6:]]

    # Build aligned Cluster A daily return matrices per subset
    def _mat_a(eids: list[str]) -> np.ndarray:
        return np.column_stack([eng_daily_a[e] for e in eids])

    # ==========================================================================
    # PART 2: PREREGISTERED CAUSAL ALLOCATION & REGIME VARIANTS (m_total = 12 <= 20)
    # ==========================================================================
    variant_specs: list[dict[str, Any]] = [
        {"id": "V01_INCUMBENT_PORT7E_BASE", "desc": "Frozen PORT_7E registry weights (SYMCAP 1.00%)", "engines": core7, "risks": risks7_base, "vol_throttle": False},
        {"id": "V02_INCUMBENT_PORT7E_INVDD", "desc": "Frozen PORT_7E Causal Cl.A Inv-DD (SYMCAP 1.00%)", "engines": core7,
         "risks": _causal_cluster_a_weights("INV_DD", core7, days_a, tapes, budget7, _mat_a(core7), eng_dd_a), "vol_throttle": False},
        {"id": "V03_INCUMBENT_PORT9E_INVDD", "desc": "Frozen PORT_9E Causal Cl.A Inv-DD (SYMCAP 1.00%)", "engines": turbo9,
         "risks": _causal_cluster_a_weights("INV_DD", turbo9, days_a, tapes, budget9, _mat_a(turbo9), eng_dd_a), "vol_throttle": False},
        {"id": "V04_PORT9E_EQUAL_RISK", "desc": "9E Equal Risk Budget (SYMCAP 1.00%)", "engines": turbo9,
         "risks": _causal_cluster_a_weights("EQUAL", turbo9, days_a, tapes, budget9, _mat_a(turbo9), eng_dd_a), "vol_throttle": False},
        {"id": "V05_PORT7E_EQUAL_RISK", "desc": "7E Equal Risk Budget (SYMCAP 1.00%)", "engines": core7,
         "risks": _causal_cluster_a_weights("EQUAL", core7, days_a, tapes, budget7, _mat_a(core7), eng_dd_a), "vol_throttle": False},
        {"id": "V06_PORT9E_CAUSAL_HRP", "desc": "9E Causal Cl.A HRP (Lopez de Prado, SYMCAP 1.00%)", "engines": turbo9,
         "risks": _causal_cluster_a_weights("HRP", turbo9, days_a, tapes, budget9, _mat_a(turbo9), eng_dd_a), "vol_throttle": False},
        {"id": "V07_PORT7E_CAUSAL_HRP", "desc": "7E Causal Cl.A HRP (SYMCAP 1.00%)", "engines": core7,
         "risks": _causal_cluster_a_weights("HRP", core7, days_a, tapes, budget7, _mat_a(core7), eng_dd_a), "vol_throttle": False},
        {"id": "V08_PORT9E_CAUSAL_ERC", "desc": "9E Causal Cl.A Equal Risk Contribution (SYMCAP 1.00%)", "engines": turbo9,
         "risks": _causal_cluster_a_weights("ERC", turbo9, days_a, tapes, budget9, _mat_a(turbo9), eng_dd_a), "vol_throttle": False},
        {"id": "V09_PRUNED_TOP6_CAUSAL_INVDD", "desc": f"LOO-Pruned Top-6 (drop {','.join(pruned_drop3_a)} on Cl.A) Inv-DD", "engines": top6_causal_a,
         "risks": _causal_cluster_a_weights("INV_DD", top6_causal_a, days_a, tapes, budget7, _mat_a(top6_causal_a), eng_dd_a), "vol_throttle": False},
        {"id": "V10_PRUNED_TOP7_CAUSAL_HRP", "desc": f"LOO-Pruned Top-7 (drop {','.join(pruned_drop2_a)} on Cl.A) HRP", "engines": top7_causal_a,
         "risks": _causal_cluster_a_weights("HRP", top7_causal_a, days_a, tapes, budget7, _mat_a(top7_causal_a), eng_dd_a), "vol_throttle": False},
        {"id": "V11_PORT7E_CAUSAL_VOL_THROTTLE", "desc": "PORT_7E Base + Causal 20d Vol-Regime Throttle [0.55, 1.35]", "engines": core7,
         "risks": risks7_base, "vol_throttle": True},
        {"id": "V12_PORT9E_HRP_VOL_THROTTLE", "desc": "9E Causal HRP + Causal 20d Vol-Regime Throttle [0.55, 1.35]", "engines": turbo9,
         "risks": _causal_cluster_a_weights("HRP", turbo9, days_a, tapes, budget9, _mat_a(turbo9), eng_dd_a), "vol_throttle": True},
    ]
    assert len(variant_specs) <= M_TOTAL_CAP, f"Variants {len(variant_specs)} exceeds HARD CAP {M_TOTAL_CAP}"

    # Evaluate every variant on exact M1 Prague-reset Dev + blind Cluster B + 2,000-path FTMO Swing MC
    firm_swing = load_firm_config("ftmo_swing_10k")
    prof_bal = {
        "id": "P1_BALANCED_4X_M22",
        "p1_mult": 4.0, "p2_mult": 2.5, "funded_mult": 1.0,
        "amber_dd_pct": 0.050, "amber_mult": 0.65,
        "red_dd_pct": 0.075, "red_mult": 0.40,
        "ea_daily_stop_pct": 0.038,
    }
    idx_mat_all = make_block_bootstrap_indices(len(ext_days), horizon=504, n_paths=2000, block_len=5, seed=SEED)
    idx_mat_b = make_block_bootstrap_indices(len(days_b), horizon=504, n_paths=2000, block_len=5, seed=SEED + 1)

    variant_rows: list[dict[str, Any]] = []
    for vs in variant_specs:
        _, ex_all = replay_portfolio_m1(ext_days, tapes, vs["risks"], 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=0.010)
        nets, dds, flgs = _extract_daily_series(ext_days, ex_all, 10000.0)
        if vs["vol_throttle"]:
            nets, dds = _causal_vol_throttle(ext_days, nets, dds, fit_cutoff_day="2022-01-01", window=20, lo=0.55, hi=1.35)

        met_a = _metrics_from_net_dd(nets[idx_a], dds[idx_a], 4.0, 10000.0)
        met_b = _metrics_from_net_dd(nets[idx_b], dds[idx_b], 3.0, 10000.0)
        met_all = _metrics_from_net_dd(nets, dds, 7.0, 10000.0)

        mc_all = evaluate_firm_profile(idx_mat_all, (nets, dds, flgs), (nets, dds, flgs), firm_swing, prof_bal)
        mc_b = evaluate_firm_profile(idx_mat_b, (nets[idx_b], dds[idx_b], flgs[idx_b]), (nets[idx_b], dds[idx_b], flgs[idx_b]), firm_swing, prof_bal)

        variant_rows.append({
            "id": vs["id"],
            "desc": vs["desc"],
            "n_engines": len(vs["engines"]),
            "vol_throttle": vs["vol_throttle"],
            "weights_pct": {k: round(v * 100.0, 3) for k, v in vs["risks"].items()},
            "cluster_a_2018_2021": met_a,
            "cluster_b_2022_2024": met_b,
            "dev_all_2018_2024": met_all,
            "mc_ftmo_swing_dev": {
                "pass_3m": mc_all["pass_3m"], "pass_6m": mc_all["pass_6m"],
                "med_pass_m": mc_all["med_pass_m"], "br1_pct": mc_all["br1_pct"], "cf24_mean": mc_all["cf24_mean"],
            },
            "mc_ftmo_swing_cluster_b": {
                "pass_3m": mc_b["pass_3m"], "pass_6m": mc_b["pass_6m"],
                "med_pass_m": mc_b["med_pass_m"], "br1_pct": mc_b["br1_pct"], "cf24_mean": mc_b["cf24_mean"],
            },
        })

    # Compare against incumbent baselines strictly honestly
    by_id = {r["id"]: r for r in variant_rows}
    inc_7e_invdd = by_id["V02_INCUMBENT_PORT7E_INVDD"]
    inc_9e_invdd = by_id["V03_INCUMBENT_PORT9E_INVDD"]
    non_inc = [r for r in variant_rows if not r["id"].startswith("V01_") and not r["id"].startswith("V02_") and not r["id"].startswith("V03_")]
    # Strictly Cluster-A-selected v2 challenger (zero peeking at Cluster B!)
    best_challenger_a = max(non_inc, key=lambda r: r["cluster_a_2018_2021"]["calmar"])
    beats_7e_b_calmar = best_challenger_a["cluster_b_2022_2024"]["calmar"] > inc_7e_invdd["cluster_b_2022_2024"]["calmar"]
    beats_9e_b_calmar = best_challenger_a["cluster_b_2022_2024"]["calmar"] > inc_9e_invdd["cluster_b_2022_2024"]["calmar"]

    summary = {
        "schema": "naqex-pass32-pruning-regime-dev-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "m_total_cap": M_TOTAL_CAP,
        "m_total_variants": len(variant_specs),
        "pass31_survivors_integrated": p31_survivors,
        "causal_pruning_from_cluster_a": {
            "ranked_order_a": [r["engine"] for r in ranked_a],
            "pruned_drop2_a": pruned_drop2_a,
            "pruned_drop3_a": pruned_drop3_a,
        },
        "loo_audit_9e": loo_rows,
        "variants": variant_rows,
        "challenger_selected_on_cluster_a": best_challenger_a["id"],
        "beats_incumbent_7e_invdd_on_blind_cluster_b_calmar": beats_7e_b_calmar,
        "beats_incumbent_9e_invdd_on_blind_cluster_b_calmar": beats_9e_b_calmar,
    }
    out_p = ROOT / ".runtime" / "quant-pod-returns" / "pass32_pruning_regime_summary.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="M8.2 Pass 32 LOO Engine Pruning & Causal Allocation/Regime Audit (Dev < 2025 ONLY)")
    ap.parse_args()
    s = run_pass32()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "holdout_rows_analysed": s["holdout_rows_analysed"],
        "m_total_variants": s["m_total_variants"],
        "pass31_survivors_integrated": s["pass31_survivors_integrated"],
        "challenger_selected_on_cluster_a": s["challenger_selected_on_cluster_a"],
        "beats_7e_b": s["beats_incumbent_7e_invdd_on_blind_cluster_b_calmar"],
        "beats_9e_b": s["beats_incumbent_9e_invdd_on_blind_cluster_b_calmar"],
        "variants_table": [
            (r["id"], r["cluster_a_2018_2021"]["calmar"], r["cluster_b_2022_2024"]["ann_pct"], r["cluster_b_2022_2024"]["peak_dd_pct"], r["cluster_b_2022_2024"]["calmar"], r["mc_ftmo_swing_cluster_b"]["med_pass_m"], r["mc_ftmo_swing_cluster_b"]["cf24_mean"])
            for r in s["variants"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
