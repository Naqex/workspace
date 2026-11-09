from copy import deepcopy
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from index_close_momentum import plans_for


def fixture():
    sessions={};pairs={};start=datetime(2022,1,3,14,30,tzinfo=timezone.utc)
    for day in range(16):
        at=int((start+timedelta(days=day)).timestamp()*1000);stamps=list(range(at,at+390*60000,60000))
        sessions[(start+timedelta(days=day)).date().isoformat()]=stamps
        for slot,t in enumerate(stamps):
            price=101 if day==15 and slot==29 else 102 if day==15 and slot==0 else 100
            b=dict(timestamp=t,open=price,high=price+1,low=price-1,close=price,volume=1)
            pairs[t]=(b,{**b,**{k:b[k]+.2 for k in ['open','high','low','close']}})
    return sessions,pairs


class CloseMomentumTests(unittest.TestCase):
    def test_first_return_includes_overnight_and_registered_exit_times(self):
        sessions,pairs=fixture();stamps=list(sessions.values())[-1];plans=plans_for(sessions,pairs)
        # Prior close100 -> firsthalf101 means BUY, despite open102 ->101 falling.
        self.assertEqual(plans[stamps[-30]]['side'],'BUY')
        self.assertEqual(plans[stamps[-30]]['distance'],D('.5'))
        self.assertEqual(plans[stamps[-2]]['side'],'EXIT')
        self.assertEqual(plans[stamps[0]]['side'],'EXIT')

    def test_future_cash_gap_cannot_remove_earlier_entry_signal(self):
        sessions,pairs=fixture();stamps=list(sessions.values())[-1]
        before=plans_for(sessions,pairs);changed=deepcopy(pairs);del changed[stamps[-1]]
        self.assertEqual(before[stamps[-30]],plans_for(sessions,changed)[stamps[-30]])

    def test_half_day_and_missing_first_half_endpoint_cannot_enter(self):
        sessions,pairs=fixture();day=list(sessions)[-1];stamps=sessions[day]
        del pairs[stamps[29]]
        self.assertNotIn(stamps[-30],plans_for(sessions,pairs))
        sessions[day]=stamps[:210]
        self.assertNotIn(stamps[180],plans_for(sessions,pairs))


if __name__=='__main__':unittest.main()
