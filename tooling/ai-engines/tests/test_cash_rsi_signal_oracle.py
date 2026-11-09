from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cash_rsi_signal_oracle import expected_decision


class CashRsiOracleTests(unittest.TestCase):
    def test_known_oversold_history_produces_independent_atr_distance(self):
        days=[dict(high=F(101-i),low=F(999-i*10,10),close=F(100-i)) for i in range(15)]
        side,distance=expected_decision(days[:-1],days[-1])
        self.assertEqual(side,'BUY')
        self.assertEqual(distance,F(33,20))

    def test_ibs_exit_does_not_require_an_available_rsi(self):
        history=[None,dict(high=F(101),low=F(99),close=F(100))]
        self.assertEqual(expected_decision(history,dict(high=F(110),low=F(100),close=F(109))),('EXIT',None))

    def test_missing_bar_exits_and_flat_range_does_not_invent_signal(self):
        self.assertEqual(expected_decision([],None),('EXIT',None))
        self.assertEqual(expected_decision([],dict(high=F(100),low=F(100),close=F(100))),(None,None))

    def test_known_rsi_exit_does_not_require_defined_ibs_on_a_flat_range(self):
        history=[dict(high=F(p),low=F(p),close=F(p)) for p in (100,101,102)]
        self.assertEqual(expected_decision(history,dict(high=F(103),low=F(103),close=F(103))),('EXIT',None))


if __name__=='__main__':unittest.main()
