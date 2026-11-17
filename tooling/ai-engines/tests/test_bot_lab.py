from pathlib import Path
import tempfile,json,unittest
from quant_core.bot_lab import inspect_bytes,log_rows,fingerprint
from quant_core.research_fast_fail import toxicity_scale

class BotLabTests(unittest.TestCase):
    def test_loss_linked_lot_multiplication_is_flagged(self):
        p=inspect_bytes(b'if last_profit < 0:\n    lot *= 2\n','.py')
        self.assertIn('MARTINGALE_GRID_TOXICITY',[r['flag'] for r in p['findings']])
    def test_comments_and_docstrings_are_not_live_code(self):
        p=inspect_bytes(b'"""if last_loss: lot *= 2"""\n# last_loss lot *= 2\nlot = 1\n','.py')
        self.assertEqual(p['findings'],[])
    def test_multiplication_without_loss_is_not_declared_martingale(self):
        self.assertEqual(inspect_bytes(b'lot = lot * 2\n','.py')['findings'],[])
    def test_calendar_filter_requires_review_not_a_proven_scam(self):
        p=inspect_bytes(b'if year == 2022:\n    skip = True\n','.py')
        self.assertEqual(p['findings'][0]['confidence'],'REVIEW_ONLY')
    def test_literal_MT4_no_SL_is_detected(self):
        p=inspect_bytes(b'OrderSend(symbol,OP_BUY,lot,Ask,3,0,100);','.mq4')
        self.assertIn('NO_STOP_LOSS_TOXICITY',[v['flag'] for v in p['findings']])
    def test_python_order_dictionary_no_SL_is_detected(self):
        p=inspect_bytes(b"mt5.order_send({'sl': 0, 'volume': 1})",'.py')
        self.assertIn('NO_STOP_LOSS_TOXICITY',[v['flag'] for v in p['findings']])
    def test_source_never_runs_imports_or_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'must-not-exist'
            code=f"open({str(path)!r},'w').write('bad')\nraise RuntimeError('must not execute')"
            self.assertFalse(inspect_bytes(code.encode(),'.py')['execution_performed']);self.assertFalse(path.exists())
    def test_binary_ASCII_and_UTF16_are_evidence_only(self):
        p=inspect_bytes(b'\x00iATR\x00'+ 'iRSI'.encode('utf-16le'),'.ex5')
        self.assertIn('iATR',p['string_signatures']);self.assertIn('iRSI',p['string_signatures'])
        self.assertEqual(p['logic_recovery'],'UNAVAILABLE_FROM_STRINGS')
    def test_binary_cannot_pass_scale_gate(self):
        self.assertFalse(toxicity_scale(inspect_bytes(b'opaque','.ex4'),friction=1,median_stop=20,retention=1)['passed'])
    def test_sensitive_source_lines_are_redacted(self):
        p=inspect_bytes(b"password = 'fixture-password'\nif password: buy()",'.py')
        self.assertNotIn('fixture-password',json.dumps(p))
    def test_pine_and_CSharp_indicator_names(self):
        self.assertIn('ta.atr',inspect_bytes(b'x = ta.atr(14)','.pine')['indicators'])
        self.assertIn('RelativeStrengthIndex',inspect_bytes(b'x=RelativeStrengthIndex(14);','.cs')['indicators'])
    def test_unsupported_and_oversize_inputs_fail_before_analysis(self):
        with self.assertRaises(ValueError):inspect_bytes(b'', '.zip')
        with self.assertRaises(ValueError):inspect_bytes(b'x'*(16*1024*1024+1),'.ex5')
    def test_naive_log_time_needs_explicit_timezone(self):
        with self.assertRaisesRegex(ValueError,'TIMEZONE'):fingerprint([dict(open_time='2023-01-01T12:00',price=1,sl=.9,tp=1.2,symbol='EURUSD')])
    def test_log_formats_share_canonical_semantics(self):
        row=dict(open_time='2023-01-01T12:00Z',price='1.1',sl='1',tp='1.3',symbol='EURUSD')
        csv=b'open_time,price,sl,tp,symbol\n2023-01-01T12:00Z,1.1,1,1.3,EURUSD\n'
        html=('<table><tr>'+''.join('<th>'+k+'</th>' for k in row)+'</tr><tr>'+''.join('<td>'+v+'</td>' for v in row.values())+'</tr></table>').encode()
        for raw,suffix in ((json.dumps([row]).encode(),'.json'),(csv,'.csv'),(html,'.html')):
            result=fingerprint(log_rows(raw,suffix));self.assertEqual(result['session_hour_UTC'],{12:1});self.assertFalse(result['algorithm_identifiable'])
    def test_log_rejects_nan_and_dst_ambiguity(self):
        row=dict(open_time='2023-01-01T12:00Z',price='nan',symbol='EURUSD')
        with self.assertRaises(ValueError):fingerprint([row])
        row.update(open_time='2023-10-29T02:30',price=1)
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):fingerprint([row],timezone_name='Europe/Prague')
    def test_market_unknown_is_preserved(self):
        r=fingerprint([dict(open_time='2023-01-01T12:00Z',price=1,symbol='EURUSD')])
        self.assertEqual(r['geometry'][0]['market_features_status'],'MARKET_DATA_REQUIRED')
