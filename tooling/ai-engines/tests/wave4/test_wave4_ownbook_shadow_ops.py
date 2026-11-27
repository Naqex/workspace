"""Unit & Local-Cache Integration Tests for Wave 4 Own-Book Shadow Operations (`W4-G08`).

Uses `unittest.TestCase` assertions exclusively so EVERY check stays active under `python -O`
as well as standard `python` and `-m "not local_cache"`.

Coverage:
  1. Static AST safety audit: ZERO bare `assert` nodes, ZERO `MetaTrader5` / `OrderSend`
     calls, `ORDER_SEND_CAPABLE is False`, `ORDER_SEND_COUNT == 0`.
  2. Hard CEX `<= 25.0%` enforcement + mutation test (`> 25%` fails closed with `ValueError`)
     + explicit clamp mode rerouting excess cleanly into `SGOV/BIL`.
  3. Funding Compression Alert (`annualized_funding < 3.0%`) -> `FUNDING_COMPRESSION_ALERT`
     + 100% carry auto-rotation into `CASH_TBILL_BUFFER` (`SGOV/BIL`).
  4. All `4/4` Extreme Stress Tests offline on deterministic synthetic fixtures:
       - `STRESS_1_CEX_CAP_25PCT_INSOLVENCY`
       - `STRESS_2_FUNDING_COMPRESSION_LT3PCT`
       - `STRESS_3_2022_SIMULTANEOUS_STOCK_BOND_CRASH`
       - `STRESS_4_CRYPTO_FLASH_CRASH_MINUS35PCT`
  5. Poisoned input fail-closed tests under `python -O`: `NaN`, `+Inf`, `-Inf`, `bool`,
     negative weights, `> 1.0`, non-unit sums, and `2025-01-01` / `2025-06-15` Holdout dates.
  6. OPS-4 Health Snapshot (`GREEN` / `AMBER` / `RED` transitions) & causal zero-lookahead
     future-mutation proof on `simulate_ownbook_composite`.
  7. `@pytest.mark.local_cache` integration test validating the real Dev `<= 2024-12-31`
     Own-Book run (`holdout_rows_analysed == 0`, `4/4` stress pass, atomic SHA-256 JSON).
"""

from __future__ import annotations

import ast
import json
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from quant_core.holdout_guard import HoldoutLockError
from quant_factory.etf40_multifactor_vrp_lab import ETF40_CACHE_DIR
from quant_factory.funding_rate_carry import FUNDING_CACHE_DIR
from quant_factory.live_ops.daily_live_ops_pipeline import (
    TRAFFIC_AMBER,
    TRAFFIC_GREEN,
    TRAFFIC_RED,
)
from quant_factory.wave4 import ownbook_shadow_ops as ops

MODULE_PATH = Path(ops.__file__).resolve()


