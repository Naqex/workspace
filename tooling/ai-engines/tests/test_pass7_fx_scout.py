"""Tests for causal FX currency conversion and the frozen Stage-0 gate."""

import unittest

import numpy as np

import pass5_usdjpy_tokyo as tokyo
from pass7_fx_scout import admitted, paired_loss_correlation, quote_cash, scout_cost


class Pass7FxScoutTests(unittest.TestCase):
    def test_quote_cash_checks_pip_and_conversion_per_symbol(self):
        spec = {'commission_usd_per_lot_roundtrip': 5., 'spec': {'trade_contract_size': 100000.},
                'spread': {'median': .9}}
        pip, cost = scout_cost('EURJPY', spec)
        breakout = quote_cash(160., 160.1, 1, cost=cost, pip=pip, quote_per_usd=150.)
        fade = quote_cash(160., 160.1, -1,cost=cost,pip=pip,quote_per_usd=150.)
        self.assertAlmostEqual(breakout['gross'], 10000/150)
        self.assertAlmostEqual(breakout['spread'], 900/150)
        self.assertAlmostEqual(breakout['slippage'], 400/150)
        self.assertAlmostEqual(breakout['net'] + fade['net'], -2*breakout['cost'])
        pip, cost = scout_cost('EURUSD', spec)
        usd = quote_cash(1.20, 1.201, 1, cost=cost, pip=pip)
        self.assertAlmostEqual(usd['gross'], 100.)
        self.assertAlmostEqual(usd['spread'], 9.)
        self.assertAlmostEqual(usd['slippage'], 4.)
        self.assertAlmostEqual(usd['net'], 82.)

    def test_stage0_scale_is_a_cohort_gate_not_a_filter(self):
        score = {'pass_stage0': True, 'friction_scale': {
            'median_cost_over_median_stop_pct': 12., 'pass_share_at_12pct': .5}}
        self.assertTrue(admitted(score))
        score['friction_scale']['pass_share_at_12pct'] = .49
        self.assertFalse(admitted(score))
        score['friction_scale']['pass_share_at_12pct'] = .9
        score['pass_stage0'] = False
        self.assertFalse(admitted(score))

    def test_missing_simultaneous_conversion_rejects_the_paired_day(self):
        start = tokyo.START
        hours = {start + i*tokyo.HOUR: tokyo.Bar(150.,150.04,149.96,150.) for i in range(19)}
        for i in range(3):
            hours[start + i*tokyo.HOUR] = tokyo.Bar(150.,150.1,149.9,150.)
        hours[start+3*tokyo.HOUR] = tokyo.Bar(150.1,150.2,150.05,150.16)
        calls = []
        def value(at, entry, exit_, side):
            calls.append(at)
            raise KeyError(at)
        observed = tokyo.run_day(start,hours,np.array([]),np.array([]),tokyo.Costs(.3,5.,100000.),
                                 value_at=value)
        self.assertEqual(observed, ('missing_conversion_quote', False, None))
        self.assertEqual(calls, [start+8*tokyo.HOUR])

    def test_correlation_only_matches_observed_days(self):
        first = [{'day': 'a','net_R': -1}, {'day': 'b','net_R': -2}]
        second = [{'day': 'a','net_R': 3}, {'day': 'b','net_R': 4}, {'day': 'c','net_R': 0}]
        measured = paired_loss_correlation(second,first)
        self.assertEqual(measured['USDJPY_negative'], {'n': 2,'pearson': -1.})
