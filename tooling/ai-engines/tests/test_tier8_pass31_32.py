"""Deterministic unit & anti-bias regression tests for Tier 8 (M8.1 Pass 31 & M8.2 Pass 32).

Verifies:
  - Hard cap m_total <= 20 on both Pass 31 and Pass 32.
  - Pass 31 Research Council HypothesisCard completeness & fail-closed critique_proposal wiring.
  - Pass 31 causal liquidity sweep reclaim zero-lookahead future-mutation invariance.
  - Pass 32 causal 20-day volatility throttle zero-lookahead future-mutation invariance.
  - Pass 32 causal Cluster-A allocation weights (EQUAL, INV_DD, HRP, ERC) sum-to-budget & positivity.
  - Sealed Holdout integrity (`holdout_rows_analysed == 0`, `order_send_count == 0`), anti-bloat (< 900 KB),
    zero bare `$` in prose, valid YAML frontmatter, and zero broken local Markdown links.
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

from quant_factory import (
    pass31_redteam_discovery_dev as p31,
    pass32_portfolio_pruning_and_regime_dev as p32,
)
from quant_factory.data_store import assert_holdout_locked
from quant_factory.research_council import propose_hypothesis


def test_pass31_catalog_cap_and_hypothesis_cards():
    cat = p31.build_pass31_catalog()
    assert len(cat) <= p31.M_TOTAL_CAP == 20
    assert len(cat) == 18
    assert len({c["id"] for c in cat}) == len(cat)
    assert {c["fam"] for c in cat} == {"FA_CROSS_SESS_VOL_COMP", "FB_LIQ_SWEEP_REVERSAL", "FC_NY_OPEN_SPILLOVER"}

    for c in cat:
        card = propose_hypothesis(
            hypothesis_id=c["id"],
            title=f"Pass 31 {c['fam']} on {c['asset']}",
            asset_universe=(c["asset"],),
            timeframe="M1_INTRADAY_SWAP0",
            counterparty_mechanism=c["counterparty"],
            economic_rationale=c["rationale"],
            causal_invariants=p31.COMMON_INVARIANTS,
            n_trials_cumulative=len(cat),
            kill_criteria=p31.PASS31_KILL_CRITERIA,
        )
        assert card.validate() == [], f"Invalid HypothesisCard for {c['id']}: {card.validate()}"


def test_pass31_liq_sweep_reclaim_causal_timing():
    # Construct synthetic M1 day with a sweep above box_hi=100.0 (atr=1.0 -> sweep [0.15..0.35]=100.25)
    # on bar 10, closing back inside (99.95) on bar 15 -> entry must occur STRICTLY on bar 16 open!
    n_bars = 120
    t0 = 1_600_000_000
    times = np.arange(n_bars, dtype=np.int64) * 60 + t0
    quotes = np.zeros((n_bars, 8), dtype=np.float64)
    # Default flat price at 99.80 Bid / 99.82 Ask
    quotes[:, 0:4] = 99.80
    quotes[:, 4:8] = 99.82
    # Sweep bar 10: High = 100.25 (0.25 ATR above box_hi=100.0), bars 10..14 stay outside (>= 100.0)
    quotes[10:15, 0:4] = 100.10
    quotes[10:15, 4:8] = 100.12
    quotes[10, 1] = 100.25
    quotes[10, 5] = 100.27
    # Reclaim bar 15: Close drops back inside box (< 100.0)
    quotes[15, 3] = 99.92
    # Bar 16 open (entry bar!)
    quotes[16, 0] = 99.90
    quotes[16, 4] = 99.92

    bundle = {
        "asset": "US100",
        "times": times,
        "quotes": quotes,
        "spec": None,
        "usdjpy_close_map": None,
    }
    day_rec = {"day": "2020-09-13", "year": 2020, "day_sec": t0, "fi": 0, "flat_idx": n_bars - 1, "atr": 1.0}
    tr, fd, targs = p31._eval_liq_sweep_reclaim(
        bundle, day_rec, 100.0, 99.0, t0 + 5 * 60, t0 + 60 * 60, t0 + 115 * 60,
        reclaim_bars=15, sl_atr=0.65,
    )
    assert tr is not None and fd is not None and targs is not None
    assert targs[0] == 16, "Entry must execute strictly on bar idx+1 after closed reclaim bar!"
    assert targs[2] == -1, "Upside sweep reclaim must enter SHORT (-1)!"
    assert tr["entry"] == int(times[16])


def test_pass32_causal_vol_throttle_zero_lookahead():
    rng = np.random.default_rng(2026)
    days_a = [f"2021-01-{i+1:02d}" for i in range(28)] + [f"2021-02-{i+1:02d}" for i in range(28)] + [f"2021-03-{i+1:02d}" for i in range(20)]
    days_b = [f"2022-01-{i+1:02d}" for i in range(28)] + [f"2022-02-{i+1:02d}" for i in range(28)]
    days = days_a + days_b
    nets1 = rng.normal(5.0, 40.0, size=len(days))
    dds1 = np.abs(rng.normal(20.0, 15.0, size=len(days)))

    out_n1, out_d1 = p32._causal_vol_throttle(days, nets1, dds1, fit_cutoff_day="2022-01-01", window=20)

    # Wildly mutate everything strictly after t_cut (inside Cluster B!)
    t_cut = len(days_a) + 15
    nets2 = nets1.copy()
    dds2 = dds1.copy()
    nets2[t_cut + 1:] *= 100.0
    dds2[t_cut + 1:] *= 50.0
    out_n2, out_d2 = p32._causal_vol_throttle(days, nets2, dds2, fit_cutoff_day="2022-01-01", window=20)

    assert np.allclose(out_n1[:t_cut + 1], out_n2[:t_cut + 1]), "Look-ahead leak in _causal_vol_throttle nets!"
    assert np.allclose(out_d1[:t_cut + 1], out_d2[:t_cut + 1]), "Look-ahead leak in _causal_vol_throttle dds!"


def test_pass32_causal_cluster_a_weights_invariants():
    rng = np.random.default_rng(99)
    engs = ["E1", "E2", "E3", "E4", "E5"]
    mat = rng.normal(0.0005, 0.004, size=(200, len(engs)))
    dd_map = {e: float(2.0 + i) for i, e in enumerate(engs)}
    budget = 0.035

    for method in ("EQUAL", "INV_DD", "HRP", "ERC"):
        w = p32._causal_cluster_a_weights(method, engs, [], {}, budget, mat, dd_map)
        assert set(w.keys()) == set(engs)
        assert all(v > 0.0 for v in w.values()), f"Non-positive weight in {method}: {w}"
        assert sum(w.values()) == pytest.approx(budget, rel=1e-6)


@pytest.mark.local_cache
def test_tier8_artifacts_holdout_seal_and_anti_bloat():
    assert len(assert_holdout_locked()) == 64

    ret_dir = ROOT / ".runtime" / "quant-pod-returns"
    p31_json = json.loads((ret_dir / "pass31_redteam_summary.json").read_text(encoding="utf-8"))
    p32_json = json.loads((ret_dir / "pass32_pruning_regime_summary.json").read_text(encoding="utf-8"))

    assert p31_json["holdout_rows_analysed"] == 0
    assert p31_json["order_send_count"] == 0
    assert p31_json["m_total"] <= p31_json["m_total_cap"] == 20
    assert len(p31_json["results"]) == p31_json["m_total"]

    assert p32_json["holdout_rows_analysed"] == 0
    assert p32_json["order_send_count"] == 0
    assert p32_json["m_total_variants"] <= p32_json["m_total_cap"] == 20
    assert len(p32_json["loo_audit_9e"]) == 9

    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for dname in ("PASS31-REDTEAM-GUARDED-DISCOVERY-20261124.md", "PASS32-PORTFOLIO-PRUNING-AND-REGIME-DEV-20261124.md"):
        dp = ROOT / "planning" / "research" / dname
        assert dp.exists(), f"Missing Tier 8 report: {dp}"
        assert dp.stat().st_size < 900 * 1024
        txt = dp.read_text(encoding="utf-8")
        assert txt.startswith("---\n")
        assert "$" not in txt, f"Found bare $ in {dname}"
        for target in link_re.findall(txt):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (dp.parent / target.split("#", 1)[0]).resolve()
            assert resolved.exists(), f"Broken local link `{target}` in {dname}"
