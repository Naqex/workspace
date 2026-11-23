"""Unit tests for Pass 24 (6 new causal MTF structural families + Dual-Firm FTMO/The5ers 2-Layer Evaluator)."""

import unittest
import numpy as np

import pass24_mtf_new_archetypes as p24


class TestPass24Suite(unittest.TestCase):
    def test_catalog_has_exact_16_specs_across_6_families(self):
        cat = p24.build_pass24_catalog()
        self.assertEqual(len(cat), 16)
        fams = {c["fam"] for c in cat}
        self.assertEqual(len(fams), 6)

    def test_causal_stop_breakout_never_fills_below_level_and_sl_first_is_conservative(self):
        t0 = 1577952000  # 2020-01-02 UTC
        times = np.array([t0, t0 + 60, t0 + 120], dtype=np.int64)
        # Minute 0: opens bid 100 / ask 101, spikes ask_high 112 crossing level=110; minute 2 flat at bid 110
        quotes = np.array([
            [100.0, 111.0, 99.0, 109.0, 101.0, 112.0, 100.0, 110.0],
            [109.0, 110.0, 108.0, 109.5, 110.0, 111.0, 109.0, 110.5],
            [110.0, 110.0, 110.0, 110.0, 111.0, 111.0, 111.0, 111.0],
        ], dtype=np.float64)
        tr = p24.replay_causal_intraday("US100", times, quotes, 0, 2, 1, max(110.0, quotes[0, 4]), 90.0)
        self.assertEqual(tr["reason"], "HARD_FLAT")
        self.assertAlmostEqual(tr["gross_usd"], 0.0, places=6)
        # Same-minute SL hit wins conservatively over TP
        tr_sl = p24.replay_causal_intraday("US100", times, quotes, 0, 2, 1, 110.0, 100.0, tp_p=111.0)
        self.assertEqual(tr_sl["reason"], "SL_GAP_OR_TOUCH")
        self.assertAlmostEqual(tr_sl["gross_usd"], -10.0, places=6)

    def test_the5ers_requires_3_profitable_days_ge_05pct_unlike_ftmo_4_trading_days(self):
        # 20 days each making +$20 (+0.4% on $5k -> total +$400, wait let's make +$18 = +0.36% * 30 days = +$540 > +10% target!)
        # On FTMO (min 4 trading days): PASSES Phase 1 easily!
        # On The5ers High Stakes (requires >= 3 days >= +0.5% = +$25/day): MUST NOT pass Phase 1 because 0 days reached +$25!
        nets = np.full(60, 18.0, dtype=np.float64)  # 0.36%/day < 0.50%/day threshold!
        dds = np.zeros(60, dtype=np.float64)
        flags = np.ones(60, dtype=np.int8)
        r_ftmo = p24.simulate_dual_firm_2layer(nets, dds, flags, firm="FTMO_SWING_10K", cap=5000.0, fee=39.0, n_paths=50)
        r_5ers = p24.simulate_dual_firm_2layer(nets, dds, flags, firm="THE5ERS_HS_5K", cap=5000.0, fee=39.0, n_paths=50)
        self.assertEqual(r_ftmo["pass_pct"]["24m"], 100.0)
        self.assertEqual(r_5ers["pass_pct"]["24m"], 0.0)

        # Now raise daily gain to +$26 (+0.52% >= 0.50%): BOTH pass 100%!
        nets_ok = np.full(60, 26.0, dtype=np.float64)
        r_5ers_ok = p24.simulate_dual_firm_2layer(nets_ok, dds, flags, firm="THE5ERS_HS_5K", cap=5000.0, fee=39.0, n_paths=50)
        self.assertEqual(r_5ers_ok["pass_pct"]["24m"], 100.0)

    def test_engine4_us100_sess_cont_mq5_export_is_clean_and_dryrun_safe(self):
        from mq5_whitebox_exporter import audit_open_source_mq5, export_sess_cont_mq5
        src = export_sess_cont_mq5({"asset": "US100.cash", "risk_pct": 0.50, "protocol_commit": "52a53cb785a6"})
        self.assertIn("input bool   InpDryRunLogOnly     = true;", src)
        self.assertIn("NewYorkUtcOffsetHours", src)
        aud = audit_open_source_mq5(src, filename="Naqex_WB_SESS_CONT_BRK40_US100.mq5")
        self.assertEqual(aud["red_flags"], [])
        self.assertEqual(aud["intake_verdict"], "CLEAN_FOR_PYTHON_REPLICATION")


if __name__ == "__main__":
    unittest.main()
