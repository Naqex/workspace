"""Wave-2 Cycle 4D Tests — Lab #8 CME-Native Zero-Swap Futures Strategy Lab (MES/MNQ/MGC/MCL/ZN/6E).

Verifies:
  - Holdout 2025+ SEALED (`holdout_rows_analysed = 0`, `OrderSend = 0`), report `< 16 KB`, zero bare `$`,
    exact 9/9 report-vs-JSON parity across `LAB8-CME-NATIVE-FUTURES-STRATEGY-LAB-20261124.md` and `lab8_cme_summary.json`.
  - All 6 CME continuous futures Parquets cached (`0` skipped), roll-safe return filter cleanly handles
    `2020-04-20` negative `CL=F` (`-37.63 USD`) without NaN/Inf or look-ahead.
  - Exact CME Micro friction & quarterly roll arithmetic (`swap_cost_bps_yr == 0.0`, `2x` cost drag == `2.0 * 1x`).
  - Bit-for-bit future-mutation anti-lookahead proof across ALL 9 Lab #8 strategies (`L8_A1..L8_C3`)!
  - Exact fail-closed `sleeve7_cme_native_futures.json` export rule (NOT exported when `n_approved == 0`)
    and `topstep_standard_overnight_allowed == False` honesty check.
"""

from __future__ import annotations

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

from quant_factory.data_store import assert_holdout_locked
from quant_factory.lab8_cme_native_futures_lab import (
    CACHE_DIR,
    CME_SPECS,
    LAB8_CATALOG,
    SLEEVE7_PATH,
    build_lab8_strategy_weights,
    compute_roll_safe_returns,
    load_aligned_cme_panel,
    simulate_cme_futures_strategy,
)


def _count_bare_dollar_pairs(md_text: str) -> int:
    in_fence = False
    bad = 0
    for ln in md_text.splitlines():
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        cleaned = re.sub(r"`[^`]*`", "", ln)
        if cleaned.count("$") >= 2:
            bad += 1
    return bad


@pytest.mark.local_cache
def test_lab8_report_json_parity_holdout_seal_and_hygiene():
    lock_sha = assert_holdout_locked()
    assert len(lock_sha) == 64

    rp = ROOT / "planning/research/LAB8-CME-NATIVE-FUTURES-STRATEGY-LAB-20261124.md"
    js = CACHE_DIR / "lab8_cme_summary.json"
    assert rp.exists(), f"Missing Lab #8 report: {rp}"
    assert js.exists(), f"Missing Lab #8 JSON summary: {js}"
    assert rp.stat().st_size < 16_384, f"Report {rp.stat().st_size} B exceeds 16 KB limit!"

    txt = rp.read_text(encoding="utf-8")
    summary = json.loads(js.read_text(encoding="utf-8"))
    assert "holdout_rows_analysed: 0" in txt
    assert "order_send_count: 0" in txt
    assert _count_bare_dollar_pairs(txt) == 0
    assert summary["holdout_rows_analysed"] == 0
    assert summary["order_send_count"] == 0
    assert summary["m_total"] == 9
    assert len(summary["results"]) == 9
    assert summary["topstep_feasibility"]["topstep_standard_overnight_allowed"] is False

    # Fail-closed sleeve7 gate: when 0 approved, sleeve7 MUST NOT exist on disk
    if summary["n_approved"] == 0:
        assert summary["sleeve7_exported"] is False
        assert not SLEEVE7_PATH.exists(), "Rogue sleeve7_cme_native_futures.json must not exist when n_approved == 0!"

    # Exact 9/9 strategy ID & Blind Cluster B 1x CAGR parity between MD report and JSON summary
    for row in summary["results"]:
        sid = row["id"]
        cagr_str = f"{row['cl_b_cagr_1x_pct']:+.2f}%"
        assert sid in txt, f"Strategy {sid} missing from report"
        assert cagr_str in txt, f"CAGR {cagr_str} for {sid} missing from report"


