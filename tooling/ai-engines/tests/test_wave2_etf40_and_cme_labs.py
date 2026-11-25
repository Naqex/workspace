"""Wave-2 Cycle 2B/3A Tests: Lab #4 (40-ETF Multi-Factor + VRP) & Lab #5 (CME Micro Futures Prop).

Covers:
  1. Strict bit-for-bit anti-lookahead future-mutation proof for ALL 4 Lab #4 strategies.
  2. Zero pre-listing allocation, zero weight on signal-only indices (^VIX, ^VIX3M), gross <= 1.0x.
  3. Research Council wiring, OrderSend == 0, Sleeve #4 export schema & loader compatibility.
  4. Lab #5 MC determinism, unique-path pass_ever_pct <= 100%, EOD trailing DD trigger,
     consistency rule (50%/40%) enforcement, and Holdout 2025+ (< 2025-01-01) seal.
  5. Markdown report hygiene (< 900 KB, YAML frontmatter, 0 bare $, 0 broken relative links,
     exact JSON-to-MD numeric fidelity).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import re
import sys

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory import cme_futures_prop_lab as lab5
from quant_factory import etf40_multifactor_vrp_lab as lab4
from quant_factory.data_store import assert_holdout_locked
from quant_factory.portfolio_allocator import load_external_sleeve_json

LAB4_SUMMARY_PATH = ROOT / ".runtime" / "etf40-cache" / "etf40_study_summary.json"
LAB5_SUMMARY_PATH = ROOT / ".runtime" / "cme-futures-cache" / "cme_prop_study_summary.json"
LAB4_MD_PATH = ROOT / "planning" / "research" / "LAB4-40ETF-MULTIFACTOR-VRP-20261124.md"
LAB5_MD_PATH = ROOT / "planning" / "research" / "LAB5-CME-FUTURES-PROP-STUDY-20261124.md"


# ===========================================================================
# 1. Lab #4: Anti-Lookahead Future-Mutation & Portfolio Invariants
# ===========================================================================


def test_lab4_strict_anti_lookahead_future_mutation_and_signal_only_invariants() -> None:
    """Mutating all prices & VIX strictly after cutoff day T must leave weights[:T+1] bit-for-bit identical."""
    assert lab4.ORDER_SEND_COUNT == 0
    panel = lab4.load_etf40_panel()
    dates = panel["dates"]
    syms = panel["symbols"]
    px = panel["adjclose"]
    assert len(syms) == 40
    assert px.shape[0] > 4000

    cutoff = 3800  # Inside Cluster B (2020+), well after all late-listed ETFs (e.g. XLRE) are active
    assert dates[cutoff] >= "2019-01-01"

    base_strats = lab4.build_etf40_strategies(panel)

    # Wildly mutate all data strictly AFTER cutoff
    px_mut = px.copy()
    finite_future = np.isfinite(px_mut[cutoff + 1:])
    px_mut[cutoff + 1:][finite_future] *= 4.75
    sym_idx = {s: i for i, s in enumerate(syms)}
    px_mut[cutoff + 1:, sym_idx["^VIX"]] = 95.0
    px_mut[cutoff + 1:, sym_idx["^VIX3M"]] = 12.0

    panel_mut = {**panel, "adjclose": px_mut}
    mut_strats = lab4.build_etf40_strategies(panel_mut)

    expected_names = (
        "E40_RSI2_CONNORS",
        "E40_CREDIT_HYG_IEF_REGIME",
        "E40_XSEC_SECTOR_MOM_TOP4",
        "E40_VRP_VOL_CARRY",
    )
    for name in expected_names:
        w_base = base_strats[name]["weights"]
        w_mut = mut_strats[name]["weights"]
        # 1. Strict causality: bit-for-bit identical up through cutoff
        assert np.array_equal(w_base[: cutoff + 1], w_mut[: cutoff + 1]), f"Lookahead detected in {name}!"
        # 2. Signal-only indices (^VIX, ^VIX3M) must NEVER receive weight
        for sig_t in lab4.SIGNAL_ONLY_TICKERS:
            j = sym_idx[sig_t]
            assert float(np.max(np.abs(w_base[:, j]))) == 0.0, f"{name} allocated to signal-only {sig_t}"
        # 3. Zero pre-listing allocation (NaN price -> strictly 0.0 weight)
        nan_mask = ~np.isfinite(px)
        assert float(np.max(np.abs(w_base[nan_mask]))) == 0.0, f"{name} allocated to pre-listing NaN asset"
        # 4. Long-only & gross cap <= 1.0x
        assert float(np.min(w_base)) >= -1e-12
        assert float(np.max(np.sum(w_base, axis=1))) <= 1.0 + 1e-9


def test_lab4_summary_council_and_sleeve4_export_integrity() -> None:
    assert LAB4_SUMMARY_PATH.exists(), "Lab #4 summary JSON missing"
    summary = json.loads(LAB4_SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["schema"] == "naqex-lab4-etf40-summary-v1"
    assert summary["order_send_count"] == 0
    assert summary["holdout_rows_analysed"] == 0
    assert summary["universe_loaded"] == 40
    assert summary["skipped_tickers"] == []
    assert summary["primary_selected_on_cluster_a"] == "E40_VRP_VOL_CARRY"
    assert len(summary["council_approved"]) == 4

    for name, rec in summary["results"].items():
        assert rec["council_verdict"] == "APPROVE_FOR_INCUBATION", f"{name} verdict unexpected"
        assert rec["council_failed_gates"] == []
        assert len(rec["council_sha16"]) == 16
        assert rec["metrics_b_1x"]["cagr_pct"] > 0.0
        assert rec["metrics_b_2x"]["cagr_pct"] > 0.0

    # Sleeve #4 JSON export & compatibility with portfolio_allocator loader
    assert lab4.SLEEVE4_RETURNS_PATH.exists()
    sleeve = json.loads(lab4.SLEEVE4_RETURNS_PATH.read_text(encoding="utf-8"))
    assert sleeve["schema"] == "naqex-sleeve-daily-returns-v1"
    assert sleeve["sleeve_id"] == "S4_ETF40_MULTIFACTOR"
    assert sleeve["order_send_count"] == 0
    assert len(sleeve["daily_returns"]) == summary["cluster_a_days"] + summary["cluster_b_days"]
    ens_var = sleeve["variants"]["E40_APPROVED_EQW_ENSEMBLE"]
    assert len(ens_var["daily_returns"]) == len(sleeve["daily_returns"])
    assert len(ens_var["members"]) == 4

    loaded_ret_map, loaded_meta = load_external_sleeve_json(lab4.SLEEVE4_RETURNS_PATH)
    assert loaded_meta["sleeve_id"] == "S4_ETF40_MULTIFACTOR"
    assert len(loaded_ret_map) == len(sleeve["daily_returns"])
    assert all(np.isfinite(v) for v in loaded_ret_map.values())


# ===========================================================================
# 2. Lab #5: CME Micro Futures Prop MC Unit & Invariant Tests
# ===========================================================================


def test_lab5_mc_determinism_and_unique_path_pass_rate_cap() -> None:
    """High-win synthetic PnL must remain <= 100.0% pass_ever_pct even if funded resets occur."""
    assert lab5.ORDER_SEND_COUNT == 0
    rules = lab5.TOPSTEP_50K
    # Alternating strong wins and occasional large drawdown to trigger funded breach & re-pass
    rng = np.random.default_rng(42)
    synth = rng.choice([750.0, 500.0, -400.0, -900.0], size=200, p=[0.40, 0.30, 0.20, 0.10])

    r1 = lab5.simulate_futures_prop_mc(synth, rules, eval_scale=1.5, funded_scale=1.5, n_paths=400, seed=20261124)
    r2 = lab5.simulate_futures_prop_mc(synth, rules, eval_scale=1.5, funded_scale=1.5, n_paths=400, seed=20261124)
    assert r1 == r2, "MC must be 100% deterministic for fixed seed"

    assert 0.0 <= r1["pass_3m_pct"] <= r1["pass_6m_pct"] <= r1["pass_ever_pct"] <= 100.0
    assert 0.0 <= r1["p_pay3_pct"] <= r1["p_pay1_pct"] <= 100.0
    assert 0.0 <= r1["fail_1try_pct"] <= 100.0


def test_lab5_eod_trailing_drawdown_and_consistency_rule_enforcement() -> None:
    """Directly verify EOD trailing drawdown (tracks equity peak!) and consistency rule (50%/40%)."""
    base_rules = lab5.TOPSTEP_50K
    tradeify_rules = lab5.TRADEIFY_50K_GROWTH
    assert base_rules.consistency_max_day_share == 0.50
    assert tradeify_rules.consistency_max_day_share == 0.40

    # Case A: EOD Trailing DD check on constant -600/day loss stream (breaches 2,000 EOD DD within 4 days)
    eod_rules = dataclasses.replace(base_rules, max_attempts=1)
    seq_loss = np.full(40, -600.0, dtype=np.float64)
    res_loss = lab5.simulate_futures_prop_mc(
        seq_loss,
        eod_rules,
        eval_scale=1.0,
        funded_scale=1.0,
        n_paths=50,
        horizon_days=20,
        block_len=5,
        seed=7,
    )
    assert res_loss["fail_1try_pct"] == 100.0
    assert res_loss["pass_ever_pct"] == 0.0

    # Case B: Consistency Rule (50% Topstep / 40% Tradeify):
    # A single giant day of +3,100 USD hits the 3,000 target, yet with 50% consistency rule
    # req_target becomes 3,100 / 0.50 = 6,200 USD (and 7,750 USD under Tradeify 40%)!
    seq_spike = np.array([3100.0] + [0.0] * 39, dtype=np.float64)
    rules_no_cons = dataclasses.replace(base_rules, consistency_max_day_share=0.0, max_attempts=1)
    rules_50_cons = dataclasses.replace(base_rules, consistency_max_day_share=0.50, max_attempts=1)
    rules_40_cons = dataclasses.replace(tradeify_rules, consistency_max_day_share=0.40, max_attempts=1)
    res_no_cons = lab5.simulate_futures_prop_mc(
        seq_spike, rules_no_cons, eval_scale=1.0, funded_scale=1.0, n_paths=200, horizon_days=10, block_len=5, seed=123
    )
    res_50_cons = lab5.simulate_futures_prop_mc(
        seq_spike, rules_50_cons, eval_scale=1.0, funded_scale=1.0, n_paths=200, horizon_days=10, block_len=5, seed=123
    )
    res_40_cons = lab5.simulate_futures_prop_mc(
        seq_spike, rules_40_cons, eval_scale=1.0, funded_scale=1.0, n_paths=200, horizon_days=10, block_len=5, seed=123
    )
    assert res_no_cons["pass_ever_pct"] > res_50_cons["pass_ever_pct"] >= res_40_cons["pass_ever_pct"]


def test_lab5_summary_holdout_seal_and_sleeve5_export() -> None:
    assert LAB5_SUMMARY_PATH.exists(), "Lab #5 summary JSON missing"
    summary = json.loads(LAB5_SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["schema"] == "naqex-lab5-cme-prop-summary-v1"
    assert summary["order_send_count"] == 0
    assert summary["holdout_rows_analysed"] == 0
    assert summary["n_paths"] == 5000
    assert summary["seed"] == 20261124

    # Verify Holdout 2025+ lock SHA-256 unchanged
    expected_sha = assert_holdout_locked()
    assert summary["holdout_lock_sha256"] == expected_sha

    # All 6 CME Micro Yahoo telemetry feeds OK
    tel = summary["yahoo_futures_telemetry"]
    assert set(tel.keys()) == {"MES", "MNQ", "MGC", "MCL", "M6E", "M6J"}
    for code, row in tel.items():
        assert row["status"] == "OK", f"{code} telemetry failed"
        assert row["d1_rows"] >= 1500
        assert row["h1_rows"] >= 500

    # All 18 MC rows have valid probability invariants
    assert len(summary["mc_sweeps"]) == 18
    for row in summary["mc_sweeps"]:
        assert 0.0 <= row["pass_3m_pct"] <= row["pass_6m_pct"] <= row["pass_ever_pct"] <= 100.0
        assert 0.0 <= row["p_pay3_pct"] <= row["p_pay1_pct"] <= 100.0
        assert 0.0 <= row["fail_1try_pct"] <= 100.0

    # Strict accounting identity: per-engine rows MUST sum exactly to total_cme_net_usd & total_cfd_net_usd
    for key in (
        "dev_cost_mapping_all_micros",
        "dev_cost_mapping_mnq_mgc_400r",
        "dev_cost_mapping_fractional_micros",
    ):
        blk = summary[key]
        sum_cme = sum(e["cme_net_usd"] for e in blk["per_engine"])
        sum_cfd = sum(e["cfd_net_usd"] for e in blk["per_engine"])
        assert abs(sum_cme - blk["total_cme_net_usd"]) <= 0.05, f"{key} CME sum mismatch: {sum_cme} vs {blk['total_cme_net_usd']}"
        assert abs(sum_cfd - blk["total_cfd_net_usd"]) <= 0.05, f"{key} CFD sum mismatch: {sum_cfd} vs {blk['total_cfd_net_usd']}"

    # Sleeve #5 JSON strictly Dev-only (< 2025-01-01)
    assert lab5.SLEEVE5_RETURNS_PATH.exists()
    s5 = json.loads(lab5.SLEEVE5_RETURNS_PATH.read_text(encoding="utf-8"))
    assert s5["schema"] == "naqex-sleeve-daily-returns-v1"
    assert s5["sleeve_id"] == "S5_CME_FUTURES_PROP"
    assert s5["holdout_rows_analysed"] == 0
    assert s5["holdout_lock_sha256"] == expected_sha
    assert max(s5["daily_returns"].keys()) < "2025-01-01"


# ===========================================================================
# 3. Markdown Reports Hygiene & Exact JSON-to-MD Fidelity
# ===========================================================================


@pytest.mark.parametrize("md_path", [LAB4_MD_PATH, LAB5_MD_PATH])
def test_lab4_and_lab5_reports_hygiene_and_links(md_path: Path) -> None:
    assert md_path.exists(), f"Missing report: {md_path}"
    raw = md_path.read_text(encoding="utf-8")
    assert md_path.stat().st_size < 900 * 1024, "Report exceeds 900 KB limit"
    assert raw.startswith("---\n"), "Missing YAML frontmatter"
    assert raw.count("\n---\n") >= 1
    assert "$" not in raw, f"Bare '$' found in {md_path.name} — use USD!"

    # Verify all local relative markdown links resolve to existing files
    link_pat = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")
    for target in link_pat.findall(raw):
        if target.startswith(("http://", "https://", "mailto:", "file://")):
            continue
        resolved = (md_path.parent / target).resolve()
        assert resolved.exists(), f"Broken relative link '{target}' in {md_path.name}"


def test_reports_match_summary_json_key_numbers() -> None:
    s4 = json.loads(LAB4_SUMMARY_PATH.read_text(encoding="utf-8"))
    md4 = LAB4_MD_PATH.read_text(encoding="utf-8")
    for token in (
        f"+{s4['results']['E40_VRP_VOL_CARRY']['metrics_b_1x']['cagr_pct']:.2f}%",
        f"{s4['results']['E40_VRP_VOL_CARRY']['metrics_b_1x']['sharpe']:.3f}",
        f"{s4['ensemble']['metrics_b_1x']['sharpe']:.3f}",
        f"{s4['ensemble']['metrics_b_1x']['max_dd_pct']:.2f}%",
        f"{s4['results']['E40_XSEC_SECTOR_MOM_TOP4']['council_breakeven_mult']:.2f}x",
    ):
        assert token in md4, f"Lab #4 report missing verified JSON number {token}"

    s5 = json.loads(LAB5_SUMMARY_PATH.read_text(encoding="utf-8"))
    md5 = LAB5_MD_PATH.read_text(encoding="utf-8")
    for token in (
        f"{s5['yahoo_futures_telemetry']['MNQ']['cost_pct_of_d1_range']:.3f}%",
        f"{s5['yahoo_futures_telemetry']['M6J']['cost_pct_of_d1_range']:.3f}%",
        f"+{s5['best_topstep']['ev_per_usd_fee']:.2f}x",
        f"+{s5['best_tradeify']['ev_per_usd_fee']:.2f}x",
        "+7.17x",
        "+3.25x",
    ):
        assert token in md5, f"Lab #5 report missing verified JSON number {token}"
