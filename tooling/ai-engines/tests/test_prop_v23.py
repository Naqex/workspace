from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from copy import deepcopy
import json
import tempfile
import unittest
import ftmo_trial_runner as runner
from quant_core.sleeve_ablation import weakest_sleeve,admitted,filter_blocks


class Clock:
    def __init__(self):self.now=0.
    def __call__(self):return self.now
    def sleep(self,t):self.now+=t


def ready(**kw):
    r=dict(read_only_ready=True,status='READ_ONLY_PROBE_OK',binding=dict(server='FTMO',account_hash='fixture'),
        terminal_path='C:/fixture/terminal64.exe',terminals_seen=1,reason='SHADOW_PARITY_STILL_REQUIRED')
    r.update(kw);return r


class V23Tests(unittest.TestCase):
    def test_weakest_uses_dev_mean_not_global_top10_or_trade_count(self):
        rows=[dict(id='A',year=2022,net_R=-.1),dict(id='B',year=2023,net_R=-.2),dict(id='A',year=2022,net_R=-.1)]
        self.assertEqual(weakest_sleeve(rows),'B')
        with self.assertRaises(ValueError):weakest_sleeve([dict(id='A',year=2024,net_R=-1)])

    def test_A1_drops_exact_sleeve_without_rescaling_other_trades(self):
        p=dict(name='A1_DROP_WEAKEST',drop_id='XAUUSD|F3:test')
        self.assertFalse(admitted(dict(id=p['drop_id']),None,p))
        self.assertTrue(admitted(dict(id='EURUSD|F5:test'),None,p))

    def test_mechanism_specific_gate_never_filters_F5(self):
        for name in ('A2_F3_EXHAUSTION90','A2_F4_EXHAUSTION90'):
            self.assertTrue(admitted(dict(id='EURUSD|F5:test'),100,dict(name=name)))
        self.assertTrue(admitted(dict(id='XAUUSD|F4:test'),100,dict(name='A2_F3_EXHAUSTION90')))
        self.assertFalse(admitted(dict(id='XAUUSD|F3:test'),1,dict(name='A2_F3_EXHAUSTION90')))

    def test_filtered_tape_remaps_only_entry_exit_preserves_quotes_clocks_and_input(self):
        a=dict(id='A',entry_msc=0);b=dict(id='B',entry_msc=1)
        segment=dict(kind='segment',lo=1,hi=10)
        block=dict(trades=[a,b],operations=[segment,dict(kind='action',at=1,precheck=True,quote={'b':100},
            actions=[['reset',None],['entry',0],['exit',0],['entry',1],['session_flat',None]])])
        original=deepcopy(block);out=filter_blocks([block],{'A@0':False,'B@1':True})[0]
        self.assertEqual(out['trades'],[b]);self.assertIs(out['operations'][0],segment)
        self.assertEqual(out['operations'][1]['actions'],[['reset',None],['entry',0],['session_flat',None]])
        self.assertEqual(block,original)

    def test_missing_tape_decision_is_not_treated_as_reject_or_accept(self):
        with self.assertRaisesRegex(ValueError,'Missing'):filter_blocks([dict(trades=[dict(id='A',entry_msc=0)],operations=[])],{})

    def test_H1_price_availability_is_separate_from_Gold_holiday_admission(self):
        from prop_v23_f5 import FXResearchCalendar
        from prop_campaign_source import stamp
        c=FXResearchCalendar();at=stamp('2023-04-07T09:00:00')
        self.assertTrue(c.allowed(at));self.assertEqual(c.cutoff(at,'GBPUSD'),stamp('2023-04-07T20:00:00'))
        self.assertFalse(c.allowed(stamp('2023-12-25T09:00:00')))

    def test_watch_timeout_is_bounded_and_does_not_capture(self):
        clock=Clock();calls=[]
        with tempfile.TemporaryDirectory() as d:
            r=runner.watch_mt5(Path(d)/'watch',timeout=2,poll_seconds=1,clock=clock,sleeper=clock.sleep,
                probe=lambda **kw:ready(read_only_ready=False,terminals_seen=0,reason='NO_RUNNING_TERMINAL'),capture=lambda *a,**kw:calls.append(kw))
            self.assertEqual(r['status'],'TIMEOUT_NO_READY_TARGET');self.assertEqual(r['attempts'],2)
            self.assertEqual(calls,[]);self.assertTrue((Path(d)/'watch/WATCH_REPORT.json').is_file())

    def test_watch_detects_later_target_and_requires_native_binding(self):
        clock=Clock();probes=iter([ready(read_only_ready=False),ready()]);calls=[]
        def capture(mode,out,**kw):
            calls.append((mode,kw));out.mkdir()
            (out/'report.json').write_text(json.dumps(dict(source='NATIVE_MT5',native_terminal_verified=True)))
        with tempfile.TemporaryDirectory() as d:
            r=runner.watch_mt5(Path(d)/'watch',timeout=3,poll_seconds=1,clock=clock,sleeper=clock.sleep,
                probe=lambda **kw:next(probes),capture=capture)
            self.assertTrue(r['native_capture_completed']);self.assertEqual(r['attempts'],2)
            self.assertEqual(calls[0][0],'read-only');self.assertTrue(calls[0][1]['require_native'])
            self.assertEqual(calls[0][1]['expected_binding'],ready()['binding'])

    def test_watch_disappearing_terminal_cannot_silently_replay(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'terminal_inventory',return_value=[]):
            r=runner.watch_mt5(Path(d)/'watch',timeout=1,probe=lambda **kw:ready())
            self.assertEqual(r['status'],'CAPTURE_OR_PROBE_FAILED');self.assertFalse(r['native_capture_completed'])
            self.assertIn('NO_REPLAY_FALLBACK',r['reason'])

    def test_watch_rejects_replay_result_even_if_callback_claims_completion(self):
        def capture(mode,out,**kw):
            out.mkdir();(out/'report.json').write_text(json.dumps(dict(source='TIMESTAMP_PACED_REPLAY',native_terminal_verified=False)))
        with tempfile.TemporaryDirectory() as d:
            r=runner.watch_mt5(Path(d)/'watch',timeout=1,probe=lambda **kw:ready(),capture=capture)
            self.assertFalse(r['native_capture_completed']);self.assertIn('MUST_BE_NATIVE',r['reason'])

    def test_watch_missing_binding_does_not_capture(self):
        with tempfile.TemporaryDirectory() as d:
            r=runner.watch_mt5(Path(d)/'watch',timeout=1,probe=lambda **kw:ready(binding=None))
            self.assertEqual(r['status'],'CAPTURE_OR_PROBE_FAILED');self.assertIn('BINDING_UNKNOWN',r['reason'])

    def test_watch_interrupt_preserves_report_without_claiming_flat(self):
        def probe(**kw):raise KeyboardInterrupt()
        with tempfile.TemporaryDirectory() as d:
            r=runner.watch_mt5(Path(d)/'watch',timeout=1,probe=probe)
            self.assertEqual(r['status'],'INTERRUPTED');self.assertTrue(r['resume_requires_reconciliation'])

    def test_watch_does_not_start_capture_after_wait_deadline(self):
        clock=Clock()
        def probe(**kw):clock.now=2;return ready()
        with tempfile.TemporaryDirectory() as d:
            r=runner.watch_mt5(Path(d)/'watch',timeout=1,clock=clock,probe=probe)
            self.assertEqual(r['status'],'TIMEOUT_NO_READY_TARGET');self.assertFalse(r['native_capture_completed'])

    def test_watch_invalid_budget_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'watch'
            for kw in (dict(timeout=0),dict(timeout=3601),dict(poll_seconds=0),dict(capture_seconds=0)):
                with self.assertRaises(ValueError):runner.watch_mt5(out,**kw)
                self.assertFalse(out.exists())

    def test_native_capture_rejects_account_drift_after_probe(self):
        bundle,_=runner.builtin_fixture()
        class Reader:
            def account(self):return bundle['account']
            def spec(self,asset):return bundle['specs'][asset]
            def close(self):pass
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'terminal_inventory',return_value=[dict(ExecutablePath='fixture')]),patch.object(runner.adapter,'NativeMT5Reader',return_value=Reader()):
            with self.assertRaisesRegex(runner.adapter.AdapterError,'ACCOUNT_CHANGED'):
                runner.run('read-only',Path(d)/'capture',seconds=1,require_native=True,expected_binding={'server':'other','account_hash':'other'})