@pytest.mark.local_cache
def test_cme_cache_complete_and_negative_oil_roll_safe_guard():
    panel = load_aligned_cme_panel(cache_dir=CACHE_DIR, force_refresh=False)
    assert len(panel["codes"]) == 6
    assert panel["codes"] == [sp.code for sp in CME_SPECS]
    assert len(panel["dates"]) >= 2800
    assert np.all(np.isfinite(panel["ret"]))
    assert float(np.max(np.abs(panel["ret"]))) <= 0.30 + 1e-12

    # Explicit unit proof on synthetic 2020-04-20 negative WTI close (-37.63) -> rebound (+10.01)
    oil_px = np.array([20.0, 18.27, -37.63, 10.01, 13.78], dtype=np.float64)
    oil_r = compute_roll_safe_returns(oil_px, code="MCL")
    assert np.all(np.isfinite(oil_r))
    assert abs(oil_r[2] - (-0.18)) < 1e-12  # conservative front-month shock on expiry day
    assert abs(oil_r[3] - 0.0) < 1e-12      # zero artifact on negative-to-positive roll print
    assert abs(oil_r[4] - 0.30) < 1e-12     # extreme rebound clamped safely at +30%


@pytest.mark.local_cache
def test_cme_friction_and_quarterly_roll_exact_zero_swap():
    panel = load_aligned_cme_panel(cache_dir=CACHE_DIR, force_refresh=False)
    w = build_lab8_strategy_weights(panel, "L8_A2_TSMOM_BLEND_20_60_120")

    s0 = simulate_cme_futures_strategy(panel, w, cost_mult=0.0)
    s1 = simulate_cme_futures_strategy(panel, w, cost_mult=1.0)
    s2 = simulate_cme_futures_strategy(panel, w, cost_mult=2.0)

    assert s1["swap_cost_bps_yr"] == 0.0
    assert s1["roll_cost_bps_yr"] > 0.0
    assert s1["trade_cost_bps_yr"] > 0.0
    assert abs(s1["total_cost_bps_yr"] - (s1["trade_cost_bps_yr"] + s1["roll_cost_bps_yr"])) <= 0.05
    assert abs(s2["total_cost_bps_yr"] - 2.0 * s1["total_cost_bps_yr"]) <= 0.05
    assert float(np.sum(s2["net_returns"])) < float(np.sum(s1["net_returns"])) < float(np.sum(s0["net_returns"]))


@pytest.mark.local_cache
def test_lab8_all_9_strategies_bit_for_bit_future_mutation_zero_lookahead():
    """Mutating all bars `[cut:]` MUST produce EXACT 0.0 difference in weights `[:cut+1]` and net returns `[:cut]`!"""
    panel = load_aligned_cme_panel(cache_dir=CACHE_DIR, force_refresh=False)
    # Slice a fast 400-bar window (still > 125d warmup + 275 eval bars) for rapid exact testing across ALL 9 strategies
    sub_n = 400
    cut = 280
    p_clean = {
        "dates": panel["dates"][:sub_n],
        "codes": panel["codes"],
        "close": panel["close"][:sub_n].copy(),
        "high": panel["high"][:sub_n].copy(),
        "low": panel["low"][:sub_n].copy(),
        "ret": panel["ret"][:sub_n].copy(),
        "atr_pct": panel["atr_pct"][:sub_n].copy(),
        "oneway_bps": panel["oneway_bps"][:sub_n].copy(),
        "roll_flags": panel["roll_flags"][:sub_n].copy(),
    }
    p_mut = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in p_clean.items()}
    p_mut["close"][cut:] *= 0.25
    p_mut["high"][cut:] *= 0.25
    p_mut["low"][cut:] *= 0.25
    p_mut["ret"][cut:] = -0.20
    p_mut["atr_pct"][cut:] = 0.15

    for item in LAB8_CATALOG:
        sid = item["id"]
        w_c = build_lab8_strategy_weights(p_clean, sid)
        w_m = build_lab8_strategy_weights(p_mut, sid)
        assert np.array_equal(w_c[: cut + 1], w_m[: cut + 1]), f"Look-ahead leak in weights of {sid}!"

        r_c = simulate_cme_futures_strategy(p_clean, w_c, cost_mult=1.0)["net_returns"]
        r_m = simulate_cme_futures_strategy(p_mut, w_m, cost_mult=1.0)["net_returns"]
        assert np.array_equal(r_c[:cut], r_m[:cut]), f"Look-ahead leak in returns of {sid}!"
