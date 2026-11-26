"""Deterministic Unit, Causality, Fill-Rate & Hygiene Tests for Wave-2 Cycle 4A.

Covers:
  - `crypto_maker_shadow_probe.py`: strict touch-through fill logic (`low < bid` / `high > ask`),
    signed 5m/15m adverse selection math, conservative non-negative adverse-selection cost floor,
    live dollar-neutral `M2B_BLEND_50_FUND_50_MOM` basket construction, and live telemetry receipt.
  - `lab7_overnight_macro_rd_loop.py`: exact `(1 + r_ov) * (1 + r_id) == adj_close[t]/adj_close[t-1]`
    identity, strict bit-for-bit future-mutation anti-lookahead across ALL 10 Lab #7 candidates,
    hard-zero weights on signal-only `^VIX/^VIX3M`, overnight `2x` round-trip auction turnover,
    and end-to-end `auto_research_loop` verified ledger & dry-run template checks.
  - Artifacts & Governance: Holdout 2025+ seal, `OrderSend == 0`, `< 18 KB` Vietnamese report,
    valid YAML frontmatter, zero bare `$`, zero broken relative Markdown links, exact JSON parity.
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

from quant_factory.crypto_maker_shadow_probe import (
    DEFAULT_MAKER_LATEST_PATH,
    aggregate_maker_probe_metrics,
    compute_live_m2b_blend_weights,
    simulate_passive_limit_window,
)
from quant_factory.etf40_multifactor_vrp_lab import ETF40_UNIVERSE, SIGNAL_ONLY_TICKERS
from quant_factory.lab7_overnight_macro_rd_loop import (
    LAB7_OUT_DIR,
    LAB7_SUMMARY_PATH,
    build_lab7_candidates,
    load_etf40_ohlc_panel,
    simulate_etf_daily_or_overnight,
)


# ==============================================================================
# Part 1: Crypto Maker Shadow Probe Unit Tests
# ==============================================================================

def test_maker_probe_strict_touch_through_and_adverse_selection() -> None:
    # 25 1m bars; bar 2 touches exactly 100.00 (MUST NOT fill buy at 100.00!),
    # bar 4 drops strictly below (low=99.95 < 100.00 -> FILLS at bar 4!).
    # At bar 4+5=9 close=99.90 (+10 bps adverse selection); at bar 4+15=19 close=100.20 (-20 bps favorable).
    n = 25
    high = np.full(n, 100.10, dtype=np.float64)
    low = np.full(n, 100.01, dtype=np.float64)
    close = np.full(n, 100.05, dtype=np.float64)
    low[2] = 100.00   # Exact touch -> NOT a strict touch-through!
    low[4] = 99.95    # Strict touch-through -> FILLS!
    close[9] = 99.90  # 5m after fill: fell 10 bps below posted 100.00 -> +10.0 bps adverse
    close[19] = 100.20  # 15m after fill: rose 20 bps above posted 100.00 -> -20.0 bps

    res_buy = simulate_passive_limit_window(high, low, close, side=+1, posted_px=100.00, horizon_bars=10)
    assert res_buy["filled"] is True
    assert res_buy["fill_bar"] == 4
    assert abs(res_buy["adv_sel_5m_bps"] - 10.0) < 1e-6
    assert abs(res_buy["adv_sel_15m_bps"] - (-20.0)) < 1e-6

    # Short horizon (3 bars) stops before bar 4 -> MUST NOT fill on bar 2's exact touch!
    res_no = simulate_passive_limit_window(high, low, close, side=+1, posted_px=100.00, horizon_bars=3)
    assert res_no["filled"] is False

    # Sell side: posted at 100.10 -> exact touch (100.10) does NOT fill; bar 3 high=100.15 FILLS!
    high[3] = 100.15
    close[8] = 100.25  # 5m after bar 3: price rose against short -> +14.985 bps adverse!
    res_sell = simulate_passive_limit_window(high, low, close, side=-1, posted_px=100.10, horizon_bars=5)
    assert res_sell["filled"] is True
    assert res_sell["fill_bar"] == 3
    assert res_sell["adv_sel_5m_bps"] > 14.0

    # Aggregation conservative floor: negative adverse selection must NEVER reduce effective cost below maker_fee_bps!
    agg_fav = aggregate_maker_probe_metrics(
        [{"filled": True, "adv_sel_5m_bps": -5.0, "adv_sel_15m_bps": -8.0}] * 10,
        maker_fee_bps=2.0,
    )
    assert agg_fav["fill_rate"] == 1.0
    assert agg_fav["effective_cost_bps"] == 2.0
    assert agg_fav["passes_m2_hurdle"] is True

    # 70% fill with +2.5 bps adv -> exact M2 = 6.15 bps -> passes!
    trials_m2 = (
        [{"filled": True, "adv_sel_5m_bps": 2.5, "adv_sel_15m_bps": 2.5}] * 7
        + [{"filled": False, "adv_sel_5m_bps": None, "adv_sel_15m_bps": None}] * 3
    )
    agg_m2 = aggregate_maker_probe_metrics(trials_m2, maker_fee_bps=2.0, taker_fee_bps=5.0, taker_slip_bps=5.0)
    assert abs(agg_m2["effective_cost_bps"] - 6.15) < 1e-3
    assert agg_m2["passes_m2_hurdle"] is True


def test_maker_probe_live_m2b_basket_exact_dollar_neutrality() -> None:
    rng = np.random.default_rng(123)
    syms = tuple(f"COIN{i}USDT" for i in range(14))
    closes = {s: 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.015, size=90))) for s in syms}
    # Strong funding spread across coins so BOTH Funding + Momentum sleeves activate
    funds = {s: [0.00005 * (i - 6)] * 21 for i, s in enumerate(syms)}

    b = compute_live_m2b_blend_weights(closes, funds, symbols=syms, k_fund=4, k_mom=5)
    assert b["fund_active"] is True
    assert b["mom_active"] is True
    assert abs(b["net_exposure"]) < 1e-6
    assert 0.0 < b["gross_exposure"] <= 1.0 + 1e-6


# ==============================================================================
# Part 2: Lab #7 Overnight/Intraday Identity, Zero Look-Ahead & Invariants
# ==============================================================================

def _make_synthetic_etf40_panel(n_t: int = 340, seed: int = 55) -> dict:
    rng = np.random.default_rng(seed)
    tickers = list(ETF40_UNIVERSE)
    n_k = len(tickers)
    # Build business-day dates spanning > 15 months so monthly & 252d rolling windows trigger
    dates = []
    y, m, d = 2020, 1, 2
    while len(dates) < n_t:
        dates.append(f"{y:04d}-{m:02d}-{d:02d}")
        d += 1
        if d > 28:
            d = 1
            m += 1
            if m > 12:
                m = 1
                y += 1
    r_ov = rng.normal(0.0002, 0.006, size=(n_t, n_k))
    r_id = rng.normal(0.0001, 0.007, size=(n_t, n_k))
    r_ov[0] = np.nan
    adj_close = np.full((n_t, n_k), np.nan, dtype=np.float64)
    adj_open = np.full((n_t, n_k), np.nan, dtype=np.float64)
    adj_close[0] = 100.0
    adj_open[0] = 100.0
    for t in range(1, n_t):
        adj_open[t] = adj_close[t - 1] * (1.0 + r_ov[t])
        adj_close[t] = adj_open[t] * (1.0 + r_id[t])
    r_cc = np.full((n_t, n_k), np.nan, dtype=np.float64)
    r_cc[1:] = adj_close[1:] / adj_close[:-1] - 1.0
    tradable_mask = np.array([tk not in SIGNAL_ONLY_TICKERS for tk in tickers], dtype=bool)
    return {
        "dates": dates,
        "tickers": tickers,
        "tradable_mask": tradable_mask,
        "adj_open": adj_open,
        "adj_close": adj_close,
        "r_cc": r_cc,
        "r_ov": r_ov,
        "r_id": r_id,
    }


@pytest.mark.local_cache
def test_lab7_overnight_intraday_identity_and_all10_zero_lookahead() -> None:
    # 1. Exact decomposition identity on real cached NYSE panel
    real_panel = load_etf40_ohlc_panel()
    spy_i = real_panel["tickers"].index("SPY")
    ok = np.isfinite(real_panel["r_ov"][:, spy_i]) & np.isfinite(real_panel["r_id"][:, spy_i]) & np.isfinite(real_panel["r_cc"][:, spy_i])
    recomp = (1.0 + real_panel["r_ov"][ok, spy_i]) * (1.0 + real_panel["r_id"][ok, spy_i]) - 1.0
    assert np.allclose(recomp, real_panel["r_cc"][ok, spy_i], atol=1e-10)

    # 2. Strict bit-for-bit future-mutation anti-lookahead across ALL 10 Lab #7 candidates!
    p_a = _make_synthetic_etf40_panel(340, seed=55)
    cands_a = build_lab7_candidates(p_a)

    cut = 290
    p_b = {k: (v.copy() if isinstance(v, np.ndarray) else list(v)) for k, v in p_a.items()}
    p_b["adj_open"][cut + 1 :] *= 2.8
    p_b["adj_close"][cut + 1 :] *= 3.1
    p_b["r_cc"][cut + 1 :] = 0.25
    p_b["r_ov"][cut + 1 :] = 0.15
    p_b["r_id"][cut + 1 :] = -0.10
    cands_b = build_lab7_candidates(p_b)

    assert len(cands_a) == 10
    sig_only_idxs = [i for i, tk in enumerate(p_a["tickers"]) if tk in SIGNAL_ONLY_TICKERS]

    for ca, cb in zip(cands_a, cands_b):
        wa, wb = ca["w"], cb["w"]
        assert np.allclose(wa[: cut + 1], wb[: cut + 1], atol=0.0, rtol=0.0), f"Look-ahead in {ca['id']}"
        assert float(np.max(np.sum(np.abs(wa), axis=1))) <= 1.0 + 1e-9, f"Leverage > 1.0 in {ca['id']}"
        for sj in sig_only_idxs:
            assert float(np.max(np.abs(wa[:, sj]))) == 0.0, f"Signal-only ticker traded in {ca['id']}"

    # 3. Overnight-only simulator pays exact 2x round-trip auction turnover per active night
    w_ov = np.zeros_like(p_a["adj_close"])
    w_ov[10, 0] = 0.50
    sim_ov = simulate_etf_daily_or_overnight(p_a, w_ov, mode="overnight_only", cost_bps_oneway=5.0)
    assert sim_ov["turnover"][10] == 0.0  # t -> t+1 shift!
    assert abs(sim_ov["turnover"][11] - 1.00) < 1e-12  # 2 * 0.50 round-trip MOC+MOO
    assert abs(sim_ov["cost_drag"][11] - 0.0005) < 1e-12


# ==============================================================================
# Part 3: Artifacts, Auto-Research-Loop Ledger, Holdout Seal & Doc Hygiene
# ==============================================================================

@pytest.mark.local_cache
def test_cycle4a_artifacts_rd_ledger_and_report_hygiene() -> None:
    # 1. Holdout lock untouched
    lock_path = ROOT / "planning" / "research" / "NATIVE_FTMO_HOLDOUT_LOCK.json"
    assert lock_path.exists()
    assert "2025-01-01" in lock_path.read_text(encoding="utf-8")

    # 2. Live maker probe snapshot receipt safe
    assert DEFAULT_MAKER_LATEST_PATH.exists()
    mk = json.loads(DEFAULT_MAKER_LATEST_PATH.read_text(encoding="utf-8"))
    assert mk["schema"] == "naqex-crypto-maker-shadow-v1"
    assert mk["order_send_count"] == 0
    assert mk["api_keys_used"] == 0
    assert abs(float(mk["m2b_blend_live_basket"]["net_exposure"])) < 1e-6

    # 3. Lab #7 summary + auto_research_loop SHA ledger + emitted dry-run templates
    assert LAB7_SUMMARY_PATH.exists()
    s7 = json.loads(LAB7_SUMMARY_PATH.read_text(encoding="utf-8"))
    assert s7["schema"] == "naqex-lab7-overnight-macro-rd-v1"
    assert s7["order_send_count"] == 0
    assert s7["holdout_rows_analysed"] == 0
    assert s7["m_total"] == 10
    assert len(s7["results"]) == 10

    ledger_json = Path(s7["auto_loop_ledger_json"])
    assert ledger_json.exists()
    assert ledger_json.with_suffix(".sha256").exists()
    for hid, tpl in s7["emitted_templates"].items():
        mq5_p = Path(tpl["mq5_template"])
        assert mq5_p.exists()
        assert "InpDryRunLogOnly     = true" in mq5_p.read_text(encoding="utf-8")

    # 4. Vietnamese report < 18 KB, YAML frontmatter, zero bare `$`, zero broken links, exact JSON parity
    rep = ROOT / "planning" / "research" / "LAB7-OVERNIGHT-DRIFT-AND-RD-LOOP-20261124.md"
    assert rep.exists()
    raw = rep.read_text(encoding="utf-8")
    assert rep.stat().st_size < 18_000, f"Report exceeds 18 KB limit: {rep.stat().st_size}"
    assert raw.startswith("---\n")
    prose = re.sub(r"```.*?```", "", raw, flags=re.S)
    assert "$" not in prose, "Bare '$' found in report prose"

    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for m in link_re.finditer(raw):
        tgt = m.group(1).strip()
        if tgt.startswith(("http://", "https://", "mailto:", "#")):
            continue
        tgt_clean = tgt.split("#", 1)[0]
        if tgt_clean:
            assert (rep.parent / tgt_clean).resolve().exists(), f"Broken link '{tgt}'"

    # Verify all 10 Lab #7 rows match summary JSON verbatim
    for r in s7["results"]:
        assert r["id"] in raw
        assert f"{r['cluster_b_1x']['cagr_pct']:+.2f}%" in raw
        assert f"{r['cluster_b_1x']['sharpe']:.3f}" in raw