def _synthetic_business_days(start: str, end: str) -> list[str]:
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    out: list[str] = []
    cur = d0
    while cur <= d1:
        if cur.weekday() < 5:
            out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def _build_synthetic_ownbook_fixture() -> dict[str, Any]:
    """Deterministic synthetic 2021-2024 fixture including a severe 2022 stock+bond crash."""
    days = _synthetic_business_days("2021-01-04", "2024-12-31")
    rng = np.random.default_rng(20261127)

    etf_map: dict[str, float] = {}
    spot_map: dict[str, float] = {}
    carry_map: dict[str, float] = {}
    tbill_map: dict[str, float] = {}
    spy_map: dict[str, float] = {}
    ief_map: dict[str, float] = {}
    tlt_map: dict[str, float] = {}
    fund_ann_map: dict[str, float] = {}

    for d in days:
        if "2022-01-01" <= d <= "2022-10-14":
            # Simultaneous 2022 stock + bond crash regime + compressed crypto funding
            r_spy = -0.0014 + float(rng.normal(0.0, 0.011))
            r_ief = -0.0010 + float(rng.normal(0.0, 0.006))
            r_tlt = -0.0016 + float(rng.normal(0.0, 0.009))
            r_etf = -0.0002 + float(rng.normal(0.0, 0.0045))
            r_spot = -0.0008 + float(rng.normal(0.0, 0.008))
            r_carry = -0.00015 + float(rng.normal(0.0, 0.0003))
            r_tb = 0.015 / 252.0
            f_ann = 0.008  # < 3% funding compression!
        else:
            r_spy = 0.0005 + float(rng.normal(0.0, 0.008))
            r_ief = 0.0001 + float(rng.normal(0.0, 0.004))
            r_tlt = 0.0001 + float(rng.normal(0.0, 0.007))
            r_etf = 0.0004 + float(rng.normal(0.0, 0.004))
            r_spot = 0.0007 + float(rng.normal(0.0, 0.009))
            r_carry = 0.0003 + float(rng.normal(0.0, 0.0002))
            r_tb = 0.035 / 252.0
            f_ann = 0.095  # Healthy +9.5% funding

        etf_map[d] = r_etf
        spot_map[d] = r_spot
        carry_map[d] = r_carry
        tbill_map[d] = r_tb
        spy_map[d] = r_spy
        ief_map[d] = r_ief
        tlt_map[d] = r_tlt
        fund_ann_map[d] = f_ann

    return {
        "days": days,
        "macro_etf_returns": etf_map,
        "crypto_spot_returns": spot_map,
        "crypto_carry_returns": carry_map,
        "tbill_returns": tbill_map,
        "spy_returns": spy_map,
        "ief_returns": ief_map,
        "tlt_returns": tlt_map,
        "funding_ann_map": fund_ann_map,
    }


