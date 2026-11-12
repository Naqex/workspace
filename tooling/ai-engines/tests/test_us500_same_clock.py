from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import us500_same_clock as s


def fixture(sign=1, count=23):
    sessions, pairs = {}, {}
    for i in range(count):
        start=(i+1)*86400000
        sessions[f'day-{i:02}']=[start+j*s.M for j in range(390)]
        for slot, value in [(29,100),(30,100),(31,100),(61,100+sign)]:
            pairs[start+slot*s.M]=({'open':str(value)},{'open':str(value+F(1,2))})
    return sessions,pairs


class SameClockTests(unittest.TestCase):
    def test_both_sides_and_warmup(self):
        for sign,side in [(1,'BUY'),(-1,'SELL')]:
            sessions,pairs=fixture(sign)
            out=s.signals(sessions,pairs)
            self.assertEqual(out['reasons']['warmup'],20)
            self.assertEqual([e['side'] for e in out['events']],[side]*3)

    def test_zero_stands_aside(self):
        self.assertEqual(s.signals(*fixture(0))['reasons']['zero_score'],3)

    def test_history_gap_not_last_twenty_valid(self):
        sessions,pairs=fixture(count=42)
        del pairs[next(iter(sessions.values()))[31]]
        out=s.signals(sessions,pairs)
        self.assertEqual(out['days'][20]['reason'],'history_endpoint_missing')
        self.assertEqual(out['days'][21]['reason'],'BUY')

    def test_current_future_target_cannot_change_signal(self):
        sessions,pairs=fixture()
        original=s.signals(sessions,pairs)['events'][0]
        mutated=deepcopy(pairs)
        for stamps in list(sessions.values())[20:]:
            mutated[stamps[61]]=({'open':'1'},{'open':'2'})
        self.assertEqual(s.signals(sessions,mutated)['events'][0],original)

    def test_freshness_and_missing_entry_are_separate(self):
        sessions,pairs=fixture()
        stamps=list(sessions.values())[20]
        out=s.signals(sessions,pairs)['events'][0]
        del pairs[stamps[31]]
        self.assertEqual(s.signals(sessions,pairs)['events'][0],out)
        self.assertFalse(s.endpoint(out,pairs,F('.25'))['known'])
        del pairs[stamps[29]]
        self.assertEqual(s.signals(sessions,pairs)['days'][20]['reason'],'decision_availability_missing')

    def test_halfday_not_history_and_annual_cold_start(self):
        sessions,pairs=fixture()
        sessions['day-00']=sessions['day-00'][:210]
        out=s.signals(sessions,pairs)
        self.assertEqual(out['reasons']['short_session'],1)
        self.assertEqual(len(out['events']),2)
        self.assertEqual(s.signals(dict(list(sessions.items())[-2:]),pairs)['events'],[])

    def test_long_short_cost_bridge_and_unknown_census(self):
        sessions,pairs=fixture()
        ev=s.signals(sessions,pairs)['events'][0]
        buy=s.endpoint(ev,pairs,F('.25'))
        sell=s.endpoint(dict(ev,side='SELL'),pairs,F('.75'))
        self.assertEqual(buy['gross_bidask'],F('.5'))
        self.assertEqual(buy['net'],0)
        self.assertEqual(sell['gross_bidask'],F('-1.5'))
        self.assertEqual(sell['net'],-3)
        del pairs[ev['t']+31*s.M]
        summary=s.aggregate([buy,s.endpoint(ev,pairs,0)])
        self.assertIsNone(summary['net'])
        self.assertEqual(summary['unknown'],1)

    def test_priority_cannot_be_won_by_positive_but_weaker_control(self):
        annual=[{k:dict(net=F(n)) for k,n in [('TC01',1),('BUY',2),('SELL',-3)]} for _ in range(3)]
        self.assertEqual(s.priority(annual),'park_exact_component')
        annual[0]['TC01']['net']=None
        self.assertEqual(s.priority(annual),'inconclusive_endpoint_missing')


if __name__=='__main__':
    unittest.main()
