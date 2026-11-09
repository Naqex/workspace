from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gold_ml_sl_labels as study
H=3600000


def fixture():
    begin=int(datetime(2018,12,26,tzinfo=timezone.utc).timestamp()*1000)
    end=int(datetime(2019,1,4,tzinfo=timezone.utc).timestamp()*1000)
    pairs={}
    for t in range(begin,end,H):
        pairs[t]=tuple(dict(timestamp=t,open=float(D(1000)+o),high=float(D('1000.1')+o),
                            low=float(D('999.9')+o),close=float(D(1000)+o),volume=0) for o in (D(0),D('.2')))
    at=int(datetime(2019,1,2,8,tzinfo=timezone.utc).timestamp()*1000)
    op=dict(id='2019-01-02-08',day='2019-01-02',decision_msc=at,entry_msc=at+H,exit_msc=at+4*H,
            status='feature_ready',x=[0.]*21,distance=D(2))
    for row,o in zip(pairs[op['exit_msc']],(D(0),D('.2'))):
        row.update(open=float(1003+o),high=float(1004+o),low=float(1003+o),close=float(1003+o))
    return pairs,op


def pack(at):
    return dict(schema='gold-stop-aligned-forest-pack-v1',candidate=study.CANDIDATES[0],available_from_msc=at,
                feature_names=list(study.FEATURE_NAMES),model={'kind':'forest','trees':[[[-2,-2,-1,-1,[.2,0.]]]]})


class GoldMLLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):study.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_manual_costed_stop_path_labels_and_replay_same_trade(self):
        pairs,op=fixture();t=study.trade_path(op,'BUY',pairs)
        self.assertEqual(t['quantity'],D('.11'));self.assertEqual(t['stop'],D('998.2'))
        self.assertEqual(t['planned_stop_risk_usd'],D('24.75'))
        self.assertEqual(t['net_usd'],D('28.05'))
        self.assertEqual(t['endpoint_msc'],op['exit_msc']+H)
        labels=study.training_labels([op],pairs)
        self.assertTrue(labels[0]['usable'])
        self.assertEqual(labels[0]['y'],[float(D('28.05')/25),float(D('-37.95')/25)])
        r=study.simulate([op],pairs,pack(op['decision_msc']),scenario='reference')
        self.assertEqual(r['trades'][0],labels[0]['sides']['BUY'])
        self.assertEqual(r['net_equity_usd'],D('28.05'));self.assertFalse(r['execution_authorized'])

    def test_short_protection_uses_Ask_and_gap_precedes_scheduled_exit(self):
        pairs,op=fixture();at=op['entry_msc']+H
        pairs[at][0]['high']=1001.9;pairs[at][1]['high']=1002.1
        t=study.trade_path(op,'SELL',pairs)
        self.assertEqual((t['exit_quote'],t['reason'],t['net_usd']),(D(1002),'stop_loss',D('-24.75')))
        pairs,op=fixture()
        for row,o in zip(pairs[op['exit_msc']],(D(0),D('.2'))):
            row.update(open=float(990+o),high=float(991+o),low=float(989+o),close=float(990+o))
        t=study.trade_path(op,'BUY',pairs)
        self.assertEqual((t['exit_quote'],t['reason']),(D(990),'stop_loss_gap'))
        self.assertLess(t['net_usd'],-25)

    def test_unknown_is_not_zero_label_and_blocks_future_entries(self):
        pairs,op=fixture();del pairs[op['entry_msc']+H]
        label=study.training_labels([op],pairs)[0]
        self.assertFalse(label['usable']);self.assertIsNone(label['y'])
        later=deepcopy(op)
        for k in ('decision_msc','entry_msc','exit_msc'):later[k]+=4*H
        later['id']='later'
        r=study.simulate([op,later],pairs,pack(op['decision_msc']),scenario='reference')
        self.assertIsNone(r['net_equity_usd']);self.assertEqual(r['entries'],1)
        self.assertEqual(r['decisions'][1]['status'],'blocked_unknown_exposure')
        n=study.simulate([op,later],pairs,pack(op['decision_msc']),scenario='reference',null_control=True)
        self.assertEqual((n['entries'],n['net_equity_usd']),(0,0))

    def test_missing_future_entry_does_not_change_past_features_or_signal(self):
        pairs,op=fixture();before=study.opportunities(pairs,2019)
        selected=next(r for r in before if r['id']==op['id'])
        self.assertIsNotNone(selected['x'])
        past_signal=study.predicted_side(pack(op['decision_msc']),selected)
        del pairs[op['entry_msc']]
        after=study.opportunities(pairs,2019);other=next(r for r in after if r['id']==op['id'])
        self.assertEqual(selected,other)
        self.assertEqual(past_signal,study.predicted_side(pack(op['decision_msc']),other))
        self.assertEqual(study.trade_path(other,'BUY',pairs)['status'],'missing_or_crossed_entry')

    def test_purge_uses_actual_endpoint_and_model_availability(self):
        pairs,op=fixture();labels=study.training_labels([op],pairs);cutoff=labels[0]['endpoint_msc']
        self.assertEqual(study.purged_training(labels,start=0,cutoff=cutoff),[])
        self.assertEqual(len(study.purged_training(labels,start=0,cutoff=cutoff+1)),1)
        self.assertEqual(study.predicted_side(pack(op['decision_msc']+H),op),(None,None))
        bad=pack(0);bad['feature_names']=[]
        with self.assertRaisesRegex(ValueError,'identity'):study.predicted_side(bad,op)

    def test_source_order_grid_scope_and_side_presence(self):
        pairs,op=fixture();lo=min(pairs);hi=max(pairs)+H
        bid=[p[0] for p in pairs.values()];ask=[p[1] for p in pairs.values()]
        self.assertEqual(study.paired_inputs(bid,ask,start=lo,end=hi),pairs)
        with self.assertRaises(ValueError):study.paired_inputs(list(reversed(bid)),ask,start=lo,end=hi)
        with self.assertRaises(ValueError):study.paired_inputs(bid,ask,start=lo,end=1735693200000)
        partial=study.paired_inputs(bid,ask[1:],start=lo,end=hi)
        self.assertIsNone(partial[lo][1]);self.assertFalse(study.valid_pair(partial[lo]))
        with self.assertRaisesRegex(ValueError,'unregistered'):study.opportunities(pairs,2025)

    def test_actual_balance_gate_and_stop_tick_rounding(self):
        pairs,op=fixture()
        self.assertEqual(study.trade_path(op,'BUY',pairs,balance=D(1))['status'],'quantity_or_margin_rejected')
        op['distance']=D('2.0004');t=study.trade_path(op,'BUY',pairs)
        self.assertEqual(t['stop'],D('998.199'));self.assertLessEqual(t['planned_stop_risk_usd'],25)

    def test_schedule_excludes_holidays_and_halfdays(self):
        pairs,_=fixture();ops=study.opportunities(pairs,2019)
        self.assertFalse(any(r['day']=='2019-01-01' or r['day']=='2019-11-29' for r in ops))
        same=[r for r in ops if r['day']=='2019-01-02']
        self.assertEqual(len(same),3)
        self.assertEqual([datetime.fromtimestamp(r['entry_msc']/1000,timezone.utc).hour for r in same],[9,13,17])
        self.assertTrue(all(a['exit_msc']+H<=b['entry_msc'] for a,b in zip(same,same[1:])))


if __name__=='__main__':unittest.main()
