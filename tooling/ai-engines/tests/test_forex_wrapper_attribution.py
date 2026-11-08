import contextlib
from copy import deepcopy
from datetime import datetime
from fractions import Fraction as F
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forex_wrapper_attribution import CANDIDATE, factorial, match_book, main
from test_forex_screen_diagnostics import fixture


def book():
    row=fixture('SELL')
    start=int(datetime(2019,3,11,2,tzinfo=ZoneInfo('America/New_York')).timestamp())*1000
    row.update(candidate=CANDIDATE,scenario='cost-stress',financing_debit_usd=0,
        financing_events=[],balance_usd='10009.10',net_equity_usd='9.10',pending_action=None)
    row['trades'][0].update(timed_financing_usd=0,net_usd='9.10',entry_time_msc=start+1,
        exit_interval_msc=[start+3600000,start+3600000],reason='strategy_exit')
    events=[dict(day='2019-03-11',entry_eligible=True,
        quotes=dict(entry=dict(time_msc=start+1,bid='1.10000',ask='1.10010'),exit_1400=dict(time_msc=start+6*3600000)),
        views=dict(baseline_1400=dict(status='resolved',outcomes=dict(stress=dict(net_usd_per_standard_lot='81.0')))))]
    return row,events


class WrapperTests(unittest.TestCase):
    def test_two_paths_and_interaction_match_hand_calculation(self):
        rows=[dict(quantity='.1',no_stop_unit_usd='100',parent_unit_usd='-20'),
              dict(quantity='.3',no_stop_unit_usd='-50',parent_unit_usd='-30')]
        result=factorial(rows)['exact']
        expected=dict(equal_lot_no_stop_usd='10',equal_lot_parent_usd='-10',
            observed_lots_no_stop_usd='-5',observed_lots_parent_usd='-11',
            weighting_without_stop_usd='-15',stop_at_observed_weights_usd='-6',interaction_usd='14')
        self.assertEqual({k:result[k] for k in expected},expected)
        self.assertEqual(factorial(rows[::-1])['exact'],result)

    def test_uniform_weights_remove_weighting_and_interaction(self):
        result=factorial([dict(quantity='.1',no_stop_unit_usd=r,parent_unit_usd=s)
            for r,s in [('100','-20'),('-50','-30')]])
        self.assertEqual(result['exact']['weighting_without_stop_usd'],'0')
        self.assertEqual(result['exact']['interaction_usd'],'0')
        self.assertFalse(result['counterfactual_is_account_backtest'])

    def test_scale_changes_cash_but_not_unit_return_and_repeating_mean_is_exact(self):
        rows=[dict(quantity=q,no_stop_unit_usd=r,parent_unit_usd=s) for q,r,s in
              [('.01','1','-4'),('.02','2','5'),('.04','-3','1')]]
        original=factorial(rows)['exact']
        self.assertEqual(F(original['mean_lots']),F(7,300))
        doubled=[r|dict(quantity=str(F(r['quantity'])*2)) for r in rows]
        scaled=factorial(doubled)['exact']
        self.assertEqual(F(scaled['observed_lots_parent_usd']),2*F(original['observed_lots_parent_usd']))
        self.assertEqual(scaled['lot_weighted_no_stop_mean_pips'],original['lot_weighted_no_stop_mean_pips'])

    def test_bad_quantity_and_nonfinite_return_rejected_and_empty_is_inconclusive(self):
        for q in ('0','-.1','.015','NaN','1/0'):
            with self.subTest(q=q),self.assertRaises(ValueError):
                factorial([dict(quantity=q,no_stop_unit_usd='1',parent_unit_usd='1')])
        with self.assertRaises(ValueError):factorial([dict(quantity='.1',no_stop_unit_usd='Infinity',parent_unit_usd=0)])
        self.assertEqual(factorial([])['status'],'inconclusive_empty_common_mask')

    def test_actual_parent_partition_retains_unresolved_without_zero_fill(self):
        row,events=book()
        result=match_book(row,events,'cost-stress')
        self.assertEqual(F(result['exact']['observed_lots_no_stop_usd']),F('8.1'))
        self.assertEqual(F(result['exact']['observed_lots_parent_usd']),F('9.1'))
        missing=deepcopy(events);missing[0]['views']['baseline_1400']['status']='missing_or_late_exit'
        result=match_book(row,missing,'cost-stress')
        self.assertEqual(result['status'],'inconclusive_empty_common_mask')
        self.assertEqual(F(result['excluded_parent_net_usd']),F('9.1'))
        self.assertEqual(result['excluded'][0]['reason'],'component_exit_unavailable')

    def test_entry_mismatch_duplicate_and_foreign_scope_rejected(self):
        row,events=book()
        for change in ('price','time','duplicate','funding','candidate','scenario'):
            bad,altered=deepcopy(row),deepcopy(events)
            if change=='price':altered[0]['quotes']['entry']['bid']='1.10001'
            if change=='time':altered[0]['quotes']['entry']['time_msc']+=1
            if change=='duplicate':altered*=2
            if change=='funding':bad['financing_debit_usd']='1'
            if change=='candidate':bad['candidate']='other'
            if change=='scenario':bad['scenario']='reference'
            with self.subTest(change=change),self.assertRaises(ValueError):match_book(bad,altered,'cost-stress')

    def test_cli_refuses_unbound_fixtures_and_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fixtures=root/'fixtures.json';fixtures.write_text(json.dumps(dict(status='passed',tool_sha256='0'*64)))
            args=['--catalogue',str(root),'--component',str(root),'--protocol',str(root/'protocol.md'),
                  '--fixtures',str(fixtures),'--output',str(root/'out')]
            with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(ValueError):main(args)
            self.assertEqual(json.loads((root/'out/progress.json').read_bytes())['phase'],'failed')
            with self.assertRaises(FileExistsError):main(args)


if __name__=='__main__':unittest.main()
