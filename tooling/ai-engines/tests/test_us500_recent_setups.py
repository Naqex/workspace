from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import us500_recent_setups as s
import us500_multiframe as native
import review_us500_multiframe as review
from test_us500_multiframe import event


def bar(slot,close,day='2022-01-04',opening=100):
    e=event(slot,close,day=day)
    e['m15'].update(open=D(opening),high=max(D(101),D(close),D(opening)),low=min(D(99),D(close),D(opening)))
    return e


def prepare(es):return dict(snapshots={e['t']:e for e in es})
def prior():return [bar(i,100,'2022-01-03') for i in range(15,391,15)]


class RecentSetupsTests(unittest.TestCase):
    def test_channel_retest_and_prior_range_closed_bar_clocks(self):
        es=prior()+[bar(15,100),bar(30,102),bar(45,102)]
        es[-1]['m15']['low']=D(101)
        out=s.signals(prepare(es))
        self.assertEqual(out['RS01'][-1]['t'],es[-2]['t'])
        self.assertEqual(out['RS02'][-1]['t'],es[-1]['t'])
        self.assertEqual(out['RS03'][-1]['t'],es[-2]['t'])
        self.assertEqual(len(out['RS01']),1)

    def test_orb_break_then_failure_needs_later_bar(self):
        es=[bar(15,100),bar(30,102),bar(45,100)]
        out=s.signals(prepare(es))
        self.assertEqual(out['RS04'][0]['side'],'BUY')
        self.assertEqual(out['RS05'][0]['side'],'SELL')
        self.assertGreater(out['RS05'][0]['t'],out['RS04'][0]['t'])

    def test_gap_fade_requires_complete_prior_day_and_opposite_move(self):
        es=prior()+[bar(15,101,opening=102)]
        self.assertEqual(s.signals(prepare(es))['RS08'][0]['side'],'SELL')
        es[0]['blocked']=True
        self.assertEqual(s.signals(prepare(es))['RS08'],[])
        es[0]['blocked']=False;es[-1]['m15']['close']=D(103)
        self.assertEqual(s.signals(prepare(es))['RS08'],[])

    def test_band_reentry_uses_prior_distribution(self):
        es=[bar(i,99 if i%30 else 101,'2022-01-03') for i in range(15,391,15)]
        es += [bar(15,97),bar(30,99)]
        out=s.signals(prepare(es))
        self.assertEqual(out['RS07'][0]['t'],es[-1]['t'])
        self.assertEqual(out['RS07'][0]['side'],'BUY')

    def test_future_edit_never_changes_prior_trigger_prefix(self):
        es=prior()+[bar(15,100),bar(30,102),bar(45,100)]
        before=s.signals(prepare(es));changed=deepcopy(es)
        changed[-1]['m15']['close']=D(999);changed[-1]['blocked']=True
        after=s.signals(prepare(changed))
        for code in s.CODES:
            self.assertEqual([e for e in before[code] if e['t']<es[-1]['t']],
                             [e for e in after[code] if e['t']<es[-1]['t']])

    def test_short_or_blocked_day_cannot_emit(self):
        for key,value in (('blocked',True),('full_session',False)):
            es=prior()+[bar(15,100),bar(30,102),bar(45,100)]
            for e in es[-3:]:e[key]=value
            out=s.signals(prepare(es))
            cutoff=es[-3]['t']
            for code in s.CODES:self.assertFalse([x for x in out[code] if x['t']>=cutoff])

    def test_native_common_stop_exit_and_null_cash_reconcile(self):
        for side in ('BUY','SELL'):
            es=[bar(30,100),bar(45,100),bar(360,100)]
            start=es[0]['t']-30*native.M
            pairs={t:tuple(dict(timestamp=t,open=100+d,high=100+d,low=100+d,close=100+d,volume=1)
                         for d in (0,.2)) for t in range(start,start+365*native.M,native.M)}
            p=prepare(es);p.update(missing=set(),total_sessions=1)
            sig=dict(kind='confirm',t=es[0]['t'],side=side,atr=D(1))
            factory=lambda config:s.FrozenPolicy(config,{sig['t']:sig})
            for null in (False,True):
                result=native.execute(dict(id='RS01'),p,pairs,native.quote_data(pairs),'.25',null=null,policy_factory=factory)
                review.inspect(result,pairs)
                self.assertIsNone(result['position'])
                self.assertEqual(len(result['trades']),0 if null else 1)
                self.assertEqual(result['decimal_cash'],D(10000)+sum((t['cash_net'] for t in result['trades']),D(0)))


if __name__=='__main__':unittest.main()
