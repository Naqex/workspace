"""Unit tests for pre-registered Portfolio v1 vs v2 architecture study (OrderSend=0, Holdout sealed)."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory import portfolio_v1_vs_v2_study as study  # noqa: E402


def test_invariants_and_preregistered_architectures():
    assert study.ORDER_SEND_CAPABLE is False
    base_r = {
        "E1_USDJPY_TOKYO": 0.001606,
        "E2_USDJPY_EXP80": 0.005894,
        "E3_GBPUSD_VH": 0.0075,
        "E4_US100_SESS40": 0.0050,
        "E5_US100_RS1130": 0.0050,
        "E6_EURJPY_VOLCOMP": 0.0050,
        "E7_USDJPY_NY10ET": 0.0050,
        "S6_FX_USD_BSK": 0.0050,
    }
    archs = study.build_preregistered_architectures(base_r)
    assert len(archs) == 6
    ids = [a[0] for a in archs]
    assert "A1_V1_LIVE8_INCUMBENT" in ids
    assert "A5_V2_ROBUST_TIER_9E_EUR" in ids
    # Risk-sum normalization: A2..A5 must match A1_V1_LIVE8_INCUMBENT total nominal risk sum
    sum_live8 = sum(archs[1][2].values())
    for aid, _, weights in archs[2:]:
        assert abs(sum(weights.values()) - sum_live8) < 1e-4, f"risk_sum_mismatch:{aid}"


def test_exact_cost_stress_monotonic_and_mark_consistent():
    row = {
        "asset": "EURUSD",
        "entry_price": 1.1000,
        "sl_price": 1.0950,
        "initial_risk_usd": 500.0,
        "stop_risk_with_cost_usd": 520.0,
        "net_usd_per_lot": 300.0,
    }
    stamps = np.array([1_600_000_000, 1_600_000_060], dtype=np.int64)
    marks = np.array([[0.0, 150.0, -50.0, 100.0], [100.0, 350.0, 90.0, 300.0]], dtype=np.float64)
    tapes = {"TEST": {"2020-09-13": (row, stamps, marks)}}

    assert study.estimate_base_friction_usd_per_lot(row) == 20.0
    t15 = study.apply_cost_stress_to_tapes(tapes, 1.5)
    t20 = study.apply_cost_stress_to_tapes(tapes, 2.0)

    r15, _, m15 = t15["TEST"]["2020-09-13"]
    r20, _, m20 = t20["TEST"]["2020-09-13"]
    assert r15["net_usd_per_lot"] == 290.0
    assert r15["stop_risk_with_cost_usd"] == 530.0
    assert float(m15[-1, -1]) == 290.0
    assert r20["net_usd_per_lot"] == 280.0
    assert r20["stop_risk_with_cost_usd"] == 540.0
    assert float(m20[-1, -1]) == 280.0
