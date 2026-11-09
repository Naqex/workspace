from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from index_preclose_reversion import plans_for


def fixture():
    sessions={};pairs={};start=datetime(2022,1,3,14,30,tzinfo=timezone.utc)
    for day in range(16):
        first=int((start+timedelta(days=day)).timestamp()*1000)
        stamps=list(range(first,first+390*60000,60000));sessions[(start+timedelta(days=day)).date().isoformat()]=stamps
        for t in stamps:
            price=100-day;b=dict(timestamp=t,open=price,high=price+1,low=price-.1,close=price,volume=1)
            pairs[t]=(b,{**b,**{k:b[k]+.2 for k in ['open','high','low','close']}})
    return sessions,pairs


class PrecloseTests(unittest.TestCase):
    def test_signal_cutoff_and_stop_distance_have_known_values(self):
        sessions,pairs=fixture();stamps=list(sessions.values())[-1];plan=plans_for(sessions,pairs)[stamps[-2]]
        self.assertEqual(plan['side'],'BUY');self.assertEqual(str(plan['distance']),'1.65')

    def test_last_two_minutes_cannot_change_earlier_signal(self):
        sessions,pairs=fixture();stamps=list(sessions.values())[-1]
        old=plans_for(sessions,pairs)[stamps[-2]];changed=deepcopy(pairs)
        for t in stamps[-2:]:
            for row in changed[t]:
                for k in ['open','high','low','close']:row[k]*=10
        self.assertEqual(old,plans_for(sessions,changed)[stamps[-2]])

    def test_halfday_cutoff_and_missing_prefix_safety_exit(self):
        sessions,pairs=fixture();key=list(sessions)[-1];sessions[key]=sessions[key][:210]
        stamps=sessions[key];self.assertEqual(plans_for(sessions,pairs)[stamps[-2]]['side'],'BUY')
        del pairs[stamps[10]]
        self.assertEqual(plans_for(sessions,pairs)[stamps[-2]]['side'],'EXIT')


if __name__=='__main__':unittest.main()
