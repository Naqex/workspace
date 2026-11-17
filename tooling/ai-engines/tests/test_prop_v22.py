from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import time
import numpy as np
from quant_core.exhaustion_gate import fit_thresholds,accept,resolution_cutoff
import ftmo_trial_runner as runner


def row(**kw):
    r=dict(id='XAUUSD|F3:test',family='F3',year=2022,day_range_ATR=.9)
    r.update(kw);return r


def sdk_fixture(**account_changes):
    account=dict(trade_mode=0,server='FTMO-Demo',company='FTMO',currency='USD',login=1234)
    account.update(account_changes)
    def obj(v):return SimpleNamespace(_asdict=lambda:v)
    class SDK:
        calls=[]
        def initialize(self,**kw):self.calls.append(('initialize',kw));return True
        def shutdown(self):self.calls.append(('shutdown',))
        def account_info(self):return obj(account)
        def terminal_info(self):return obj(dict(connected=True,ping_last=153000))
        def symbol_info(self,asset):return obj(dict(name=asset))
        def symbol_info_tick(self,asset):return obj(dict(time_msc=int(time.time()*1000),bid=100.,ask=100.1))
    s=SDK();s.calls=[];return s


TERMINAL='C:/fixture/terminal64.exe'
INVENTORY=[dict(ExecutablePath=TERMINAL)]


class V22Tests(unittest.TestCase):
    def test_gate_A_boundary_and_F5_untouched(self):
        self.assertTrue(accept(row(),'G_L3_A',{}));self.assertFalse(accept(row(day_range_ATR=.90001),'G_L3_A',{}))
        self.assertTrue(accept(row(family='F5',day_range_ATR=100),'G_L3_A',{}))

    def test_unknown_exhaustion_abstains_for_gold_only(self):
        self.assertFalse(accept(row(day_range_ATR=None),'G_L3_A',{}))
        self.assertTrue(accept(row(family='F5',day_range_ATR=None),'G_L3_B',{}))

    def test_threshold_fit_rejects_validation_rows(self):
        with self.assertRaisesRegex(ValueError,'Development'):fit_thresholds([row(year=2024)])

    def test_threshold_fit_never_uses_returns_or_labels(self):
        rows=[row(day_range_ATR=v,net_R=v,label='W1') for v in (.3,.6,.9,1.2)]
        expected=fit_thresholds(rows)
        changed=deepcopy(rows)
        for r in changed:r.update(net_R=-100,label='L3')
        self.assertEqual(expected,fit_thresholds(changed))
        self.assertAlmostEqual(expected[rows[0]['id']],1.11)

    def test_per_sleeve_normalization_is_not_cross_asset_price_comparison(self):
        rows=[row(day_range_ATR=1),row(id='XAUUSD|F4:test',family='F4',day_range_ATR=2)]
        f=fit_thresholds(rows);self.assertEqual(f[rows[0]['id']],1);self.assertEqual(f[rows[1]['id']],2)

    def test_unknown_or_unregistered_gate_rejected(self):
        with self.assertRaises(ValueError):accept(row(),'hindsight',{})
        self.assertFalse(accept(row(),'G_L3_B',{}))

    def test_resolution_clamp_is_known_grid_not_last_available_quote(self):
        d=20*3600000+30*60000
        self.assertEqual(resolution_cutoff(d,step=3600000),20*3600000)
        self.assertEqual(resolution_cutoff(d,step=60000),d)

    def test_early_close_clamp_is_rounded_earlier_never_later(self):
        d=17*3600000+45*60000
        self.assertEqual(resolution_cutoff(d,step=3600000),17*3600000)
        with self.assertRaises(ValueError):resolution_cutoff(d,step=300000)

    def test_preflight_no_terminal_does_not_initialize_or_fake_replay(self):
        s=sdk_fixture();r=runner.check_mt5_ready(sdk=s,inventory=[])
        self.assertFalse(r['read_only_ready']);self.assertEqual(r['reason'],'NO_RUNNING_TERMINAL');self.assertEqual(s.calls,[])

    def test_preflight_multiple_terminals_require_explicit_path(self):
        s=sdk_fixture();r=runner.check_mt5_ready(sdk=s,inventory=INVENTORY*2)
        self.assertEqual(r['reason'],'MULTIPLE_TERMINALS_REQUIRE_EXPLICIT_PATH');self.assertEqual(s.calls,[])

    def test_preflight_running_path_binding_prevents_autostart(self):
        s=sdk_fixture();r=runner.check_mt5_ready(terminal='C:/other/terminal64.exe',sdk=s,inventory=INVENTORY)
        self.assertFalse(r['read_only_ready']);self.assertEqual(s.calls,[])

    def test_preflight_demo_account_and_reported_ping_units(self):
        s=sdk_fixture();r=runner.check_mt5_ready(sdk=s,inventory=INVENTORY)
        self.assertTrue(r['read_only_ready']);self.assertEqual(r['last_reported_broker_ping_ms'],153)
        self.assertFalse(r['shadow_ready']);self.assertFalse(r['ping_is_fresh_network_measurement'])
        self.assertNotIn('login',r['account']);self.assertEqual(s.calls[-1],('shutdown',))

    def test_preflight_rejects_real_unrelated_and_nonUSD_accounts(self):
        for changes in (dict(trade_mode=2),dict(server='Other',company='Other'),dict(currency='EUR')):
            s=sdk_fixture(**changes);r=runner.check_mt5_ready(sdk=s,inventory=INVENTORY)
            self.assertFalse(r['read_only_ready']);self.assertEqual(s.calls[-1],('shutdown',))

    def test_preflight_stale_active_quote_is_not_ready(self):
        s=sdk_fixture();s.symbol_info_tick=lambda a:SimpleNamespace(_asdict=lambda:dict(time_msc=0,bid=100.,ask=101.))
        r=runner.check_mt5_ready(sdk=s,inventory=INVENTORY);self.assertFalse(r['read_only_ready'])

    def test_preflight_missing_inactive_symbol_remains_visible_without_trading(self):
        s=sdk_fixture();s.symbol_info=lambda a:None if a=='US500' else SimpleNamespace()
        r=runner.check_mt5_ready(sdk=s,inventory=INVENTORY)
        self.assertTrue(r['read_only_ready']);self.assertFalse(r['symbols']['US500']['info_readable'])

    def test_preflight_failed_IPC_is_not_connected(self):
        s=sdk_fixture();s.initialize=lambda **kw:False;r=runner.check_mt5_ready(sdk=s,inventory=INVENTORY)
        self.assertFalse(r['terminal_connected']);self.assertEqual(r['reason'],'READONLY_IPC_ATTACH_FAILED')

    def test_preflight_does_not_call_submission_or_symbol_selection(self):
        import inspect
        source=inspect.getsource(runner.check_mt5_ready)
        for call in ('.order_send(','.order_check(','.login(','.symbol_select('):self.assertNotIn(call,source)

    def test_preflight_symbol_failure_closes_IPC_and_preserves_unknown(self):
        s=sdk_fixture()
        def bad(a):raise RuntimeError('private detail')
        s.symbol_info=bad;r=runner.check_mt5_ready(sdk=s,inventory=INVENTORY)
        self.assertEqual(r['error_type'],'RuntimeError');self.assertNotIn('private detail',str(r));self.assertEqual(s.calls[-1],('shutdown',))