class TestOwnBookShadowOpsOffline(unittest.TestCase):
    """100% offline synthetic tests passing under `python`, `python -O`, and `-m "not local_cache"`."""

    def test_ast_zero_bare_asserts_and_readonly_invariants(self) -> None:
        self.assertFalse(ops.ORDER_SEND_CAPABLE)
        self.assertEqual(ops.ORDER_SEND_COUNT, 0)
        self.assertEqual(ops.SPEND_VND, 0)
        self.assertEqual(ops.HOLDOUT_CUTOFF_INCLUSIVE, "2024-12-31")
        self.assertEqual(ops.HOLDOUT_CUTOFF_EXCLUSIVE, "2025-01-01")

        src = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(MODULE_PATH))
        assert_nodes = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        self.assertEqual(assert_nodes, [], f"Bare assert found at lines {assert_nodes} (violates -O safety!)")

        banned_imports = {"MetaTrader5", "backtesting", "backtrader", "vectorbt"}
        found_banned: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in banned_imports:
                        found_banned.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in banned_imports:
                    found_banned.append(node.module)
        self.assertEqual(found_banned, [])

    def test_hard_cex_cap_25pct_and_mutation_rejection(self) -> None:
        # Exact 25.0% CEX boundary passes cleanly
        ok_res = ops.validate_ownbook_allocation(ops.DEFAULT_OWNBOOK_WEIGHTS, allow_clamp=False)
        self.assertTrue(ok_res["cex_cap_compliant"])
        self.assertAlmostEqual(ok_res["cex_exposure_pct"], 25.0, places=4)
        self.assertFalse(ok_res["was_clamped"])

        # Mutation test: 25.01% CEX MUST fail closed
        mutated_25_01 = {
            ops.SLEEVE_MACRO_ETF: 0.5999,
            ops.SLEEVE_CRYPTO_SPOT: 0.1001,
            ops.SLEEVE_CRYPTO_CARRY: 0.1500,
            ops.SLEEVE_CASH_TBILL: 0.1500,
        }
        with self.assertRaises(ValueError) as ctx:
            ops.validate_ownbook_allocation(mutated_25_01, allow_clamp=False)
        self.assertIn("CEX_CAP_VIOLATION", str(ctx.exception))

        # Mutation test: 40% CEX in OwnBookConfig MUST fail closed
        with self.assertRaises(ValueError):
            ops.OwnBookConfig(
                target_weights={
                    ops.SLEEVE_MACRO_ETF: 0.50,
                    ops.SLEEVE_CRYPTO_SPOT: 0.20,
                    ops.SLEEVE_CRYPTO_CARRY: 0.20,
                    ops.SLEEVE_CASH_TBILL: 0.10,
                }
            )

        # Mutation test: trying to relax max_cex_exposure > 0.25 MUST fail closed
        with self.assertRaises(ValueError):
            ops.OwnBookConfig(max_cex_exposure=0.30)

        # Explicit clamp mode routes excess strictly into CASH_TBILL_BUFFER (`SGOV/BIL`)
        clamped = ops.validate_ownbook_allocation(
            {
                ops.SLEEVE_MACRO_ETF: 0.50,
                ops.SLEEVE_CRYPTO_SPOT: 0.20,
                ops.SLEEVE_CRYPTO_CARRY: 0.20,
                ops.SLEEVE_CASH_TBILL: 0.10,
            },
            allow_clamp=True,
        )
        self.assertTrue(clamped["was_clamped"])
        self.assertTrue(clamped["cex_cap_compliant"])
        self.assertAlmostEqual(clamped["cex_exposure_pct"], 25.0, places=4)
        self.assertAlmostEqual(clamped["clamped_excess_pct"], 15.0, places=4)
        self.assertAlmostEqual(clamped["weights"][ops.SLEEVE_CASH_TBILL], 0.25, places=6)
        self.assertIn(ops.CEX_CAP_CLAMPED_ALERT_CODE, clamped["alerts"])

    def test_funding_compression_lt3pct_alert_and_tbill_rotation(self) -> None:
        # Healthy funding >= 3.0% -> no alert, carry retained
        healthy = ops.evaluate_funding_compression_step(ops.DEFAULT_OWNBOOK_WEIGHTS, 0.085)
        self.assertFalse(healthy["funding_compression_active"])
        self.assertEqual(healthy["alerts"], [])
        self.assertAlmostEqual(healthy["effective_weights"][ops.SLEEVE_CRYPTO_CARRY], 0.15, places=6)
        self.assertAlmostEqual(healthy["effective_weights"][ops.SLEEVE_CASH_TBILL], 0.15, places=6)
        self.assertAlmostEqual(healthy["effective_cex_exposure_pct"], 25.0, places=4)

        # Exact boundary 3.0% -> healthy
        boundary = ops.evaluate_funding_compression_step(ops.DEFAULT_OWNBOOK_WEIGHTS, 0.03)
        self.assertFalse(boundary["funding_compression_active"])

        # Compressed funding < 3.0% -> FUNDING_COMPRESSION_ALERT + 100% carry rotated to SGOV/BIL
        compressed = ops.evaluate_funding_compression_step(ops.DEFAULT_OWNBOOK_WEIGHTS, 0.029)
        self.assertTrue(compressed["funding_compression_active"])
        self.assertIn(ops.FUNDING_COMPRESSION_ALERT_CODE, compressed["alerts"])
        self.assertAlmostEqual(compressed["effective_weights"][ops.SLEEVE_CRYPTO_CARRY], 0.0, places=8)
        self.assertAlmostEqual(compressed["effective_weights"][ops.SLEEVE_CASH_TBILL], 0.30, places=6)
        self.assertAlmostEqual(compressed["rotated_carry_to_tbill_pct"], 15.0, places=4)
        self.assertAlmostEqual(compressed["effective_cex_exposure_pct"], 10.0, places=4)
        self.assertEqual(compressed["tbill_vehicle"], "SGOV/BIL")

        # Negative funding spike -> also rotates & alerts
        neg_spike = ops.evaluate_funding_compression_step(ops.DEFAULT_OWNBOOK_WEIGHTS, -0.18)
        self.assertTrue(neg_spike["funding_compression_active"])
        self.assertIn(ops.FUNDING_COMPRESSION_ALERT_CODE, neg_spike["alerts"])
        self.assertAlmostEqual(neg_spike["effective_weights"][ops.SLEEVE_CRYPTO_CARRY], 0.0, places=8)

    def test_poisoned_inputs_and_holdout_dates_fail_closed_under_python_O(self) -> None:
        # 1. Poisoned numeric values (NaN, +Inf, -Inf, bool, negative, >1, None)
        poisoned_scalars: list[Any] = [math.nan, math.inf, -math.inf, True, False, -0.05, 1.5, None, "0.10"]
        for bad in poisoned_scalars:
            with self.subTest(bad_weight=bad):
                w = dict(ops.DEFAULT_OWNBOOK_WEIGHTS)
                w[ops.SLEEVE_CRYPTO_SPOT] = bad
                with self.assertRaises(ValueError):
                    ops.validate_ownbook_allocation(w)

        for bad_fund in [math.nan, math.inf, -math.inf, True, False, None, "0.05"]:
            with self.subTest(bad_funding=bad_fund):
                with self.assertRaises(ValueError):
                    ops.evaluate_funding_compression_step(ops.DEFAULT_OWNBOOK_WEIGHTS, bad_fund)  # type: ignore[arg-type]

        # 2. Poisoned Holdout dates (`>= 2025-01-01`, timestamps, malformed, bool) raise HoldoutLockError
        poisoned_dates: list[Any] = [
            "2025-01-01",
            "2025-06-15",
            "2026-11-20",
            "2025-01-01T00:00:00Z",
            "not-a-date",
            True,
            None,
            20241231,
        ]
        for bad_d in poisoned_dates:
            with self.subTest(bad_date=bad_d):
                with self.assertRaises((HoldoutLockError, ValueError)):
                    ops.enforce_ownbook_pre_holdout(["2024-12-30", bad_d], context="poison_test")
                with self.assertRaises((HoldoutLockError, ValueError)):
                    ops.validate_cutoff_date(bad_d)

        # 3. OwnBookConfig refuses post-2024 cutoff_date
        with self.assertRaises(HoldoutLockError):
            ops.OwnBookConfig(cutoff_date="2025-01-01")

        # 4. Composite simulator refuses any 2025-01-01 row in ETF or Crypto map
        fx = _build_synthetic_ownbook_fixture()
        poisoned_etf = dict(fx["macro_etf_returns"])
        poisoned_etf["2025-01-01"] = 0.001
        with self.assertRaises(HoldoutLockError):
            ops.simulate_ownbook_composite(
                macro_etf_returns=poisoned_etf,
                crypto_spot_returns=fx["crypto_spot_returns"],
                crypto_carry_returns=fx["crypto_carry_returns"],
                tbill_returns=fx["tbill_returns"],
                funding_ann_map=fx["funding_ann_map"],
                config=ops.OwnBookConfig(start_date="2021-01-04"),
            )

        # 5. Stress 3 refuses any 2025-01-01 date
        with self.assertRaises(HoldoutLockError):
            ops.run_stress_3_2022_stock_bond_crash(
                dates=["2022-01-03", "2025-01-01"],
                ownbook_returns=[0.0, 0.0],
                spy_returns={"2022-01-03": -0.01},
                bond_returns={"2022-01-03": -0.01},
            )

    def test_all_four_extreme_stress_tests_offline(self) -> None:
        fx = _build_synthetic_ownbook_fixture()
        cfg = ops.OwnBookConfig(start_date="2021-01-04", cutoff_date="2024-12-31")
        comp = ops.simulate_ownbook_composite(
            macro_etf_returns=fx["macro_etf_returns"],
            crypto_spot_returns=fx["crypto_spot_returns"],
            crypto_carry_returns=fx["crypto_carry_returns"],
            tbill_returns=fx["tbill_returns"],
            funding_ann_map=fx["funding_ann_map"],
            config=cfg,
        )
        self.assertEqual(comp["holdout_rows_analysed"], 0)
        self.assertLessEqual(comp["max_realized_cex_exposure_pct"], 25.0)
        self.assertGreater(comp["funding_compression_days"], 100)
        self.assertGreaterEqual(comp["carry_rotation_events"], 2)

        stresses = ops.run_all_four_stress_tests(
            cfg,
            dates=comp["dates"],
            ownbook_returns=comp["guarded_returns"],
            spy_returns=fx["spy_returns"],
            bond_returns=fx["ief_returns"],
            tlt_returns=fx["tlt_returns"],
        )
        self.assertEqual(set(stresses.keys()), set(ops.ALL_STRESS_IDS))

        # Stress 1: CEX Cap 25% + -100% CEX insolvency
        s1 = stresses[ops.STRESS_1_ID]
        self.assertTrue(s1["passed"])
        self.assertTrue(s1["breach_gt25_rejected_fail_closed"])
        self.assertLessEqual(s1["effective_ownbook_dd_pct"], 25.0)
        self.assertGreaterEqual(s1["effective_surviving_equity_pct"], 75.0)
        self.assertEqual(s1["holdout_rows_analysed"], 0)

        # Stress 2: 6-month funding < 3% + negative spikes
        s2 = stresses[ops.STRESS_2_ID]
        self.assertTrue(s2["passed"])
        self.assertTrue(s2["alert_fired"])
        self.assertEqual(s2["alert_code"], ops.FUNDING_COMPRESSION_ALERT_CODE)
        self.assertEqual(s2["post_compression_carry_weight_pct"], 0.0)
        self.assertGreater(s2["guarded_carry_sleeve_return_pct"], s2["unprotected_carry_sleeve_return_pct"])
        self.assertLess(s2["guarded_carry_sleeve_max_dd_pct"], s2["unprotected_carry_sleeve_max_dd_pct"])

        # Stress 3: 2022 simultaneous stock+bond crash vs static 60/40
        s3 = stresses[ops.STRESS_3_ID]
        self.assertTrue(s3["passed"])
        self.assertLess(s3["ownbook_2022_max_dd_pct"], s3["static_60_40_ief_2022_max_dd_pct"])
        self.assertGreater(s3["dd_reduction_vs_60_40_pp"], 0.0)
        self.assertEqual(s3["holdout_rows_analysed"], 0)

        # Stress 4: -35% crypto flash crash + basis blow-out -> zero liquidation & survival
        s4 = stresses[ops.STRESS_4_ID]
        self.assertTrue(s4["passed"])
        self.assertTrue(s4["zero_liquidation"])
        self.assertEqual(s4["isolated_liq_events"], 0)
        self.assertEqual(s4["cross_liq_events"], 0)
        self.assertEqual(s4["spot_liquidation_events"], 0)
        self.assertTrue(s4["portfolio_survived"])
        self.assertLess(s4["total_ownbook_shock_dd_pct"], 10.0)

    def test_ops4_health_snapshot_green_amber_red_transitions(self) -> None:
        fx = _build_synthetic_ownbook_fixture()
        cfg = ops.OwnBookConfig(start_date="2021-01-04", cutoff_date="2024-12-31")
        comp = ops.simulate_ownbook_composite(
            macro_etf_returns=fx["macro_etf_returns"],
            crypto_spot_returns=fx["crypto_spot_returns"],
            crypto_carry_returns=fx["crypto_carry_returns"],
            tbill_returns=fx["tbill_returns"],
            funding_ann_map=fx["funding_ann_map"],
            config=cfg,
        )
        stresses = ops.run_all_four_stress_tests(
            cfg,
            dates=comp["dates"],
            ownbook_returns=comp["guarded_returns"],
            spy_returns=fx["spy_returns"],
            bond_returns=fx["ief_returns"],
        )

        # GREEN: healthy funding (9.5%), CEX <= 25%, 4/4 stress pass
        snap_green = ops.build_ops4_health_snapshot(
            weights=cfg.target_weights,
            annualized_funding_rate=0.095,
            stress_results=stresses,
            as_of_date="2024-12-31",
            holdout_rows_analysed=0,
        )
        self.assertEqual(snap_green["traffic_light"], TRAFFIC_GREEN)
        self.assertFalse(snap_green["order_send_capable"])
        self.assertEqual(snap_green["holdout_rows_analysed"], 0)
        self.assertEqual(snap_green["active_alerts"], [])
        self.assertTrue(snap_green["stress_summary"]["all_passed"])

        # AMBER: funding < 3.0% -> FUNDING_COMPRESSION_ALERT & carry rotated to SGOV/BIL
        snap_amber = ops.build_ops4_health_snapshot(
            weights=cfg.target_weights,
            annualized_funding_rate=0.012,
            stress_results=stresses,
            as_of_date="2024-12-31",
            holdout_rows_analysed=0,
        )
        self.assertEqual(snap_amber["traffic_light"], TRAFFIC_AMBER)
        self.assertIn(ops.FUNDING_COMPRESSION_ALERT_CODE, snap_amber["active_alerts"])
        self.assertTrue(snap_amber["funding_compression_active"])
        self.assertAlmostEqual(snap_amber["cex_exposure_pct"], 10.0, places=4)
        self.assertAlmostEqual(snap_amber["effective_weights"][ops.SLEEVE_CASH_TBILL], 0.30, places=6)

        # RED: stress failure triggers RED halt
        bad_stresses = dict(stresses)
        bad_stresses[ops.STRESS_4_ID] = {**stresses[ops.STRESS_4_ID], "passed": False}
        snap_red = ops.build_ops4_health_snapshot(
            weights=cfg.target_weights,
            annualized_funding_rate=0.095,
            stress_results=bad_stresses,
            as_of_date="2024-12-31",
            holdout_rows_analysed=0,
        )
        self.assertEqual(snap_red["traffic_light"], TRAFFIC_RED)
        self.assertIn("OWNBOOK_STRESS_FAILURE", snap_red["active_alerts"])
        self.assertEqual(snap_red["risk_multiplier"], 0.0)

        # Non-zero holdout_rows_analysed fails closed with HoldoutLockError
        with self.assertRaises(HoldoutLockError):
            ops.build_ops4_health_snapshot(
                weights=cfg.target_weights,
                annualized_funding_rate=0.095,
                stress_results=stresses,
                as_of_date="2024-12-31",
                holdout_rows_analysed=1,
            )

    def test_causal_zero_lookahead_future_mutation(self) -> None:
        """Mutating all future dates after `cut` produces EXACT 0.0 change in returns `[:cut]`."""
        fx = _build_synthetic_ownbook_fixture()
        cfg = ops.OwnBookConfig(start_date="2021-01-04", cutoff_date="2024-12-31")
        cut_date = "2023-06-30"

        res_clean = ops.simulate_ownbook_composite(
            macro_etf_returns=fx["macro_etf_returns"],
            crypto_spot_returns=fx["crypto_spot_returns"],
            crypto_carry_returns=fx["crypto_carry_returns"],
            tbill_returns=fx["tbill_returns"],
            funding_ann_map=fx["funding_ann_map"],
            config=cfg,
        )

        # Violently mutate funding & returns strictly after cut_date
        mut_fund = {k: (-0.50 if k > cut_date else v) for k, v in fx["funding_ann_map"].items()}
        mut_etf = {k: (-0.25 if k > cut_date else v) for k, v in fx["macro_etf_returns"].items()}
        mut_carry = {k: (-0.15 if k > cut_date else v) for k, v in fx["crypto_carry_returns"].items()}

        res_mut = ops.simulate_ownbook_composite(
            macro_etf_returns=mut_etf,
            crypto_spot_returns=fx["crypto_spot_returns"],
            crypto_carry_returns=mut_carry,
            tbill_returns=fx["tbill_returns"],
            funding_ann_map=mut_fund,
            config=cfg,
        )

        cut_idx = sum(1 for d in res_clean["dates"] if d <= cut_date)
        self.assertGreater(cut_idx, 200)
        self.assertTrue(
            np.array_equal(res_clean["guarded_returns"][:cut_idx], res_mut["guarded_returns"][:cut_idx]),
            "Causal violation: future mutation altered historical Own-Book guarded returns!",
        )


