import unittest
import numpy as np
from quant_core.market_data_store import BAR
from quant_core.corpus_batch_execution import normalize_trades,default_exits


class CorpusExecutionTests(unittest.TestCase):
    def bars(self):
        values=np.zeros(2,dtype=BAR)
        values["t"]=[0,60000]
        for prefix,spread in (("b",0),("a",10)):
            for field,price in (("o",100000),("h",100200),("l",99800),("c",100000)):
                values[prefix+field]=price+spread
        return values

    def execute(self,order):
        bars=self.bars()
        return normalize_trades(bars,dict(t=np.array([0,3600000])),np.zeros(2),
            np.array([50.,50.]),"RSI",np.array([0]),np.array([1]),np.array([100]),
            np.array([60000]),"EURUSD|F6:test|SOURCE|P0",order,"EURUSD")[0]

    def test_same_minute_stop_target_order_is_preserved(self):
        lowfirst=self.execute("OLHC")
        highfirst=self.execute("OHLC")
        self.assertEqual(lowfirst["reason"],"SL")
        self.assertEqual(highfirst["reason"],"TP")
        self.assertTrue(lowfirst["same_minute_SL_TP_ambiguous"])
        self.assertLess(lowfirst["exit_msc"],20000)
        self.assertLess(highfirst["exit_msc"],20000)

    def test_source_oscillator_exit_is_disabled_when_entry_signal_exists(self):
        f=dict(t=np.arange(3))
        buy,sell=default_exits(f,np.array([75.,65.,25.]),np.array([0,1,0]),"RSI")
        self.assertEqual(buy.tolist(),[False,False,True])
        self.assertFalse(sell.any())
