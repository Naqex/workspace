"""Focused tests for Round-3 counterfactual benchmark, factor cluster caps & canonical v2 contracts."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory import round3_frame_benchmark as r3


def test_prop_contracts_v2_schema_and_retired_items() -> None:
    path = AI_ENGINES / "configs/prop_contracts_v2.json"
    assert path.is_file()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    assert cfg["order_send_count"] == 0
    assert cfg["portfolio_frame"]["fixed_across_all_phases"] is True
    assert len(cfg["portfolio_frame"]["core_engines"]) == 7
    assert cfg["contracts"]["ftmo_swing_10k"]["role"] == "PRIMARY_BENCHMARK"
    assert cfg["contracts"]["ftmo_swing_10k"]["external_cash_refund_pct"] == 1.0
    assert cfg["contracts"]["the5ers_hs_5k"]["role"] == "SHADOW_SCORED_SECONDARY"
    assert cfg["contracts"]["the5ers_hs_5k"]["external_cash_refund_pct"] == 0.70
    assert cfg["contracts"]["the5ers_hs_5k"]["min_payout_net_usd"] == 150.0


def test_directional_factor_exposures_and_calendar_alignment() -> None:
    assert r3._directional_factor_exposures("USDJPY", +1) == (1, -1, 0)
    assert r3._directional_factor_exposures("USDJPY", -1) == (-1, 1, 0)
    assert r3._directional_factor_exposures("GBPUSD", +1) == (-1, 0, 0)
    assert r3._directional_factor_exposures("EURJPY", +1) == (0, -1, 0)
    assert r3._directional_factor_exposures("US100.cash", +1) == (0, 0, 1)

    cal_days, nets, dds, flgs = r3.align_exits_to_real_calendar(
        "2024-01-05",
        "2024-01-08",
        [{"day": "2024-01-05", "net_usd": 120.0, "day_dd_usd": 35.0, "trades": 1}],
    )
    assert cal_days == ["2024-01-05", "2024-01-06", "2024-01-07", "2024-01-08"]
    assert nets[0] == 120.0 and nets[1] == 0.0 and nets[2] == 0.0
    assert flgs.tolist() == [1, 0, 0, 0]


def test_real_calendar_numba_settled_lag_and_receipt_integrity() -> None:
    # Deterministic 60-day tape where every weekday earns +150 USD -> verifies T+3 settlement lag & net settled cash
    n = 60
    nets = np.full(n, 150.0, dtype=np.float64)
    dds = np.full(n, 20.0, dtype=np.float64)
    flgs = np.ones(n, dtype=np.int8)
    idx = np.tile(np.arange(n, dtype=np.int32), (2, 13))[:, :730]

    res = r3._simulate_real_calendar_prop_numba(
        idx,
        nets, dds, flgs,
        nets, dds, flgs,
        nets, dds, flgs,
        nets, dds, flgs,
        nets, dds, flgs,
        10000.0, 168.0, 1.0,
        0.10, 0.05, 0.05, 0.10,
        4, 0.0, 0.80,
        14, 3, 50.0, 0.01,
        4, 0.50, 0.60,
        0.035, 0.65, 0.060, 0.40,
        0.035, 0.080, 0,
    )
    summary = r3._summarize_sim(res, 168.0)
    assert summary["fail_1try_pct"] == 0.0
    assert summary["payout_reached_24m_pct"] == 100.0
    assert summary["pay1_cal_days_median_cond"] >= 25.0
    assert summary["net_24m_mean_usd"] > 0.0

    # Verify published receipt integrity (Holdout 2025+ sealed, OrderSend=0, zero bare '$')
    assert r3.OUT_MD.is_file() and r3.OUT_JSON.is_file()
    md_text = r3.OUT_MD.read_text(encoding="utf-8")
    assert "$" not in md_text
    payload = json.loads(r3.OUT_JSON.read_text(encoding="utf-8"))
    assert payload["holdout_rows_analysed"] == 0
    assert payload["order_send_count"] == 0
    assert payload["order_send_capable"] is False
    fc = payload["factor_cap_diagnostics_p1_1x"]["symbol_plus_factor_caps"]
    assert fc["worst_day_dd_pct"] < 5.0
    assert fc["peak_usd_cluster_pct"] <= 2.26
    assert fc["peak_jpy_cluster_pct"] <= 2.01
    assert fc["clamped_factor"] > 0
