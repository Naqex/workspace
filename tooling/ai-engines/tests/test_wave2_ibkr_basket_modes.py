"""Wave-2 Cycle 4J Tests — Multi-Mode IBKR BasketTrader Order-Sheet Upgrade (`OrderSend = 0`).

Verifies:
  - All 4 new modes (`s3b_macro`, `l7_top2`, `s4_lab4_eqw`, `super_etf_6eng`) plus exact `s3b_macro` == `M5` parity.
  - Strict `ORDER_SEND_COUNT == 0`, `DRY_RUN_ONLY is True`, zero signal-only (`^VIX`/`^VIX3M`) tickets.
  - Exact IBKR TWS BasketTrader CSV header (`Action,Quantity,Symbol,SecType,Exchange,Currency,TimeInForce,OrderType,BasketTag`)
    and CLI flags (`--mode`, `--capital-usd`, `--fractional {on,off}`, `--out-basket-csv`).
  - Exact IBKR Tiered commission math (`$0.0035/sh`, `$0.35` min, `1%` cap) & `> 25 bps/yr` min-order fee warning
    triggering at `5,000 USD` vs clean pass at `50,000 USD`.
  - Fractional `off` (strict integer shares) vs `on` (reduced idle cash at `5k USD`) and causal `--as-of` cutoff.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import subprocess
import sys

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import assert_holdout_locked
from quant_factory.ibkr_macro_rebalancer import (
    DRY_RUN_ONLY,
    MIN_ORDER_FEE_WARN_BPS_YR,
    ORDER_SEND_COUNT,
    VALID_MODES,
    compute_ibkr_tiered_commission,
    generate_rebalance_plan,
    tickets_to_ibkr_basket_csv,
    tickets_to_ibkr_csv,
)


EXPECTED_BASKET_HEADER = [
    "Action",
    "Quantity",
    "Symbol",
    "SecType",
    "Exchange",
    "Currency",
    "TimeInForce",
    "OrderType",
    "BasketTag",
]


def test_all_four_new_modes_dryrun_and_s3b_parity():
    assert len(assert_holdout_locked()) == 64
    assert ORDER_SEND_COUNT == 0
    assert DRY_RUN_ONLY is True
    for m in ("s3b_macro", "l7_top2", "s4_lab4_eqw", "super_etf_6eng"):
        assert m in VALID_MODES

    p_m5 = generate_rebalance_plan(mode="M5_VOL_PARITY_TREND_GUARD", equity_usd=50_000.0)
    p_s3b = generate_rebalance_plan(mode="s3b_macro", equity_usd=50_000.0)
    assert p_m5["allocations"] == p_s3b["allocations"]
    assert p_m5["ticket_count"] == p_s3b["ticket_count"]

    for m in ("s3b_macro", "l7_top2", "s4_lab4_eqw", "super_etf_6eng"):
        plan = generate_rebalance_plan(mode=m, equity_usd=50_000.0, allow_fractional_shares=False)
        assert plan["order_send_count"] == 0
        assert plan["dry_run_only"] is True
        assert plan["ticket_count"] > 0
        assert plan["gross_exposure_pct"] <= 100.05
        # Signal-only indices (^VIX, ^VIX3M) must NEVER appear in allocations or tickets
        assert all(not a["symbol"].startswith("^") for a in plan["allocations"])
        assert all(not t["Symbol"].startswith("^") for t in plan["tickets"])
        # Integer-share mode produces strictly integer quantities
        assert all(isinstance(t["Quantity"], int) and t["Quantity"] >= 1 for t in plan["tickets"])


def test_ibkr_tiered_commission_and_5k_warn_vs_50k_clean():
    assert abs(compute_ibkr_tiered_commission(1.0, 500.0) - 0.35) < 1e-12
    assert abs(compute_ibkr_tiered_commission(1.0, 10.0) - 0.10) < 1e-12
    assert abs(compute_ibkr_tiered_commission(500.0, 100.0) - 1.75) < 1e-12
    assert compute_ibkr_tiered_commission(0.0, 500.0) == 0.0

    # At 5,000 USD on super_etf_6eng: $0.35 min-order trap triggers warning (> 25 bps/yr)
    p5k = generate_rebalance_plan(mode="super_etf_6eng", equity_usd=5_000.0, allow_fractional_shares=True)
    assert p5k["min_order_fee_warning"] is True
    assert p5k["est_annual_comm_drag_bps"] > MIN_ORDER_FEE_WARN_BPS_YR
    assert "l7_top2" in p5k["fee_warning_detail"] and "s3b_macro" in p5k["fee_warning_detail"]

    # At 50,000 USD on super_etf_6eng (integer-clean): passes cleanly <= 25 bps/yr
    p50k = generate_rebalance_plan(mode="super_etf_6eng", equity_usd=50_000.0, allow_fractional_shares=False)
    assert p50k["min_order_fee_warning"] is False
    assert p50k["est_annual_comm_drag_bps"] <= MIN_ORDER_FEE_WARN_BPS_YR
    assert p50k["est_ibkr_comm_usd"] > 0.0

    # Fractional ON at 5k reduces idle cash vs Fractional OFF
    p5k_int = generate_rebalance_plan(mode="super_etf_6eng", equity_usd=5_000.0, allow_fractional_shares=False)
    assert p5k["idle_cash_pct"] < p5k_int["idle_cash_pct"]


def test_ibkr_basket_trader_csv_schema_and_cli_execution(tmp_path: Path):
    out_basket = tmp_path / "ibkr_basket_super6.csv"
    out_json = tmp_path / "ibkr_plan_super6.json"
    out_legacy = tmp_path / "ibkr_legacy.csv"

    cmd = [
        sys.executable,
        "-X", "utf8",
        str(AI_ENGINES / "quant_factory/ibkr_macro_rebalancer.py"),
        "--mode", "super_etf_6eng",
        "--capital-usd", "50000",
        "--fractional", "off",
        "--as-of", "2024-12-31",
        "--out-basket-csv", str(out_basket),
        "--out-csv", str(out_legacy),
        "--out-json", str(out_json),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f"CLI failed: {proc.stderr}"
    assert out_basket.exists() and out_json.exists() and out_legacy.exists()

    plan = json.loads(out_json.read_text(encoding="utf-8"))
    assert plan["order_send_count"] == 0
    assert plan["dry_run_only"] is True
    assert plan["as_of_date"] <= "2024-12-31"
    assert plan["equity_usd"] == 50_000.0
    assert plan["min_order_fee_warning"] is False

    # Verify exact IBKR TWS BasketTrader CSV header & rows
    reader = csv.reader(io.StringIO(out_basket.read_text(encoding="utf-8")))
    rows = list(reader)
    assert rows[0] == EXPECTED_BASKET_HEADER
    assert len(rows) - 1 == plan["ticket_count"]
    for r in rows[1:]:
        assert r[0] in ("BUY", "SELL")
        assert int(r[1]) >= 1
        assert r[3] == "STK" and r[4] == "SMART" and r[5] == "USD"
        assert r[6] == "DAY" and r[7] == "LMT"
        assert r[8].startswith("DRYRUN_ONLY_super_etf_6eng_")

    # Verify legacy CSV serializer also remains 100% intact
    legacy_rows = list(csv.DictReader(io.StringIO(tickets_to_ibkr_csv(plan))))
    assert len(legacy_rows) == plan["ticket_count"]
    assert all(r["DryRunOnly"] == "TRUE" for r in legacy_rows)
    assert tickets_to_ibkr_basket_csv(plan) == out_basket.read_text(encoding="utf-8")
