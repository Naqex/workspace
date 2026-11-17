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
        r=Mock();r.account.return_value={'server':'FTMO-Demo'};t=1794916800000
        r.ticks.return_value=[dict(time_msc=t+7200000,bid=1,ask=2),dict(time_msc=t+7202000,bid=1,ask=2)]
        rows=c.ClockReader(r).ticks('EURUSD',t,t+1000)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['time_msc'],t);self.assertEqual(r.ticks.call_args.args[1],t+7200000)
    def test_running_owned_terminal_is_never_cleaned_or_rotated(self):
        import uuid
        v=self.values();folder=c.ROOT/'.runtime/ftmo-trial-readonly-v24'/str(uuid.uuid5(uuid.NAMESPACE_URL,'123|FTMO-Demo'))
        product=Mock()
        with self.assertRaisesRegex(ValueError,'ALREADY_RUNNING'):
            with c.trial_session(v,product=product,inventory=[dict(ExecutablePath=str(folder/'terminal64.exe'))]):pass
        product.prepare_terminal.assert_not_called()
