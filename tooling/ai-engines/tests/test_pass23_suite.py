"""Unit tests for Pass 23 (FTMO 2-Step Lifecycle Simulator, Engine #1 Tokyo-box .mq5 Exporter, and GER40/US100/XAUUSD discovery)."""

import unittest
import numpy as np

from mq5_whitebox_exporter import audit_open_source_mq5, export_tokyo_box_oco_mq5
import pass23_ftmo_lifecycle_sim as p23_life


class TestPass23Suite(unittest.TestCase):
    def test_ftmo_2step_breach_checked_before_target_and_min_days_enforced(self):
        # Reaching +10% in 2 days must NOT pass Phase 1 until 4 trading days are met
        nets = np.array([600.0, 600.0, 0.0, 0.0, 0.0, 300.0, 300.0, 0.0, 0.0], dtype=np.float64)
        dds = np.zeros(len(nets), dtype=np.float64)
        flags = np.array([1, 1, 1, 1, 0, 1, 1, 1, 1], dtype=np.int8)
        r = p23_life.simulate_two_step_path(nets, dds, flags, 10000.0)
        self.assertTrue(r["p1_passed"])
        self.assertTrue(r["p2_passed"])
        self.assertEqual(r["p1_day"], 4)  # Required 4 trading days even though +12% hit on day 2
        self.assertEqual(r["pass_day"], 9)

    def test_ftmo_daily_and_static_breach_conservative_ordering(self):
        # Intraday daily drop >= 5% ($500 on 10k) breaches EVEN IF end-of-day closes +$1,200!
        nets = np.array([1200.0, 100.0, 100.0, 100.0], dtype=np.float64)
        dds = np.array([500.0, 0.0, 0.0, 0.0], dtype=np.float64)
        flags = np.ones(4, dtype=np.int8)
        r = p23_life.simulate_two_step_path(nets, dds, flags, 10000.0)
        self.assertTrue(r["breached"])
        self.assertEqual(r["outcome"], "BREACH_DAILY_P1")

        # Static floor breach: balance drops to 9150, intraday dd 200 -> eq_low 8950 <= 9000 -> BREACH_STATIC_P1
        nets2 = np.array([-300.0, -300.0, -250.0, 50.0], dtype=np.float64)
        dds2 = np.array([300.0, 300.0, 250.0, 200.0], dtype=np.float64)
        r2 = p23_life.simulate_two_step_path(nets2, dds2, flags, 10000.0)
        self.assertTrue(r2["breached"])
        self.assertEqual(r2["outcome"], "BREACH_STATIC_P1")

    def test_continuous_lifecycle_refunds_fee_once_and_splits_80pct(self):
        # 4 days P1 (+1000), 4 days P2 (+500), 10 days Funded (+1000) -> 80%*$1000 + $168 refund - $168 fee = +$800 net
        nets = np.array([250.0] * 4 + [125.0] * 4 + [100.0] * 10, dtype=np.float64)
        dds = np.zeros(len(nets), dtype=np.float64)
        flags = np.ones(len(nets), dtype=np.int8)
        cf = p23_life.simulate_continuous_lifecycle(nets, dds, flags, 10000.0, 168.0, horizon_days=len(nets))
        self.assertTrue(cf["reached_funded"])
        self.assertEqual(cf["breaches"], 0)
        self.assertAlmostEqual(cf["payouts_total_usd"], 800.0 + 168.0, places=2)
        self.assertAlmostEqual(cf["net_cashflow_usd"], 800.0, places=2)

    def test_engine1_tokyo_box_mq5_export_is_clean_and_dryrun_safe(self):
        src = export_tokyo_box_oco_mq5({"asset": "USDJPY", "risk_pct": 0.30, "protocol_commit": "5eb0506089d1"})
        self.assertIn("input bool   InpDryRunLogOnly      = true;", src)
        self.assertIn("HelsinkiUtcOffsetHours", src)
        aud = audit_open_source_mq5(src, filename="Naqex_WB_TOKYO_BOX_USDJPY.mq5")
        self.assertEqual(aud["red_flags"], [])
        self.assertEqual(aud["intake_verdict"], "CLEAN_FOR_PYTHON_REPLICATION")

    def test_index_stop_breakout_never_fills_better_than_trigger(self):
        import pass23_xau_indices_discovery as p23_d
        # Minute 0: bar opens at 100.00 (ask 101.00), spikes to ask_high 112.00 crossing top=110.00, closes at 110.00.
        # Minute 1: flat exit at bid_open=110.00 -> causal stop entry MUST fill at 110.00 (gross=0.0), NOT at ask_open=101.00 (+9.0 lookahead!)
        t0 = 1577952000  # 2020-01-02 UTC
        times = np.array([t0, t0 + 60], dtype=np.int64)
        quotes = np.array([
            [100.0, 111.0, 99.0, 109.0, 101.0, 112.0, 100.0, 110.0],
            [110.0, 110.0, 110.0, 110.0, 111.0, 111.0, 111.0, 111.0],
        ], dtype=np.float64)
        sess = {"day": "2020-01-02", "year": 2020, "start": t0, "lo": 0, "hi": 2, "o": 100.0}
        # 1) With SL below bar low (sl_pts=20 -> sl=90 < 99), causal fill at 110.0 gives gross=0.0 (NOT +9.0 from ask_open=101!)
        tr = p23_d.sim_index_trade(times, quotes, sess, 0, 1, 20.0, entry_price_override=max(110.0, quotes[0, 4]))
        self.assertEqual(tr["reason"], "HARD_FLAT")
        self.assertAlmostEqual(tr["gross_usd"], 0.0, places=6)
        # 2) With SL=100 >= bar low 99, conservative SL-first triggers immediately on entry minute
        tr_sl = p23_d.sim_index_trade(times, quotes, sess, 0, 1, 10.0, entry_price_override=max(110.0, quotes[0, 4]))
        self.assertEqual(tr_sl["reason"], "SL_GAP_OR_TOUCH")
        self.assertAlmostEqual(tr_sl["gross_usd"], -10.0, places=6)


if __name__ == "__main__":
    unittest.main()
