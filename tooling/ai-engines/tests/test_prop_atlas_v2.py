from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prop_atlas_core import carry_path
from prop_atlas_scan import catalog,candidates,money,exit_deadline,daily_context
from prop_atlas_source import ComponentQuotes
from prop_campaign_source import stamp,HOUR,DAY,END
from prop_campaign_exits import costs
from test_prop_campaign import Quotes
from prop_atlas_policy import RiskV2


def parent(side='BUY'):
    at=stamp('2023-06-20T08:00:00');end=at+48*HOUR
    t=dict(recipe='A',signal_id='fixture',day='2023-06-20',side=side,
        decision_msc=at,entry_msc=at,entry_price_units=2000000,
        entry_quote_index=0,entry_quote=[at,1999900,2000000],
        exit_msc=end,exit_quote_index=4,exit_price_units=2005000,
        deadline_msc=end,stop_units=1990000 if side=='BUY' else 2010000,
        natural_sl_usd_per_oz=10,reason='TIME_48H')
    return t


class AtlasTests(unittest.TestCase):
    def reader(self,when,p=2005000):
        t=parent();rows=[(t['entry_msc'],1999900,2000000),
            (when,p,p+100),(t['exit_msc'],2005000,2005100)]
        return Quotes(rows)

    def test_catalog_budget_and_structural_dedup(self):
        c=catalog()
        self.assertEqual(len(c),112);self.assertEqual(len({r['id'] for r in c}),112)
        self.assertEqual(sum(r['asset']=='XAUUSD' for r in c),16)
        self.assertEqual(sum(r['asset']=='USDJPY' for r in c),0)

    def test_ca1_closes_buy_without_swap(self):
        t=parent();when=t['entry_msc']//DAY*DAY+20*HOUR+HOUR//2
        r=carry_path(t,'CA1','ASYM_FLAT',self.reader(when))
        self.assertEqual(r['exit_msc'],when)
        self.assertEqual(costs(r,'ASYM_FLAT')['swap_usd'],0)
        self.assertEqual(r['stop_units'],t['stop_units'])

    def test_sell_is_unchanged_by_both_carry_policies(self):
        t=parent('SELL')
        for p in ('CA1','CA2'):
            r=carry_path(t,p,'ASYM_FLAT',None)
            self.assertEqual(r['exit_msc'],t['exit_msc'])
            self.assertEqual(r['exit_price_units'],t['exit_price_units'])

    def test_ca2_only_wednesday_if_profit_not_cushioned(self):
        t=parent();when=stamp('2023-06-21T20:30:00')
        r=carry_path(t,'CA2','ASYM_FLAT',self.reader(when))
        self.assertEqual(r['exit_msc'],when)
        self.assertEqual(costs(r,'ASYM_FLAT')['swap_usd'],-6.75)

    def test_ca2_keeps_large_tail_without_tp_cap(self):
        t=parent();when=stamp('2023-06-21T20:30:00')
        r=carry_path(t,'CA2','ASYM_FLAT',self.reader(when,2020000))
        self.assertEqual(r['exit_msc'],t['exit_msc'])

    def test_unknown_clock_not_filled_at_next_hour(self):
        t=parent();when=stamp('2023-06-20T21:00:00')
        r=carry_path(t,'CA1','ASYM_FLAT',self.reader(when))
        self.assertIn('exit_policy_unknown',r)

    def test_component_reader_has_scope_and_clock_fences(self):
        q=ComponentQuotes({},100000,'H1_OPEN_PROXY')
        with self.assertRaisesRegex(ValueError,'fence'):q.endpoint(END)
        self.assertIsNone(q.endpoint(stamp('2023-06-20T20:30:00')))

    def test_sweep_uses_closed_bar_no_future_h1(self):
        start=stamp('2023-05-25')
        rows=[[start+i*HOUR,100000,105000,95000,100000,60] for i in range(26*24)]
        target=stamp('2023-06-20T08:00:00')
        rows.append([target,94000,103000,90000,100000,60])
        signals,_=candidates(rows,'XAUUSD')
        at=target+HOUR;prefix=[r for r in signals if r['decision_msc']==at]
        self.assertTrue(prefix)
        rows.append([at,100000,900000,1000,800000,60])
        later,_=candidates(rows,'XAUUSD')
        self.assertEqual(prefix,[r for r in later if r['decision_msc']==at])
        self.assertTrue(all(r['side']=='BUY' for r in prefix))

    def test_stress_fx_cost_and_wednesday_triple_are_not_zeroed(self):
        at=stamp('2023-06-21T08:00:00')
        r=dict(asset='EURUSD',side='BUY')
        c=money(r,[at,100000,100010,0],[at+24*HOUR,100000,100010,0],100000,'ASYM_FLAT')
        self.assertAlmostEqual(c['commission']+c['slippage'],.00009)
        self.assertAlmostEqual(c['swap'],-.0012)
        self.assertLess(c['net'],0)

    def test_progressive_risk_thresholds_and_funded_never_increases(self):
        c=RiskV2(0,10**15,'ASYM_FLAT',rolling=True)
        for eq,want in ((50000000,200),(49000000,200),(48750000,200),
                        (48749999,150),(47750000,150),(47749999,90)):
            self.assertEqual(c.risk(eq),want)
        c.phase=3
        self.assertEqual(c.risk(49000000),125)
        self.assertEqual(c.risk(48000000),125)
        self.assertEqual(c.risk(47000000),90)

    def test_daily_soft_cap_and_recovery(self):
        c=RiskV2(0,10**15,'ASYM_FLAT',rolling=True)
        c.balance=49099999
        self.assertEqual(c.risk(49099999),125)
        c.anchor=c.balance
        self.assertEqual(c.risk(c.balance),200)

    def test_internal_reserve_rejects_whole_order_no_artificial_resize(self):
        c=RiskV2(0,10**15,'ASYM_FLAT',rolling=True);t=parent()
        c.balance=46550000;c.anchor=c.balance
        c.action('entry',t['entry_msc'],0,[t],t['entry_quote'])
        self.assertFalse(c.active)
        self.assertEqual(c.rejected['INTERNAL_STATIC_7PCT_RESERVE'],1)
        self.assertEqual(len(c.internal_rejections),1)


if __name__=='__main__':unittest.main()
