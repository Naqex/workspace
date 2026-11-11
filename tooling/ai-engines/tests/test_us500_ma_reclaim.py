from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest
import json
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import us500_multiframe as core
import us500_ma_reclaim as study
from run_us500_ma_reclaim import frequency_eligible,cost_screen_registration
from sealed_m1_review import digest
from test_us500_multiframe import event


def fixture(side='BUY',stop=False,missing=None):
    start=event(0,100)['t']
    times=list(range(start,start+390*core.M,core.M))
    pairs={t:tuple(dict(timestamp=t,open=100+d,high=101+d,low=99+d,close=100+d,volume=0) for d in (0,.2)) for t in times}
    if stop:
        pairs[times[290]][0 if side=='BUY' else 1]['low' if side=='BUY' else 'high']=95 if side=='BUY' else 105
    if missing is not None:del pairs[times[missing]]
    es=[event(270,100,side=side),event(285,101 if side=='BUY' else 99,side=side),event(360,101 if side=='BUY' else 99,side=side)]
    prepared=dict(snapshots={e['t']:e for e in es},missing=set(times)-pairs.keys(),total_sessions=1)
    return pairs,prepared,times


class ReclaimPolicyTests(unittest.TestCase):
    def test_frequency_priority_floor_is_not_lowered_for_old158(self):
        self.assertFalse(frequency_eligible([dict(year=y,exact_fill_available=n) for y,n in zip((2022,2023,2024),(55,50,53))]))
        self.assertTrue(frequency_eligible([dict(year=y,exact_fill_available=n) for y,n in zip((2022,2023,2024),(100,50,50))]))
        self.assertFalse(frequency_eligible([dict(year=y,exact_fill_available=n) for y,n in zip((2022,2023,2024),(200,49,50))]))
        with self.assertRaises(ValueError):frequency_eligible([])

    def test_reclaim_does_not_need_arm_extreme_break_and_no_same_bar(self):
        for side,confirm in [('BUY','100.2'),('SELL','99.8')]:
            p=study.ReclaimPolicy(study.CONFIG)
            p.event(event(30,100,side=side))
            self.assertIsNone(p.event(event(30,102 if side=='BUY' else 98,side=side)))
            p=study.ReclaimPolicy(study.CONFIG)
            p.event(event(30,100,side=side))
            a=p.event(event(45,confirm,side=side))
            self.assertEqual(a['side'],side)
            self.assertEqual(a['confirmation'],'closed_fast_MA_reclaim')

    def test_strict_equality_and_dynamic_closed_ma_frozen_atr(self):
        p=study.ReclaimPolicy(study.CONFIG)
        p.event(event(30,100))
        self.assertIsNone(p.event(event(45,'100.1')))
        e=event(60,'99.7')
        e['m15']['means'][20]=D('99.5')
        e['m15']['atr']=D(1000)
        a=p.event(e)
        self.assertEqual(a['atr'],1)
        self.assertEqual(a['threshold'],'498/5')

    def test_no_h1_dependency_but_own_slow_ma_required(self):
        e=event(30,100)
        e['ready']=False
        e['bias']=None
        p=study.ReclaimPolicy(study.CONFIG)
        p.event(e)
        self.assertIsNotNone(p.arm)
        e['m15']['previous']['means'].pop(80)
        p=study.ReclaimPolicy(study.CONFIG)
        p.event(e)
        self.assertIsNone(p.arm)

    def test_direction_cancel_before_reclaim_and_no_rearm(self):
        p=study.ReclaimPolicy(study.CONFIG)
        p.event(event(30,100))
        e=event(45,101)
        e['m15']['means'][80]=D(100)
        self.assertIsNone(p.event(e))
        p.event(event(60,100))
        self.assertIsNone(p.arm)
        self.assertEqual(p.events[-1]['kind'],'cancel_trend')

    def test_late_window_expiry_and_short_gap_blocks(self):
        p=study.ReclaimPolicy(study.CONFIG)
        p.event(event(270,100))
        self.assertIsNotNone(p.event(event(330,101)))
        p=study.ReclaimPolicy(study.CONFIG)
        p.event(event(270,100))
        self.assertIsNone(p.event(event(345,101)))
        self.assertEqual(p.events[-1]['kind'],'expire')
        for key,value in [('blocked',True),('full_session',False)]:
            e=event(30,100)
            e[key]=value
            p=study.ReclaimPolicy(study.CONFIG)
            p.event(e)
            self.assertIsNone(p.arm)

    def test_noon_is_not_end_of_session_and_no_future_entry(self):
        p=study.ReclaimPolicy(study.CONFIG)
        self.assertIsNone(p.event(event(150,101),active='BUY'))
        self.assertEqual(p.event(event(360,101),active='BUY')['reason'],'session_flat')
        self.assertIsNone(p.event(event(360,101),active='BUY',pending=True))


