"""Regression & contract tests for the 4-layer Quant Factory (zero-pickle cache, Numba JIT, DSR, per-symbol risk cap, PropGuard.mqh)."""

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import (
    _load_tapes_safe_npz,
    _save_tapes_safe_npz,
    assert_holdout_locked,
    load_firm_config,
    load_profile_config,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.eval_pipeline import (
    benjamini_hochberg,
    deflated_sharpe_ratio,
    sign_flip_p_numba,
    tail_correlation_report,
)
from quant_factory.prop_engine import (
    apply_vol_targeting_causal,
    evaluate_firm_profile,
    replay_portfolio_m1,
)
from quant_factory.report_gen import format_markdown_table, write_verified_receipt


class QuantFactorySuiteTests(unittest.TestCase):
    def test_holdout_lock_registry_and_declarative_configs_load(self):
        sha_hex = assert_holdout_locked()
        self.assertEqual(len(sha_hex), 64)
        reg = load_registry()
        self.assertEqual(len(reg["engines"]), 9)
        self.assertEqual(reg["holdout_lock"]["holdout_rows_analysed"], 0)
        self.assertEqual(reg["holdout_lock"]["order_send_count"], 0)

        for firm in ("ftmo_swing_10k", "ftmo_standard_10k", "the5ers_high_stakes_5k", "the5ers_hyper_growth_5k", "exness_personal_sf"):
            cfg = load_firm_config(firm)
            self.assertIn("capital_usd", cfg)
            self.assertIn("fee_usd", cfg)
        for prof in ("p1_sprint_25x", "p1_sprint_30x", "p1_smooth_invdd_vt", "funded_harvest_core", "personal_vault"):
            cfg = load_profile_config(prof)
            self.assertIn("p1_mult", cfg)
            self.assertIn("amber_dd_pct", cfg)
        cal = load_red_news_calendar()
        self.assertEqual(sum(len(v) for v in cal.values()), 224)

    def test_zero_pickle_npz_tape_cache_roundtrip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            stamps = np.array([1704153600, 1704153660, 1704153720], dtype=np.int64)
            marks = np.array([[0.0, 5.0, -2.0, 3.0], [3.0, 9.0, 1.0, 8.0], [8.0, 12.0, 6.0, 10.0]], dtype=np.float64)
            tapes = {
                "E1_TEST": {
                    "2024-01-02": ({"day": "2024-01-02", "asset": "USDJPY", "entry": 1704153600, "net_usd_per_lot": 10.0}, stamps, marks),
                }
            }
            meta = {"binding_sha256": "abc123", "ext_days": ["2024-01-02"], "strict_cluster_a_days": []}
            _save_tapes_safe_npz(d, "unit_tape", meta, tapes)

            hit = _load_tapes_safe_npz(d, "unit_tape", "abc123")
            self.assertIsNotNone(hit)
            _, loaded = hit
            row, s2, m2 = loaded["E1_TEST"]["2024-01-02"]
            self.assertEqual(row["asset"], "USDJPY")
            np.testing.assert_array_equal(s2, stamps)
            np.testing.assert_allclose(m2, marks)

            # Binding SHA mismatch must reject cache hit
            self.assertIsNone(_load_tapes_safe_npz(d, "unit_tape", "wrong_binding"))

    def test_numba_sign_flip_bh_dsr_and_tail_correlation(self):
        rng = np.random.default_rng(42)
        vals = rng.normal(loc=0.45, scale=0.8, size=120)
        fade = -vals
        p = sign_flip_p_numba(vals, fade, draws=1000, seed=12345)
        self.assertLess(p, 0.01)

        qs = benjamini_hochberg([0.001, 0.02, 0.50])
        self.assertAlmostEqual(qs[0], 0.003, places=6)
        self.assertAlmostEqual(qs[1], 0.03, places=6)
        self.assertAlmostEqual(qs[2], 0.50, places=6)

        # DSR monotonically decreases as M trials increases
        daily = rng.normal(loc=0.0005, scale=0.005, size=1500)
        d1 = deflated_sharpe_ratio(daily, n_trials=1)
        d40 = deflated_sharpe_ratio(daily, n_trials=40)
        d500 = deflated_sharpe_ratio(daily, n_trials=500)
        self.assertGreater(d1["dsr"], d40["dsr"])
        self.assertGreater(d40["dsr"], d500["dsr"])

        # Tail correlation report separates normal vs worst 5% days
        mat = rng.normal(0.0, 0.004, size=(400, 3))
        tc = tail_correlation_report(mat, ["A", "B", "C"], tail_pct=0.05)
        self.assertEqual(tc["n_days_all"], 400)
        self.assertEqual(tc["n_days_tail"], 20)
        self.assertIn("max_pair", tc["worst_tail_corr"])

    def test_causal_vol_targeting_and_per_symbol_concurrent_risk_cap(self):
        days = [f"2020-01-{i:02d}" for i in range(1, 32)] + [f"2021-02-{i:02d}" for i in range(1, 29)]
        nets = np.array([10.0 if i % 2 == 0 else -5.0 for i in range(31)] + [100.0 if i % 2 == 0 else -80.0 for i in range(28)], dtype=np.float64)
        dds = np.abs(nets) * 0.5
        vn, vd = apply_vol_targeting_causal(days, nets, dds, window=10, lo=0.55, hi=1.35)
        # During high-vol 2021 regime, causal vol-targeting must scale exposure DOWN (lo=0.55)
        self.assertLess(abs(vn[-1]), abs(nets[-1]))
        self.assertAlmostEqual(vn[-1], nets[-1] * 0.55, places=6)

        # Two concurrent trades on US100 each asking 0.75% risk -> capped to 1.00% total (second trimmed to 0.25%)
        ts0 = 1704200400  # 2024-01-02 13:00 UTC (same Prague day)
        stamps1 = np.array([ts0, ts0 + 60, ts0 + 120], dtype=np.int64)
        stamps2 = np.array([ts0 + 60, ts0 + 120, ts0 + 180], dtype=np.int64)
        marks = np.array([[0.0, 20.0, -50.0, 10.0], [10.0, 30.0, -10.0, 20.0], [20.0, 40.0, 0.0, 30.0]], dtype=np.float64)
        row1 = {"day": "2024-01-02", "asset": "US100", "entry": ts0, "exit": ts0 + 180, "at_open": False, "entry_price": 17000.0, "stop_risk_with_cost_usd": 100.0, "net_usd_per_lot": 30.0}
        row2 = {"day": "2024-01-02", "asset": "US100", "entry": ts0 + 60, "exit": ts0 + 240, "at_open": False, "entry_price": 17010.0, "stop_risk_with_cost_usd": 100.0, "net_usd_per_lot": 30.0}
        tapes = {"E4": {"2024-01-02": (row1, stamps1, marks)}, "E5": {"2024-01-02": (row2, stamps2, marks)}}
        met_uncap, _ = replay_portfolio_m1(["2024-01-02"], tapes, {"E4": 0.0075, "E5": 0.0075}, 10000.0, max_symbol_concurrent_risk=None)
        met_cap, exits_cap = replay_portfolio_m1(["2024-01-02"], tapes, {"E4": 0.0075, "E5": 0.0075}, 10000.0, max_symbol_concurrent_risk=0.0100)
        self.assertEqual(met_uncap["sym_cap_hits"], 0)
        self.assertEqual(met_cap["sym_cap_hits"], 1)
        self.assertLess(met_cap["net_usd"], met_uncap["net_usd"])
        eff_sum = sum(o["eff_risk"] for o in exits_cap[0]["orders"])
        self.assertAlmostEqual(eff_sum, 0.0100, places=6)

    def test_numba_lifecycle_2step_and_1step_pause_parity(self):
        # 1-Step Hyper Growth non-breaching 3% daily pause
        nets = np.array([-400.0] + [150.0] * 15, dtype=np.float64)
        dds = np.array([400.0] + [20.0] * 15, dtype=np.float64)
        flg = np.ones(16, dtype=np.int8)
        idx = np.array([np.arange(16, dtype=np.int32)])
        hg_cfg = load_firm_config("the5ers_hyper_growth_5k")
        prof = {**load_profile_config("p1_sprint_25x"), "p1_mult": 1.0, "p2_mult": 1.0, "funded_mult": 1.0, "amber_dd_pct": 0.99, "red_dd_pct": 0.99}
        res_hg = evaluate_firm_profile(idx, (nets, dds, flg), (nets, dds, flg), hg_cfg, prof)
        self.assertEqual(res_hg["br1_pct"], 0.0)
        self.assertEqual(res_hg["pass_3m"], 100.0)

        # 2-Step FTMO Swing: clean positive stream passes both steps & collects payout
        nets2 = np.full(60, 120.0, dtype=np.float64)
        dds2 = np.full(60, 20.0, dtype=np.float64)
        flg2 = np.ones(60, dtype=np.int8)
        idx2 = np.array([np.arange(60, dtype=np.int32)])
        ftmo_cfg = load_firm_config("ftmo_swing_10k")
        res_ftmo = evaluate_firm_profile(idx2, (nets2, dds2, flg2), (nets2, dds2, flg2), ftmo_cfg, prof)
        self.assertEqual(res_ftmo["pass_3m"], 100.0)
        self.assertGreater(res_ftmo["cf24_mean"], 0.0)

    def test_report_gen_and_propguard_mqh_static_audit(self):
        md = format_markdown_table(["A", "B"], [["x", 1], ["y", 2]], right_align_cols={1})
        self.assertIn("|---|---:|", md)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.json"
            digest = write_verified_receipt(out, {"ok": True})
            self.assertEqual(len(digest), 64)
            self.assertTrue(out.with_suffix(".sha256").exists())
            with self.assertRaises(FileExistsError):
                write_verified_receipt(out, {"ok": False}, overwrite=False)

        import mq5_whitebox_exporter as exp
        mqh_path = AI_ENGINES / "exports/Include/Naqex_PropGuard.mqh"
        src = mqh_path.read_text(encoding="utf-8")
        audit = exp.audit_open_source_mq5(src, filename=mqh_path.name)
        self.assertEqual(audit["red_flags"], [])
        self.assertEqual(audit["intake_verdict"], "CLEAN_FOR_PYTHON_REPLICATION")
        for required in (
            "InpGuardDryRunLogOnly     = true;",
            "SYMBOL_TRADE_TICK_VALUE_LOSS",
            "SYMBOL_FILLING_MODE",
            "SymbolInfoSessionTrade",
            "InpGuardMaxSymbolRiskPct",
            "GlobalVariableSet",
            "TRADE_RETCODE_DONE",
            "MQL_TESTER",
            "NQXG_GLOBAL_KILLSWITCH",
            "NQXG_GLOBAL_RISK_MULT",
            "LogExecAuditFor",
        ):
            self.assertIn(required, src)

    def test_all_8_eas_and_orchestrator_use_propguard_and_unique_magics(self):
        import re
        import mq5_whitebox_exporter as exp
        exp_dir = AI_ENGINES / "exports"
        eas = sorted(p for p in exp_dir.glob("Naqex_WB_*.mq5"))
        self.assertEqual(len(eas), 8)
        magics = []
        for f in eas:
            src = f.read_text(encoding="utf-8")
            aud = exp.audit_open_source_mq5(src, filename=f.name)
            self.assertEqual(aud["red_flags"], [], f"{f.name} had red flags")
            self.assertIn('#include "Include/Naqex_PropGuard.mqh"', src)
            self.assertIn("InpDryRunLogOnly", src)
            m = re.search(r"InpMagicNumber\s*=\s*(\d+)\s*;", src)
            self.assertIsNotNone(m, f"Missing magic in {f.name}")
            magics.append(int(m.group(1)))
        # All 8 EAs must have strictly unique Magic Numbers inside Orchestrator range 20261120..20261199
        self.assertEqual(len(set(magics)), 8, f"Duplicate magic numbers found: {magics}")
        for mg in magics:
            self.assertTrue(20261120 <= mg <= 20261199, f"Magic {mg} outside orchestrator range")

        orch = (exp_dir / "Naqex_AccountOrchestrator.mq5").read_text(encoding="utf-8")
        self.assertIn("InpDryRunLogOnly", orch)
        self.assertIn("NQXG_GLOBAL_KILLSWITCH", orch)
        self.assertIn("NQXG_GLOBAL_RISK_MULT", orch)
        self.assertIn("naqex_heartbeat.json", orch)
        self.assertTrue((exp_dir / "Files/naqex_red_news_utc.csv").exists())

    def test_tca_reconcile_live_decay_cusum_and_ops_monitor(self):
        import json
        from quant_factory.tca_reconcile import compute_tca_report
        from quant_factory.live_decay_monitor import evaluate_live_decay
        from quant_factory.ops_monitor import dispatch_alert, inspect_heartbeat

        # 1. TCA: clean fills -> GREEN; high slippage + swap violation -> RED
        clean = [
            {"symbol": "US100.cash", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 20000.0, "fill_price": 20001.0, "sl_price": 19900.0, "spread_pts": 18.0, "latency_ms": 95.0, "swap_usd": 0.0},
            {"symbol": "USDJPY", "side": "SELL", "event_type": "ORDER_FILL", "signal_price": 150.000, "fill_price": 149.995, "sl_price": 150.800, "spread_pts": 6.0, "latency_ms": 110.0, "swap_usd": 0.0},
        ]
        r_ok = compute_tca_report(clean)
        self.assertEqual(r_ok["verdict"], "GREEN")
        bad = [{**clean[0], "fill_price": 20035.0, "swap_usd": -4.5}]
        r_bad = compute_tca_report(bad)
        self.assertEqual(r_bad["verdict"], "RED_SWAP_VIOLATION")
        self.assertEqual(r_bad["swap_violations"], 1)

        # 2. Live Decay Monitor: healthy stream -> GREEN; severe negative drift -> RED_HALT_ALPHA_DECAY
        rng = np.random.default_rng(7)
        dev = rng.normal(loc=0.05, scale=0.40, size=600)
        live_ok = rng.normal(loc=0.06, scale=0.40, size=120)
        live_dead = rng.normal(loc=-0.18, scale=0.40, size=120)
        d_ok = evaluate_live_decay(dev, live_ok)
        d_dead = evaluate_live_decay(dev, live_dead)
        self.assertEqual(d_ok["verdict"], "GREEN_WITHIN_EXPECTATION")
        self.assertEqual(d_dead["verdict"], "RED_HALT_ALPHA_DECAY")
        self.assertTrue(d_dead["cusum"]["active_breach"])

        # 3. Ops Monitor: fresh OK heartbeat vs stale/killswitch/orphan alerts (always dry_run safe)
        with tempfile.TemporaryDirectory() as td:
            hb = Path(td) / "naqex_heartbeat.json"
            hb.write_text(json.dumps({
                "utc_ts": 1700000000, "balance": 10000.0, "equity": 10020.0,
                "daily_dd_pct": 0.1, "static_dd_pct": 0.0, "regime": "NORMAL",
                "risk_mult": 1.0, "kill_switch": False, "open_positions": 1, "orphan_no_sl": 0, "dry_run": True,
            }), encoding="utf-8")
            rep_ok = inspect_heartbeat(hb, now_utc_ts=1700000030)
            self.assertEqual(rep_ok["status"], "OK")
            rep_stale = inspect_heartbeat(hb, now_utc_ts=1700000500)
            self.assertEqual(rep_stale["status"], "CRITICAL")
            res_alert = dispatch_alert(rep_stale, dry_run=True)
            self.assertFalse(res_alert["sent"])
            self.assertIn("HEARTBEAT_STALE", res_alert["message"])


if __name__ == "__main__":
    unittest.main()
