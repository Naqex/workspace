import unittest
import numpy as np
from quant_core.corpus_batch_signals import pattern,oscillator,signals,PATTERNS
from quant_core.corpus_signals import engulfing_rsi


class CorpusBatchSignalTests(unittest.TestCase):
    def frame(self):
        random=np.random.default_rng(124)
        c=100+np.cumsum(random.normal(0,1,300))
        o=c+random.normal(0,.8,300)
        return dict(o=o,c=c,h=np.maximum(c,o)+1,l=np.minimum(c,o)-1)

    def test_engulfing_rsi_preserves_v25_formula(self):
        frame=self.frame()
        np.testing.assert_equal(signals(frame,"Engulfing","RSI"),engulfing_rsi(frame))

    def test_every_pattern_uses_only_closed_prefix(self):
        frame=self.frame()
        for name in PATTERNS:
            np.testing.assert_equal(pattern({k:v[:180] for k,v in frame.items()},name),
                                    pattern(frame,name)[:180])

    def test_oscillators_are_causal_for_all_four_source_defaults(self):
        frame=self.frame()
        for name in ("RSI","CCI","Stoch","MFI"):
            volume=np.arange(300)+1 if name=="MFI" else None
            prefix={k:v[:180] for k,v in frame.items()}
            np.testing.assert_allclose(oscillator(prefix,name,volume[:180] if volume is not None else None),
                                       oscillator(frame,name,volume)[:180],equal_nan=True)

    def test_mfi_refuses_bar_count_as_implicit_volume(self):
        with self.assertRaisesRegex(ValueError,"ADMITTED_TICK_VOLUME"):
            oscillator(self.frame(),"MFI")

    def test_mfi_rejects_invalid_volume(self):
        with self.assertRaisesRegex(ValueError,"INVALID_TICK_VOLUME"):
            oscillator(self.frame(),"MFI",np.full(300,-1))

    def test_cci_uses_close_and_mean_absolute_deviation(self):
        c=np.arange(1,61,dtype=float)
        frame=dict(c=c,h=c+1000,l=c-1000)
        expected=(60-42)/(.015*np.mean(abs(np.arange(24,61)-42)))
        self.assertAlmostEqual(oscillator(frame,"CCI")[-1],expected)

    def test_stochastic_uses_slowed_ratio_then_signal_line(self):
        c=np.arange(1,101,dtype=float)
        frame=dict(c=c,h=c+1,l=c-1)
        # Every complete K47 window has numerator47/range48; slowing and D stay constant.
        self.assertAlmostEqual(oscillator(frame,"Stoch")[-1],100*47/48)

    def test_harami_uses_high_low_midpoint_instead_of_body_midpoint(self):
        frame=dict(o=np.full(30,100.),c=np.full(30,100.),
                   h=np.full(30,101.),l=np.full(30,99.))
        frame["o"][-2:]=[100,108];frame["c"][-2:]=[110,102]
        frame["h"][-2:]=[120,110];frame["l"][-2:]=[100,101]
        self.assertEqual(pattern(frame,"Harami")[-1],-1)