class TestOwnBookShadowOpsLocalCache(unittest.TestCase):
    """Real Dev `<= 2024-12-31` cache integration check (`holdout_rows_analysed == 0`)."""

    @pytest.mark.local_cache
    def test_real_dev_cache_run_strictly_pre_holdout_and_4_of_4_stress_pass(self) -> None:
        has_etf = (ETF40_CACHE_DIR / "SPY.parquet").exists()
        has_fund = (FUNDING_CACHE_DIR / "rates" / "BTCUSDT.parquet").exists()
        if not has_etf or not has_fund:
            self.skipTest("Local ETF40 / Crypto funding caches not present.")

        with tempfile.TemporaryDirectory(prefix="w4m2b_") as tmpdir:
            out_json = Path(tmpdir) / "ownbook_shadow_ops_summary.json"
            res = ops.run_ownbook_shadow_ops_study(
                config=ops.OwnBookConfig(cutoff_date="2024-12-31"),
                out_summary_path=out_json,
                verify_holdout_lock_file=True,
            )
            self.assertTrue(out_json.exists())
            loaded = json.loads(out_json.read_text(encoding="utf-8"))

            # Hard Holdout & Read-Only proof
            self.assertEqual(res["invariants"]["holdout_rows_analysed"], 0)
            self.assertEqual(loaded["invariants"]["holdout_rows_analysed"], 0)
            self.assertFalse(res["invariants"]["order_send_capable"])
            self.assertEqual(res["invariants"]["order_send_count"], 0)
            self.assertLessEqual(res["data_provenance"]["etf_super_sleeve_max_date"], "2024-12-31")
            self.assertLessEqual(res["data_provenance"]["crypto_carry_max_date"], "2024-12-31")
            self.assertLessEqual(res["data_provenance"]["crypto_spot_max_date"], "2024-12-31")
            self.assertGreater(res["data_provenance"]["etf_raw_holdout_rows_excluded"], 0)
            self.assertGreater(res["data_provenance"]["crypto_carry_raw_holdout_rows_excluded"], 0)

            # Hard CEX <= 25% & 4/4 Stress Pass
            self.assertLessEqual(res["ownbook_dev_performance"]["max_realized_cex_exposure_pct"], 25.0)
            health = res["ops4_health_snapshot"]
            self.assertEqual(health["holdout_rows_analysed"], 0)
            self.assertFalse(health["order_send_capable"])
            self.assertTrue(health["cex_cap_compliant"])
            self.assertTrue(health["stress_summary"]["all_passed"])
            self.assertEqual(health["stress_summary"]["passed"], 4)
            self.assertEqual(health["traffic_light"], TRAFFIC_GREEN)

            # Secondary AMBER compression probe verified
            probe = res["ops4_compression_amber_probe"]
            self.assertEqual(probe["traffic_light"], TRAFFIC_AMBER)
            self.assertIn(ops.FUNDING_COMPRESSION_ALERT_CODE, probe["active_alerts"])
            self.assertAlmostEqual(probe["effective_cex_exposure_pct"], 10.0, places=4)

            # Empirical 2022 Stress 3 beat static 60/40 cleanly
            s3 = res["extreme_stress_tests"][ops.STRESS_3_ID]
            self.assertTrue(s3["passed"])
            self.assertLess(s3["ownbook_2022_max_dd_pct"], s3["static_60_40_ief_2022_max_dd_pct"])
            self.assertEqual(len(str(res["report_sha256"])), 64)


if __name__ == "__main__":
    unittest.main()
