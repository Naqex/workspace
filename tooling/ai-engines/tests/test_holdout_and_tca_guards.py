"""Regression tests for Holdout 2025+ guards, production red-news CSV protection & TCA symbol normalization."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
EXPORTS_DIR = AI_ENGINES / "exports"
REPO_ROOT = AI_ENGINES.parents[1]

for p in (AI_ENGINES, EXPORTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import mt5_realtick_runner as rt_runner  # noqa: E402
from native_ftmo_monfri_seal import STOP  # noqa: E402
from quant_factory import (  # noqa: E402
    auto_research_loop as arl,
)
from quant_factory import (  # noqa: E402
    data_store,
    prop_engine,
)
from quant_factory import (  # noqa: E402
    holdout_eval_2025_2026 as heval,
)
from quant_factory import (  # noqa: E402
    tca_reconcile as tca,
)


class HoldoutAndTcaGuardTests(unittest.TestCase):
    def test_holdout_eval_refuses_without_explicit_unlock_flag_and_protects_prod_csv(self):
        prod_csv = EXPORTS_DIR / "Files/naqex_red_news_utc.csv"
        tracked_json = AI_ENGINES / "configs/calendars/red_news_official_2025_2026.json"
        self.assertTrue(prod_csv.exists())
        self.assertTrue(tracked_json.exists())
        before_sha = hashlib.sha256(prod_csv.read_bytes()).hexdigest()
        before_json_sha = hashlib.sha256(tracked_json.read_bytes()).hexdigest()

        # 1. Calling main([]) without --confirm-one-time-holdout-unlock MUST exit 2 fail-closed
        rc = heval.main([])
        self.assertEqual(rc, 2)

        # 2. Subprocess CLI invocation without flag also fails closed with exit 2
        proc = subprocess.run(
            [sys.executable, str(AI_ENGINES / "quant_factory/holdout_eval_2025_2026.py")],
            capture_output=True, text=True, check=False, timeout=20,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("HOLDOUT_LOCKED", proc.stderr)

        # 3. Attempting to export holdout CSV over production red-news CSV or configs/calendars MUST raise
        with self.assertRaises(ValueError) as cm:
            heval.build_2025_2026_red_news_calendar_and_export_csv(out_csv_path=prod_csv)
        self.assertIn("SAFETY ABORT", str(cm.exception))
        with self.assertRaises(ValueError) as cm2:
            heval.build_2025_2026_red_news_calendar_and_export_csv(out_csv_path=tracked_json)
        self.assertIn("SAFETY ABORT", str(cm2.exception))

        # 4. Exporting to an isolated temp path succeeds while production CSV & tracked JSON stay untouched
        with tempfile.TemporaryDirectory() as td:
            iso_csv = Path(td) / "holdout_red_news_usd_2018_2026.csv"
            cal = heval.build_2025_2026_red_news_calendar_and_export_csv(out_csv_path=iso_csv)
            self.assertTrue(iso_csv.exists())
            self.assertTrue(iso_csv.with_suffix(".json").exists())
            self.assertGreater(len(cal), 30)

        after_sha = hashlib.sha256(prod_csv.read_bytes()).hexdigest()
        after_json_sha = hashlib.sha256(tracked_json.read_bytes()).hexdigest()
        self.assertEqual(before_sha, after_sha, "Production red-news CSV SHA changed!")
        self.assertEqual(before_json_sha, after_json_sha, "Tracked red_news_official_2025_2026.json SHA changed!")

    def test_data_store_and_prop_engine_reject_2025_holdout_days_and_timestamps(self):
        # Valid dev days/stamps pass
        good_tapes = {"E1": {"2024-12-30": ({}, np.array([STOP - 3600, STOP - 60], dtype=np.int64), np.zeros((2, 4)))}}
        data_store.assert_dev_series_strictly_pre_holdout(["2024-12-30", "2024-12-31"], good_tapes)

        # Day >= 2025-01-01 fails in data_store
        with self.assertRaises(ValueError):
            data_store.assert_dev_series_strictly_pre_holdout(["2024-12-31", "2025-01-01"])

        # Stamp >= STOP fails in data_store even when day key claims 2024-12-31
        bad_stamp_tapes = {"E1": {"2024-12-31": ({}, np.array([STOP - 60, STOP], dtype=np.int64), np.zeros((2, 4)))}}
        with self.assertRaises(ValueError):
            data_store.assert_dev_series_strictly_pre_holdout(["2024-12-31"], bad_stamp_tapes)

        # prop_engine.replay_portfolio_m1 rejects 2025-01-01 day, cutoff > STOP, and stamp >= STOP by default
        with self.assertRaises(ValueError):
            prop_engine.replay_portfolio_m1(["2025-01-01"], {"E1": {}}, {"E1": 0.005})
        with self.assertRaises(ValueError):
            prop_engine.replay_portfolio_m1(["2024-12-30"], good_tapes, {"E1": 0.005}, cutoff=STOP + 60)
        with self.assertRaises(ValueError):
            prop_engine.replay_portfolio_m1(["2024-12-31"], bad_stamp_tapes, {"E1": 0.005})

        # prop_engine.apply_vol_targeting_causal rejects 2025-01-01 by default
        arr = np.zeros(5, dtype=np.float64)
        with self.assertRaises(ValueError):
            prop_engine.apply_vol_targeting_causal(
                ["2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03", "2025-01-04"],
                arr,
                arr,
            )

    def test_auto_research_loop_rejects_holdout_end_day_and_nonzero_holdout_rows(self):
        # 1. end_day >= 2025-01-01 rejected
        bad_spec_end = {
            "evaluator": {
                "kind": "inline_arrays",
                "end_day": "2025-01-01",
                "cluster_a_returns": [0.001] * 30,
                "cluster_b_returns": [0.001] * 30,
                "p_value_raw": 0.01,
                "cost_1x_net": 1.0,
                "cost_2x_net": 0.8,
                "n_trades_cluster_b": 40,
                "holdout_rows_analysed": 0,
            }
        }
        with self.assertRaises(ValueError) as cm1:
            arl._builtin_evaluate_spec(bad_spec_end, dev_ctx={})
        self.assertIn("HOLDOUT_LOCK_VIOLATION", str(cm1.exception))

        # 2. holdout_rows_analysed > 0 rejected
        bad_spec_rows = {
            "evaluator": {
                "kind": "inline_arrays",
                "end_day": "2024-12-31",
                "cluster_a_returns": [0.001] * 30,
                "cluster_b_returns": [0.001] * 30,
                "p_value_raw": 0.01,
                "cost_1x_net": 1.0,
                "cost_2x_net": 0.8,
                "n_trades_cluster_b": 40,
                "holdout_rows_analysed": 12,
            }
        }
        with self.assertRaises(ValueError) as cm2:
            arl._builtin_evaluate_spec(bad_spec_rows, dev_ctx={})
        self.assertIn("HOLDOUT_LOCK_VIOLATION", str(cm2.exception))

        # 3. cluster_b_start >= 2025-01-01 rejected
        bad_spec_split = {
            "evaluator": {
                "kind": "sleeve_json",
                "json_path": "nonexistent.json",
                "cluster_b_start": "2025-01-01",
                "end_day": "2024-12-31",
            }
        }
        with self.assertRaises(ValueError) as cm3:
            arl._builtin_evaluate_spec(bad_spec_split, dev_ctx={})
        self.assertIn("HOLDOUT_LOCK_VIOLATION", str(cm3.exception))

    def test_mt5_realtick_runner_blocks_2025_dates_in_all_entrypoints(self):
        fake_root = REPO_ROOT / ".runtime/ftmo-demo-portable-1515343166"
        eng = rt_runner.ENGINE_TEST_PLAN[0]

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            # 1. run_single_tester_job blocks ToDate >= 2025.01.01 before touching MT5
            with self.assertRaises(ValueError) as cm1:
                rt_runner.run_single_tester_job(
                    portable_root=fake_root,
                    engine_spec=eng,
                    latency_ms=50,
                    from_date="2024.09.01",
                    to_date="2025.01.01",
                    results_dir=out_dir,
                )
            self.assertIn("HOLDOUT LOCK VIOLATION", str(cm1.exception))

            # 2. run_suite blocks ToDate >= 2025.01.01
            with self.assertRaises(ValueError) as cm2:
                rt_runner.run_suite(
                    portable_root=fake_root,
                    results_dir=out_dir,
                    from_date="2024.09.01",
                    to_date="2025-03-01",
                )
            self.assertIn("HOLDOUT LOCK VIOLATION", str(cm2.exception))

            # 3. run_master_prop7e_job blocks FromDate >= 2025.01.01
            with self.assertRaises(ValueError) as cm3:
                rt_runner.run_master_prop7e_job(
                    portable_root=fake_root,
                    results_dir=out_dir,
                    from_date="2025.01.02",
                    to_date="2025.02.01",
                )
            self.assertIn("HOLDOUT LOCK VIOLATION", str(cm3.exception))

        # Valid Dev date passes assert_dev_date_sealed cleanly
        rt_runner.assert_dev_date_sealed("2024.12.31", "2024.01.01")

    def test_tca_reconcile_normalizes_broker_suffixes_and_aliases_without_point_distortion(self):
        cases = [
            ("USDJPY.pro", "USDJPY", 0.001, 7.0),
            ("USDJPYm", "USDJPY", 0.001, 7.0),
            ("EURJPY+", "EURJPY", 0.001, 14.0),
            ("CADJPY.raw", "CADJPY", 0.001, 16.0),
            ("SGDJPY.raw", "SGDJPY", 0.001, None),
            ("GBPUSD.ecn", "GBPUSD", 0.00001, 6.0),
            ("NAS100", "US100", 0.01, 20.0),
            ("USTECm", "US100", 0.01, 20.0),
            ("US100.cash", "US100", 0.01, 20.0),
            ("SPX500", "US500", 0.01, 6.0),
            ("US500.cash", "US500", 0.01, 6.0),
            ("XAUUSDm", "XAUUSD", 0.01, 28.0),
            ("GOLD.pro", "XAUUSD", 0.01, 28.0),
        ]
        for raw, exp_canon, exp_pt, exp_bench in cases:
            self.assertEqual(tca.normalize_symbol_alias(raw), exp_canon, f"Alias failed for {raw}")
            self.assertAlmostEqual(tca.point_size_for_symbol(raw), exp_pt, places=8, msg=f"Point size failed for {raw}")
            self.assertEqual(tca.benchmark_spread_for_symbol(raw), exp_bench, f"Bench spread failed for {raw}")

        # Verify exact slippage points calculation on suffixed symbols (zero 100x-1000x blowup!)
        fills = [
            {
                "utc_ts": 1730000000, "magic": 20261123, "symbol": "USDJPY.pro", "side": "BUY",
                "event_type": "ORDER_FILL", "signal_price": 152.000, "fill_price": 152.005,
                "sl_price": 151.000, "lots": 0.10, "spread_pts": 7.0, "latency_ms": 80.0,
                "retcode": 10009, "comment": "", "swap_usd": 0.0,
            },
            {
                "utc_ts": 1730000100, "magic": 20261124, "symbol": "NAS100", "side": "SELL",
                "event_type": "ORDER_FILL", "signal_price": 20500.00, "fill_price": 20499.50,
                "sl_price": 20600.00, "lots": 0.10, "spread_pts": 20.0, "latency_ms": 90.0,
                "retcode": 10009, "comment": "", "swap_usd": 0.0,
            },
            {
                "utc_ts": 1730000200, "magic": 20261125, "symbol": "XAUUSDm", "side": "BUY",
                "event_type": "ORDER_FILL", "signal_price": 2650.00, "fill_price": 2650.10,
                "sl_price": 2630.00, "lots": 0.10, "spread_pts": 28.0, "latency_ms": 70.0,
                "retcode": 10009, "comment": "", "swap_usd": 0.0,
            },
        ]
        rep = tca.compute_tca_report(fills)
        self.assertEqual(rep["verdict"], "GREEN")
        self.assertAlmostEqual(rep["per_symbol_mean_slip_pts"]["USDJPY.pro"], 5.0, places=2)
        self.assertAlmostEqual(rep["per_symbol_mean_slip_pts"]["NAS100"], 50.0, places=2)
        self.assertAlmostEqual(rep["per_symbol_mean_slip_pts"]["XAUUSDm"], 10.0, places=2)
        self.assertAlmostEqual(rep["spread_vs_benchmark_ratio"]["mean"], 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
