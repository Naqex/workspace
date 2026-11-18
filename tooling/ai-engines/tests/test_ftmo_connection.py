from pathlib import Path
from unittest.mock import patch,Mock
import tempfile,unittest
import ftmo_connection as c

class ConnectionTests(unittest.TestCase):
    def values(self):return dict(zip(c.KEYS,('123','fixture-password','FTMO-Demo','C:/fixture/terminal64.exe')))
    def test_missing_credentials_preserves_attach_only(self):self.assertIsNone(c.credentials(environ={}))
    def test_partial_credentials_do_not_login_last_saved_account(self):
        with self.assertRaisesRegex(ValueError,'COMPLETE'):c.credentials(environ={c.KEYS[0]:'123'})
    def test_env_file_is_data_no_interpolation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'env';v=self.values();v[c.KEYS[1]]='$(never-execute)';p.write_text('\n'.join(k+'='+x for k,x in v.items()))
            self.assertEqual(c.credentials(p,environ={})[c.KEYS[1]],'$(never-execute)')
    def test_unknown_env_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'env';p.write_text('PATH=not-allowed')
            with self.assertRaisesRegex(ValueError,'FOUR'):c.credentials(p,environ={})
    def test_non_ftmo_and_non_numeric_login_rejected(self):
        for key,value in ((c.KEYS[0],'abc'),(c.KEYS[2],'other')):
            v=self.values();v[key]=value
            with self.assertRaises(ValueError):c.credentials(environ=v)
    def test_exact_server_clock_uses_existing_decoder(self):
        from datetime import datetime,timezone
        t=int(datetime(2026,11,17,12,tzinfo=timezone.utc).timestamp()*1000)
        self.assertEqual(c.quote_utc_msc(t+2*3600000,'FTMO-Demo'),t)
        self.assertEqual(c.quote_utc_msc(t,'OTHER'),t)
    def test_clock_does_not_guess_old_FTMO_regime(self):
        with self.assertRaises(RuntimeError):c.quote_utc_msc(1672531200000,'FTMO-Demo')
    def test_clock_reader_queries_envelope_and_filters_normalized_UTC(self):
        r=Mock();t=1794916800000
        r.copy_ticks_range.return_value=[dict(time_msc=t+7200000,bid=1,ask=2,flags=0),dict(time_msc=t+7202000,bid=1,ask=2,flags=0)]
        from datetime import datetime,timezone
        rows=c.ClockSDK(r,'FTMO-Demo').copy_ticks_range('EURUSD',datetime.fromtimestamp(t/1000,timezone.utc),datetime.fromtimestamp((t+1000)/1000,timezone.utc),0)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['time_msc'],t);self.assertEqual(int(r.copy_ticks_range.call_args.args[1].timestamp()*1000),t+7200000)
    def test_running_owned_terminal_is_never_cleaned_or_rotated(self):
        import uuid
        v=self.values();folder=c.ROOT/'.runtime/ftmo-trial-readonly-v24'/str(uuid.uuid5(uuid.NAMESPACE_URL,'123|FTMO-Demo'))
        product=Mock()
        with self.assertRaisesRegex(ValueError,'ALREADY_RUNNING'):
            with c.trial_session(v,product=product,inventory=[dict(ExecutablePath=str(folder/'terminal64.exe'))]):pass
        product.prepare_terminal.assert_not_called()
    def test_shadow_rates_and_deals_use_normalized_clock_before_checks(self):
        import numpy as np
        from collections import namedtuple
        from datetime import datetime,timezone
        sdk=Mock();sdk.copy_rates_from_pos.return_value=np.array([(1794916800+7200,1.)],dtype=[('time','i8'),('open','f8')])
        clock=c.ClockSDK(sdk,'FTMO-Demo');rows=clock.copy_rates_from_pos('EURUSD',1,0,10)
        self.assertEqual(rows[0]['time'],1794916800)
        Deal=namedtuple('Deal','time profit');sdk.history_deals_get.return_value=[Deal(1794916800+7200,5),Deal(1794916800+7200+200,8)]
        rows=clock.history_deals_get(datetime.fromtimestamp(1794916800,timezone.utc),datetime.fromtimestamp(1794916801,timezone.utc))
        self.assertEqual(rows,[Deal(1794916800,5)])
    def test_watch_does_not_accept_other_demo_after_credential_login(self):
        import ftmo_trial_runner as runner
        with tempfile.TemporaryDirectory() as d:
            result=runner.watch_mt5(Path(d)/'watch',timeout=1,expected_binding={'account_hash':'target','server':'FTMO'},
                probe=lambda **kw:dict(read_only_ready=True,binding={'account_hash':'other','server':'FTMO'},terminal_path='fixture'))
            self.assertEqual(result['reason'],'CONFIGURED_TRIAL_ACCOUNT_CHANGED');self.assertFalse(result['native_capture_completed'])
    def test_isolated_session_owns_tree_and_never_passes_password_in_argv(self):
        from types import SimpleNamespace
        import sys,os,ctypes
        import ftmo_trial_runner
        product=Mock();sdk=Mock();job=Mock();process=Mock();process.poll.return_value=None
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'terminal';folder.mkdir();terminal=folder/'terminal64.exe';config=folder/'config.ini'
            product.prepare_terminal.return_value=(terminal,config)
            product.verify_identity.return_value=SimpleNamespace(trade_mode=0,currency='USD',server='FTMO-Demo',company='FTMO')
            sdk.initialize.return_value=True;sdk.terminal_info.return_value=SimpleNamespace(path=str(folder),data_path=str(folder))
            kernel=Mock();kernel.NtResumeProcess.return_value=0
            fake=SimpleNamespace(_WorkerOwnedJob=lambda:job)
            with patch.object(c,'ROOT',root),patch.dict(sys.modules,{'trading_workspace_v2.nautilus_worker':fake}),patch.object(c.subprocess,'Popen',return_value=process),patch.object(ctypes,'WinDLL',return_value=kernel):
                process._handle=123
                with c.trial_session(self.values(),sdk=sdk,product=product,inventory=[]) as out:self.assertEqual(out,str(terminal))
                args=c.subprocess.Popen.call_args
                self.assertNotIn('fixture-password',str(args));self.assertEqual(args.kwargs['creationflags'],4)
            job.assign.assert_called_once_with(process);job.close.assert_called_once();sdk.shutdown.assert_called_once()
            self.assertFalse(list((root/'.runtime/ftmo-trial-readonly-v24').glob('*.lock')))
