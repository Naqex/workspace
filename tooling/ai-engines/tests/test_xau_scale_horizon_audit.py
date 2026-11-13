from pathlib import Path
from decimal import Decimal as D
import sys
import subprocess
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from xau_scale_horizon_audit import first_passage,markout,friction_record,stop_record,summarize_passage,money


class ScaleHorizonTests(unittest.TestCase):
    def test_optimized_python_cannot_disable_input_guards(self):
        program=Path(__file__).resolve().parents[1]/'xau_scale_horizon_audit.py'
        run=subprocess.run([sys.executable,'-O',str(program),'--config','not-a-real-input.json'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('scale_audit_requires_assertions_enabled',run.stderr)
        self.assertNotIn('FileNotFoundError',run.stderr)

    def test_same_ms_first_boundary_keeps_source_order(self):
        quotes=[(0,1999700,2000000),(0,1992000,1992300),(0,2016000,2016300)]
        result=first_passage(quotes,0,2000000,'BUY',7500,1000)
        self.assertEqual((result['status'],result['index'],result['price_units']),('SL',1,1992000))

    def test_buy_and_sell_tp_use_limit_not_later_quote_improvement(self):
        buy=first_passage([(0,1999700,2000000),(1000,2016000,2016300)],0,2000000,'BUY',7500,2000)
        sell=first_passage([(0,2000000,2000300),(1000,1983000,1983300)],0,2000000,'SELL',7500,2000)
        self.assertEqual((buy['status'],buy['price_units']),('TP_2R',2015000))
        self.assertEqual((sell['status'],sell['price_units']),('TP_2R',1985000))

    def test_right_censoring_is_not_a_losing_boundary(self):
        row=first_passage([(0,1999700,2000000),(1000,2000000,2000300)],0,2000000,'BUY',7500,1000)
        self.assertEqual(row['status'],'RIGHT_CENSORED')
        self.assertFalse(row['path_incomplete'])

    def test_missing_cutoff_quote_is_not_forward_filled(self):
        row=first_passage([(0,1999700,2000000),(62000,2000000,2000300)],0,2000000,'BUY',7500,1000)
        self.assertEqual(row['status'],'MISSING_CUTOFF_QUOTE')

    def test_tick_gap_is_preserved_on_observed_hit(self):
        row=first_passage([(0,1999700,2000000),(70000,1990000,1990300)],0,2000000,'BUY',7500,70000)
        self.assertEqual(row['status'],'SL')
        self.assertTrue(row['path_incomplete'])

    def test_markout_is_distinct_from_protective_exit(self):
        qs=[(0,1999700,2000000),(1000,1990000,1990300),(2000,2015000,2015300)]
        result=markout(qs,[r[0] for r in qs],0,'BUY',2000)
        self.assertEqual(result['gross_usd_per_oz'],15)
        self.assertAlmostEqual(result['stress_net_usd_per_oz'],15-(2000+2015)*.000007-.4)

    def test_mid_spread_bridge_does_not_hide_tp_clipping(self):
        t=dict(day='2022-01-04',side='BUY',lot_steps=20,entry_units=2000000,entry_bid_units=1999700,entry_ask_units=2000000,
               exit_units=2015000,exit_bid_units=2016000,exit_ask_units=2016400,
               results=dict(reference=dict(commission_usd=.56,gross_after_spread_usd=300)))
        row=friction_record(t)
        self.assertAlmostEqual(row['roundtrip_mid_spread_usd_per_oz'],.35)
        self.assertAlmostEqual(row['commission_usd_per_oz'],.028)
        self.assertEqual(row['tp_no_improvement_usd_per_oz'],1)

    def test_stop_formula_separates_small_m15_buffer(self):
        row=stop_record(dict(day='2022-01-04',side='BUY',status='friction_cap_rejected',
            bar_units=[1999000,2001000,1998000,2000000],atr_units='2000',entry_units=2000300,
            entry_bid_units=2000000,entry_ask_units=2000300,stop_units=1997800,take_units=2005300))
        self.assertAlmostEqual(row['sl_usd_per_oz'],2.5)
        self.assertAlmostEqual(row['atr_buffer_usd_per_oz'],.2)
        self.assertAlmostEqual(row['close_to_bar_extreme_usd_per_oz'],2)
        self.assertAlmostEqual(row['entry_drift_usd_per_oz'],.3)

    def test_censored_median_keeps_unknown_upper_bound(self):
        def row(status,hours):return dict(status=status,observed_hours=hours,cutoff_hours=hours,
            path_incomplete=False,terminal_gross_usd_per_oz=0,terminal_stress_net_usd_per_oz=-.4)
        s=summarize_passage([row('SL',1),row('RIGHT_CENSORED',2),row('RIGHT_CENSORED',3)])
        self.assertEqual(s['event_times_hours_conditional_on_observed_boundary']['median'],1)
        self.assertIsNone(s['median_all_cohort_hours'])
        self.assertEqual(s['median_all_cohort_bounds'],dict(lower=2,upper=None))
        s=summarize_passage([row('SL',1),row('TP_2R',2),row('RIGHT_CENSORED',3)])
        self.assertEqual(s['median_all_cohort_hours'],2)


if __name__=='__main__':unittest.main()