class NativeReclaimTests(unittest.TestCase):
    def run_case(self,**kw):
        pairs,prepared,times=fixture(**kw)
        r=core.execute(study.CONFIG,prepared,pairs,core.quote_data(pairs),'.25',policy_factory=study.ReclaimPolicy)
        study.review(r,prepared,pairs)
        return r,pairs,prepared,times

    def test_buy_sell_late_entry_and_1531_exit_native_cash(self):
        for side in ('BUY','SELL'):
            r,_,_,times=self.run_case(side=side)
            t=r['trades'][0]
            self.assertEqual(t['entry_time'],times[286])
            self.assertEqual(t['exit_ns']//1000000,times[361])
            self.assertEqual(t['reason'],'session_flat')
            self.assertFalse(t['unresolved'])
            self.assertEqual(r['native_cash'],D('9992.22'))
            self.assertEqual(r['native_open_positions'],0)

    def test_native_stop_and_held_gap_remain_reconciled(self):
        for side in ('BUY','SELL'):
            r,_,_,_=self.run_case(side=side,stop=True)
            self.assertEqual(r['trades'][0]['reason'],'stop')
        r,_,_,_=self.run_case(missing=289)
        self.assertTrue(r['trades'][0]['unresolved'])
        r,_,_,_=self.run_case(stop=True,missing=361)
        self.assertFalse(r['trades'][0]['unresolved'])

    def test_missing_exact_flat_exit_then_recovery_stays_unknown(self):
        pairs,prepared,times=fixture(missing=361)
        e=event(375,100)
        e['m15']['means'][80]=D(100)
        prepared['snapshots'][e['t']]=e
        r=core.execute(study.CONFIG,prepared,pairs,core.quote_data(pairs),'.25',policy_factory=study.ReclaimPolicy)
        study.review(r,prepared,pairs)
        self.assertEqual(r['trades'][0]['exit_ns']//1000000,times[376])
        self.assertTrue(r['trades'][0]['unresolved'])
        self.assertEqual(r['trades'][0]['reason'],'trend_lost')

    def test_null_and_default_policy_injection_parity(self):
        pairs,prepared,_=fixture()
        r=core.execute(study.CONFIG,prepared,pairs,core.quote_data(pairs),'.25',null=True,policy_factory=study.ReclaimPolicy)
        study.review(r,prepared,pairs)
        self.assertEqual(r['fills'],[])
        config=core.configurations()[0]
        a=core.execute(config,prepared,pairs,core.quote_data(pairs),'.25')
        b=core.execute(config,prepared,pairs,core.quote_data(pairs),'.25',policy_factory=core.Policy)
        self.assertEqual(a,b)

    def test_signal_and_exit_mutations_are_rejected(self):
        r,pairs,prepared,times=self.run_case()
        changed=deepcopy(r)
        next(e for e in changed['policy_events'] if e['kind']=='confirm')['threshold']='999'
        with self.assertRaises(ValueError):study.review(changed,prepared,pairs)
        changed=deepcopy(r)
        changed['trades'][0]['exit_ns']=(times[346])*1000000+1
        changed['fills'][-1]['timestamp_ns']=changed['trades'][0]['exit_ns']
        with self.assertRaisesRegex(ValueError,'scheduled_exit_clock'):
            study.review(changed,prepared,pairs)


class CostRegistrationTests(unittest.TestCase):
    def setup_files(self,root):
        old=dict(status='completed_frequency_only_below_priority_floor',rows=[],frequency_eligible=False,
                 frequencies=[dict(exact_fill_available=n) for n in (58,50,57)])
        (root/'result.json').write_text(json.dumps(old),encoding='utf-8')
        (root/'manifest.json').write_text(json.dumps(dict(config=study.CONFIG)),encoding='utf-8')
        reg=dict(schema='us500-ma-reclaim-cost-screen-registration-v1',stage='G2_exploratory_cost_and_execution_only',
            parent_frequency_manifest_sha256=digest(root/'manifest.json'),parent_frequency_result_sha256=digest(root/'result.json'),
            config=study.CONFIG,years=[2022,2023,2024],observed_exact_signal_counts=[58,50,57],
            financial_books=6,null_books=3,deep_review_frequency_floor_unchanged=200,
            strategy_rule_change=False,edge_qualified=False,holdout_read=False)
        path=root/'registration.json'
        path.write_text(json.dumps(reg),encoding='utf-8')
        return path,reg

    def test_scoped_cost_screen_does_not_pass_deep_review_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path,reg=self.setup_files(root)
            self.assertEqual(cost_screen_registration(path,digest(path),root),reg)
            self.assertFalse(frequency_eligible([dict(year=y,exact_fill_available=n) for y,n in zip((2022,2023,2024),(58,50,57))]))

    def test_scope_expansion_and_strategy_changes_are_rejected(self):
        for key,value in [('years',[2022,2023,2025]),('edge_qualified',True),('holdout_read',True),
                          ('strategy_rule_change',True),('financial_books',27),('deep_review_frequency_floor_unchanged',100),
                          ('config',dict(study.CONFIG,k='0.05'))]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                path,reg=self.setup_files(root)
                reg[key]=value
                path.write_text(json.dumps(reg),encoding='utf-8')
                with self.assertRaises(ValueError):cost_screen_registration(path,digest(path),root)

    def test_parent_or_registration_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path,reg=self.setup_files(root)
            sha=digest(path)
            path.write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'registration_hash'):cost_screen_registration(path,sha,root)
            path.write_text(json.dumps(reg),encoding='utf-8')
            old=json.loads((root/'result.json').read_text())
            old['rows']=[dict(already_financial=True)]
            (root/'result.json').write_text(json.dumps(old))
            reg['parent_frequency_result_sha256']=digest(root/'result.json')
            path.write_text(json.dumps(reg))
            with self.assertRaises(ValueError):cost_screen_registration(path,digest(path),root)

    def test_known_frequency_cannot_be_replaced_to_choose_another_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path,reg=self.setup_files(root)
            reg['observed_exact_signal_counts']=[100,100,100]
            path.write_text(json.dumps(reg),encoding='utf-8')
            with self.assertRaises(ValueError):cost_screen_registration(path,digest(path),root)


if __name__=='__main__':
    unittest.main()
