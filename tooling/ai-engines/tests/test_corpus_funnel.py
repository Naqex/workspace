import unittest
from quant_core.corpus_funnel import classify, arguments
from quant_core.corpus_signals import engulfing_rsi, wilder_rsi
import numpy as np

CODE = """input uint InpSL=200;
void OnTick() {
    ExtTrade.Buy(.1, Symbol(), Ask(), NormalizeDouble(Ask()-InpSL*point,digits), 0);
}"""


class CorpusFunnelTests(unittest.TestCase):
    def profile(self):
        return dict(format=".mq5",indicators=["iRSI"],findings=[])

    def test_candidate_is_scoped_to_defaults_and_never_certifies_safety(self):
        row=classify(self.profile(),CODE,"BullishBearish Engulfing RSI.mq5")
        self.assertEqual(row["status"],"CLEAN_STRUCTURAL_CANDIDATE")
        self.assertEqual(row["default_SL_points"],200)
        self.assertFalse(row["safety_proven"])
        self.assertTrue(row["causal_translation_review_required"])

    def test_no_flags_or_zero_sl_default_is_insufficient(self):
        for code in ("void OnTick() {}",CODE.replace("InpSL=200","InpSL=0")):
            self.assertNotEqual(classify(self.profile(),code)["status"],"CLEAN_STRUCTURAL_CANDIDATE")

    def test_default_trade_without_sl_is_flagged_even_when_legacy_parser_missed_it(self):
        row=classify(self.profile(),CODE.replace("NormalizeDouble(Ask()-InpSL*point,digits)","0"))
        self.assertIn("NO_STOP_LOSS",row["flags"])

    def test_binary_and_orphan_signal_block_cannot_enter_clean_bucket(self):
        binary=dict(format=".ex5",logic_recovery="UNAVAILABLE_FROM_STRINGS",findings=[])
        self.assertEqual(classify(binary)["status"],"BINARY_LOGIC_UNKNOWN")
        bad=CODE+"\nif(ok) return(true); { ExtPatternDetected=true; }"
        row=classify(self.profile(),bad)
        self.assertIn("ORPHAN_SIGNAL_BLOCK_REVIEW",row["flags"])
        self.assertNotEqual(row["status"],"CLEAN_STRUCTURAL_CANDIDATE")

    def test_balanced_arguments_keep_nested_prices_and_quoted_commas(self):
        values=arguments(CODE+r' ExtTrade.Buy(.1,"x,y",0,MathMax(1,2),0);',r"\.\s*Buy")
        self.assertEqual(len(values),2)
        self.assertEqual(len(values[0]),5)
        self.assertEqual(values[1][1],'"x,y"')
        self.assertEqual(values[1][3],"MathMax(1,2)")

    def test_rsi_monotone_flat_and_future_causality(self):
        self.assertEqual(wilder_rsi(np.arange(100),37)[-1],100)
        self.assertEqual(wilder_rsi(-np.arange(100),37)[-1],0)
        self.assertEqual(wilder_rsi(np.ones(100),37)[-1],50)
        source=np.arange(100,dtype=float)
        np.testing.assert_equal(wilder_rsi(source,37),wilder_rsi(np.r_[source,[0,200,0]],37)[:100])

    def test_reviewed_engulfing_rule_is_symmetric_on_closed_bars(self):
        close=np.linspace(100,40,100)
        close[-6:]=[65,60,55,50,40,45]
        op=close+1
        op[-2:]=[43,39]
        frame=dict(o=op,c=close)
        self.assertEqual(engulfing_rsi(frame)[-1],1)
        self.assertEqual(engulfing_rsi(dict(o=200-op,c=200-close))[-1],-1)
        extended=dict(o=np.r_[op,[200,1]],c=np.r_[close,[1,200]])
        np.testing.assert_equal(engulfing_rsi(frame),engulfing_rsi(extended)[:100])
