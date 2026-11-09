from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forex_uncertainty import bootstrap,binned_trades


class UncertaintyTests(unittest.TestCase):
    def test_constant_expectancy_stays_constant_and_zero_trades_are_not_zero_edge(self):
        panel={'2023':{'a':dict(net=[25.]*8,counts=[1]*8),'b':dict(net=[0.]*8,counts=[0]*8)}}
        result=bootstrap(panel,draws=50)
        a,b=result['rows']
        self.assertEqual(a['conditional_bootstrap_95pct_interval_r'],[1.,1.])
        self.assertIsNone(b['mean_closed_r'])
        self.assertIsNone(b['conditional_bootstrap_95pct_interval_r'])
        self.assertEqual(b['zero_trade_draws'],50)

    def test_circular_full_block_keeps_cancelling_values_and_reproducible(self):
        panel={'2023':{'a':dict(net=[25.,-25.,25.,-25.],counts=[1]*4)}}
        first=bootstrap(panel,draws=50)
        self.assertEqual(first['rows'][0]['conditional_bootstrap_95pct_interval_r'],[0.,0.])
        self.assertEqual(first,bootstrap(panel,draws=50))
        self.assertFalse(first['selection_adjusted'])

    def test_missing_or_unaligned_series_and_nan_rejected(self):
        panel={'2023':{'a':dict(net=[0.]*8,counts=[1]*8)},'2024':{}}
        with self.assertRaises(ValueError):bootstrap(panel,draws=50)
        panel={'2023':{'a':dict(net=[float('nan')]*8,counts=[1]*8)}}
        with self.assertRaises(ValueError):bootstrap(panel,draws=50)

    def test_flat_account_reconciliation_and_unknown_crossing_bin_rejected(self):
        start=1672531200000
        row=dict(open_position=None,floating_usd='0',pending_entry=False,closed_trades=1,
            trades=[dict(position_id='a',net_usd='25',exit_interval_msc=[start,start])],net_equity_usd='25')
        self.assertEqual(sum(binned_trades(row,2023)['net']),25.)
        bad=deepcopy(row);bad['net_equity_usd']='50'
        with self.assertRaises(ValueError):binned_trades(bad,2023)
        bad=deepcopy(row);bad['trades'][0]['exit_interval_msc']=[start+604800000-1,start+604800000]
        with self.assertRaises(ValueError):binned_trades(bad,2023)
