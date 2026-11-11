from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import us500_frequency_audit as a
from test_us500_multiframe import event


def run(events,probe,pairs=None):
    if pairs is None:
        pairs={t:True for e in events for t in (e['t'],e['t']+60000)}
    return a.audit(dict(snapshots={e['t']:e for e in events}),pairs,a.PROBES[probe])


class FrequencyTests(unittest.TestCase):
    def test_five_fixed_probes_no_grid(self):
        self.assertEqual([p['id'] for p in a.PROBES],[f'FP0{i}' for i in range(5)])

    def test_buy_sell_and_parent_parity(self):
        for side in ('BUY','SELL'):
            events=[event(30,100,side=side),event(45,102 if side=='BUY' else 98,side=side)]
            result=run(events,0)
            self.assertEqual(result['counts']['confirm'],1)
            self.assertEqual(a.trace(result),a.parent_trace(dict(snapshots={e['t']:e for e in events}),dict(lane='A',fast=20,slow=80,k='0.1')))

    def test_touch_includes_but_does_not_require_closed_cross(self):
        for side,arm_close,confirm in (('BUY',101,102),('SELL',99,98)):
            es=[event(30,arm_close,side=side),event(45,confirm,side=side)]
            self.assertEqual(run(es,1)['counts'].get('arm',0),0)
            self.assertEqual(run(es,3)['counts']['confirm'],1)

    def test_own_warmup_removes_unused_h1_not_slow_ma_requirement(self):
        es=[event(30,100),event(45,102)]
        for e in es:e['ready']=False
        self.assertEqual(run(es,0)['counts'].get('arm',0),0)
        self.assertEqual(run(es,1)['counts']['confirm'],1)
        es[0]['m15']['previous']['means'].pop(80)
        self.assertEqual(run(es,1)['counts'].get('arm',0),0)

    def test_late_clock_and_final_expiry_confirmation(self):
        es=[event(270,100),event(330,102)]
        self.assertEqual(run(es,1)['counts'].get('arm',0),0)
        self.assertEqual(run(es,2)['counts']['confirm'],1)
        es[-1]=event(345,102)
        self.assertEqual(run(es,2)['counts'].get('confirm',0),0)
        self.assertEqual(run(es,2)['counts']['expire'],1)

    def test_equality_and_no_same_bar_confirmation(self):
        es=[event(30,100),event(45,'101.1'),event(90,100)]
        r=run(es,0)
        self.assertEqual(r['counts'].get('confirm',0),0)
        self.assertEqual(r['counts']['expire'],1)

    def test_gap_and_short_sessions_never_inflate_signals(self):
        for key in ('blocked','full_session'):
            es=[event(30,100),event(45,102)]
            for e in es:e[key]=key=='blocked'
            self.assertEqual(run(es,4)['counts'].get('arm',0),0)

    def test_gap_cancels_and_one_attempt_even_after_expiry(self):
        es=[event(30,100),event(35,100,m15=False),event(45,100),event(90,102),event(105,102)]
        es[1]['blocked']=True
        r=run(es,4)
        self.assertEqual(r['counts']['arm'],1)
        self.assertEqual(r['counts']['cancel_gap'],1)
        self.assertEqual(r['counts'].get('confirm',0),0)

    def test_missing_exact_open_or_intervening_minute_is_separate(self):
        es=[event(30,100),event(45,102),event(50,102,m15=False)]
        for minute in (es[1]['t'],es[1]['t']+60000):
            pairs={es[1]['t']:True,es[1]['t']+60000:True}
            del pairs[minute]
            r=run(es,0,pairs)
            self.assertEqual(r['counts']['confirm'],1)
            self.assertEqual(r['counts']['exact_fill_unavailable'],1)

    def test_future_change_cannot_remove_earlier_confirm(self):
        es=[event(30,100),event(45,102),event(60,100)]
        original=run(es,0)
        es[-1]['blocked']=True
        es[-1]['m15']['close']=1
        changed=run(es,0)
        self.assertEqual(a.trace(original),a.trace(changed))


if __name__=='__main__':
    unittest.main()
