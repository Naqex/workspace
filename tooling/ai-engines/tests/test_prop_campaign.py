from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prop_campaign_source import Prices, END, FINAL, DTYPE, stamp,deadline
from prop_campaign_exits import covered_stop, path, quantity, funding_rate
from prop_campaign_accounts import Account, CAPITAL, stats


class Quotes:
    def __init__(self,rows):
        self.rows=np.array(rows,dtype=DTYPE)
    def endpoint(self,at):
        i=int(self.rows['t'].searchsorted(at))
        if i==len(self.rows) or self.rows['t'][i]-at>60000:return None
        r=self.rows[i];return [int(r['t']),int(r['b']),int(r['a']),i]
    def path(self,start,end):
        a=self.rows;mask=(a['t']>=start)&(a['t']<=end)
        return a[mask],np.flatnonzero(mask)


class Calendar:
    def __init__(self,end):self.end=end
    def deadline(self,at):return self.end,'TIME_48H'


class CampaignTests(unittest.TestCase):
    def test_price_scope_is_enforced_before_files(self):
        p=Prices({},END)
        with self.assertRaisesRegex(ValueError,'closed'):p.hour(END)
        with self.assertRaisesRegex(ValueError,'closed'):Prices({},FINAL).hour(FINAL)
        with self.assertRaisesRegex(ValueError,'cutoff'):Prices({},FINAL+1)

    def test_horizon_clock_starts_at_observed_entry_tick(self):
        class C:
            def deadline(self,at):return at+48*3600000,'TIME_48H'
        r=dict(recipe='A',decision_msc=stamp('2023-06-20T08:00:00'))
        actual=r['decision_msc']+127
        self.assertEqual(deadline(r,C(),actual)[0],actual+48*3600000)

    def fixture(self):
        at=stamp('2023-06-20T08:00:00');end=at+2*3600000
        r=dict(recipe='A',side='BUY',decision_msc=at,day='2023-06-20',stop_units=1990000)
        q=Quotes([(at,1999900,2000000),(at+60000,2016000,2016100),
                  (at+120000,1995000,1995100),(end,2020000,2020100)])
        return r,q,Calendar(end)

    def test_initial_stop_and_tail_remain_for_baseline(self):
        r,q,c=self.fixture();t,_=path(r,q,c,'A0','ASYM_FLAT',[])
        self.assertEqual(t['exit_price_units'],2020000)
        self.assertEqual(t['stop_units'],1990000)

    def test_protection_acts_next_quote_and_gap_can_lose(self):
        r,q,c=self.fixture();t,_=path(r,q,c,'E2','ASYM_FLAT',[])
        self.assertEqual(t['reason'],'PROTECTED_SL')
        self.assertLess(t['costs']['ASYM_FLAT']['net_R'],0)
        self.assertEqual(t['exit_quote_index'],2)

    def test_cost_reserved_stop_covers_future_wednesday(self):
        r,_,_=self.fixture()
        t=dict(r,entry_msc=r['decision_msc'],entry_price_units=2000000,
            deadline_msc=stamp('2023-06-22T08:00:00'))
        stop=covered_stop(t,'ASYM_FLAT')
        self.assertGreater(stop,2000000+2200)
        self.assertGreaterEqual(stop,t['stop_units'])

    def test_quantity_rounds_down_and_funding_is_directional(self):
        self.assertEqual(quantity(dict(entry_price_units=2000000,stop_units=1991000),175),19)
        self.assertEqual(funding_rate('SELL','ASYM_FLAT'),-.05)
        self.assertEqual(funding_rate('SELL','SYM_FLAT'),-.40)

    def test_endpoint_not_fabricated(self):
        r,q,c=self.fixture()
        with self.assertRaisesRegex(ValueError,'missing_deadline'):
            path(r,q,Calendar(c.end+120000),'A0','ASYM_FLAT',[])

    def test_risk_phase_throttle_and_exact_thresholds(self):
        c=Account(0,10**15,'SYM_FLAT',rolling=True)
        self.assertEqual(c.risk(CAPITAL),250)
        c.balance=c.anchor-900000
        self.assertEqual(c.risk(CAPITAL),250)
        c.balance-=1
        self.assertEqual(c.risk(CAPITAL),125)
        c.balance=c.anchor
        self.assertEqual(c.risk(47749999),125)
        c.phase=2
        self.assertEqual(c.risk(CAPITAL),175)
        c.phase=3
        self.assertEqual(c.risk(CAPITAL),125)

    def test_breach_before_pass_and_equal_floor_not_breach(self):
        c=Account(0,10**15,'SYM_FLAT',rolling=True)
        c.balance=47500000;c.check(1,0)
        self.assertIsNone(c.breach)
        c.check(2,-1)
        self.assertTrue(c.breach['daily'])
        self.assertFalse(c.passes)

    def test_phase_pass_flat_four_days_and_capital_reset(self):
        c=Account(0,10**15,'SYM_FLAT',rolling=True)
        c.balance=55000000;c.phase_days={'a','b','c'}
        c.check(1,0);self.assertEqual(c.phase,1)
        c.phase_days.add('d');c.check(2,0)
        self.assertEqual(c.phase,2);self.assertEqual(c.balance,CAPITAL)
        self.assertEqual(c.gate,2);self.assertFalse(c.phase_days)
        c.balance=52500000;c.phase_days={'a','b','c','d'};c.check(3,0)
        self.assertEqual(c.phase,3)

    def test_reward_debit_and_firm_share_reconcile(self):
        c=Account(0,10**15,'SYM_FLAT',rolling=True)
        c.phase=3;c.funded_first=1000;c.balance=50100000
        c.reward(1000+29*86400000);self.assertFalse(c.payouts)
        c.reward(1000+30*86400000)
        p=c.payouts[0]
        self.assertEqual(p['trader_usd'],80)
        self.assertEqual(p['firm_usd'],20)
        self.assertEqual(c.balance,CAPITAL)
        c.balance=49000000;c.reward(1000+60*86400000)
        self.assertEqual(c.balance,49000000);self.assertEqual(len(c.payouts),1)

    def test_reward_minimum_and_open_position(self):
        c=Account(0,10**15,'SYM_FLAT',rolling=True)
        c.phase=3;c.funded_first=0;c.balance=50019990;c.reward(40*86400000)
        self.assertFalse(c.payouts)
        c.balance=50020000;c.active[1]=(1,125);c.reward(40*86400000)
        self.assertFalse(c.payouts)

    def test_shared_stop_reserve_blocks_full_requested_risk(self):
        r,q,cal=self.fixture();t,_=path(r,q,cal,'A0','SYM_FLAT',[])
        c=Account(0,10**15,'SYM_FLAT',rolling=True)
        c.balance=45200000
        self.assertLess(c.reserve_floor([t],0,25,1000),45000000)

    def test_drawdown_order_and_negative_marks(self):
        s=stats(np.array([0,100,-10,90,-100]))
        self.assertEqual(s['dd'],200);self.assertEqual(s['low'],-100)
        c=Account(0,10**15,'SYM_FLAT')
        c.metrics(CAPITAL-100,CAPITAL+300,200)
        c.metrics(CAPITAL-50,CAPITAL,100)
        self.assertEqual(c.dd,350)

    def test_flat_start_and_no_signal_reuse(self):
        r,q,cal=self.fixture();t,_=path(r,q,cal,'A0','SYM_FLAT',[])
        c=Account(t['entry_msc']+1,10**15,'SYM_FLAT',rolling=True)
        c.action('entry',t['entry_msc'],0,[t],t['entry_quote'])
        self.assertFalse(c.active)
        c=Account(0,10**15,'SYM_FLAT',rolling=True);c.gate=t['decision_msc']
        c.action('entry',t['entry_msc'],0,[t],t['entry_quote'])
        self.assertEqual(c.rejected['PRESTART_OR_PHASE_GATE'],1)

    def test_collision_is_causal_admission_not_trade_deletion(self):
        r,q,cal=self.fixture();t,_=path(r,q,cal,'A0','SYM_FLAT',[])
        s=dict(t,recipe='S1')
        c=Account(0,10**15,'SYM_FLAT')
        c.action('entry',t['entry_msc'],0,[t,s],t['entry_quote'])
        c.action('entry',s['entry_msc'],1,[t,s],s['entry_quote'])
        self.assertEqual(len(c.active),1)
        self.assertEqual(c.rejected['ASSET_DECISION_COLLISION'],1)

    def test_e1_flat_is_before_swap_and_keeps_original_stop(self):
        at=stamp('2023-06-20T08:00:00');flat=stamp('2023-06-20T20:30:00')
        end=stamp('2023-06-21T08:00:00')
        r=dict(recipe='A',side='BUY',decision_msc=at,day='2023-06-20',stop_units=1990000)
        q=Quotes([(at,1999900,2000000),(flat,2005000,2005100),(end,1990000,1990100)])
        t,_=path(r,q,Calendar(end),'E1','ASYM_FLAT',[])
        self.assertEqual(t['exit_msc'],flat);self.assertEqual(t['reason'],'E1_FLAT')
        self.assertEqual(t['costs']['ASYM_FLAT']['swap_usd'],0)
        self.assertEqual(t['stop_units'],1990000)

    def test_e3_closed_market_is_unknown_not_a_late_fill(self):
        at=stamp('2023-06-20T08:00:00');end=stamp('2023-06-21T08:00:00')
        after=stamp('2023-06-20T22:00:00')
        r=dict(recipe='A',side='BUY',decision_msc=at,day='2023-06-20',stop_units=1990000)
        q=Quotes([(at,1999900,2000000),(after,2005000,2005100),(end,2006000,2006100)])
        t,_=path(r,q,Calendar(end),'E3','ASYM_FLAT',[])
        self.assertEqual(t['exit_policy_unknown'],'E3_DECISION_NO_FRESH_QUOTE')
        self.assertNotEqual(t['exit_msc'],after)

    def test_e2_h1_trailing_only_after_activation(self):
        r,q,c=self.fixture()
        # An opposite close before the profitable tick is not an exit.
        t,_=path(r,q,c,'E2','SYM_FLAT',[(r['decision_msc'],100,200)])
        self.assertEqual(t['reason'],'PROTECTED_SL')

    def test_right_censoring_does_not_force_a_pass(self):
        c=Account(0,100,'SYM_FLAT',rolling=True)
        c._trades=[];c.balance=CAPITAL
        r=c.dump()
        self.assertEqual(r['status'],'RIGHT_CENSORED')
        self.assertEqual(r['trader_payout_usd'],0)
        self.assertFalse(r['prop_qualified'])

    def test_entry_fee_is_realized_but_swap_remains_floating_at_reset(self):
        r,q,cal=self.fixture();t,_=path(r,q,cal,'A0','SYM_FLAT',[])
        c=Account(0,10**15,'SYM_FLAT')
        c.action('entry',t['entry_msc'],0,[t],t['entry_quote'])
        b=c.balance
        c.action('swap',t['entry_msc']+100,0,[t],t['entry_quote'],3)
        self.assertEqual(c.balance,b)
        c.action('reset',t['entry_msc']+101,None,[t],t['entry_quote'])
        self.assertEqual(c.anchor,b)
        self.assertLess(c.floating([t],t['entry_quote']),-200*quantity(t))


if __name__=='__main__':unittest.main()
