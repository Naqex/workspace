from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_nasdaq_opening5_orb import fixture, update
import nasdaq_opening5_orb as parent
import nasdaq_opening5_bounds as bounds


def hours_for(pairs):
    result = {}
    for stamp,pair in pairs.items():
        at = stamp//bounds.HOUR*bounds.HOUR
        if at not in result:
            result[at] = tuple(dict(timestamp=at, low=r['low'], high=r['high'],
                                   open=r['open'],close=r['close']) for r in pair)
        for side in (0,1):
            result[at][side]['low'] = min(result[at][side]['low'],pair[side]['low'])
            result[at][side]['high'] = max(result[at][side]['high'],pair[side]['high'])
    return result


def run(f, hours=None, scenario='stress', null=False):
    sessions,pairs,start,end = f
    return bounds.simulate(sessions,pairs,hours if hours is not None else hours_for(pairs),
                           start=start,end=end,scenario=scenario,null_control=null)


class BoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent.core.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_complete_input_matches_parent_both_sides_and_costs(self):
        for side in ('BUY','SELL','DOJI'):
            for scenario in ('reference','stress'):
                f=fixture(side=side)
                a=run(f,scenario=scenario)
                b=parent.simulate(f[0],f[1],start=f[2],end=f[3],scenario=scenario)
                self.assertEqual(a['net_lower_usd'],b['net_equity_usd'])
                self.assertEqual(a['net_upper_usd'],b['net_equity_usd'])
                self.assertEqual(a['entries'],b['entries'])

    def test_missing_minute_preserves_wide_loss_branch_and_later_exit(self):
        for side in ('BUY','SELL'):
            f=fixture(side=side);stamps=next(iter(f[0].values()));at=stamps[8]
            hs=hours_for(f[1]);index=0 if side=='BUY' else 1
            hs[at//bounds.HOUR*bounds.HOUR][index]['low']=900
            hs[at//bounds.HOUR*bounds.HOUR][index]['high']=1100
            del f[1][at]
            r=run(f,hs);t=r['trades'][0]
            self.assertLess(t['net_lower_usd'],-25)
            self.assertGreater(t['net_upper_usd'],0)
            self.assertEqual(r['uncertain_trades'],1)
            self.assertFalse(r['parent_unknown_cleared'])
            self.assertFalse(r['execution_authorized'])

    def test_missing_H1_or_inconsistent_envelope_is_inconclusive(self):
        f=fixture();at=next(iter(f[0].values()))[8];hs=hours_for(f[1]);del f[1][at]
        with self.assertRaisesRegex(ValueError,'missing_or_crossed_H1'):run(f,{})
        hs[at//bounds.HOUR*bounds.HOUR][0]['low']=1000
        with self.assertRaisesRegex(ValueError,'excludes_observed'):run(f,hs)

    def test_missing_scheduled_exit_remains_unknown(self):
        f=fixture();del f[1][next(iter(f[0].values()))[-1]]
        with self.assertRaisesRegex(ValueError,'missing_scheduled_exit'):run(f)

    def test_ambiguous_bar_keeps_both_barriers(self):
        f=fixture();at=next(iter(f[0].values()))[8];update(f[1][at][0],low=990,high=1030)
        r=run(f);t=r['trades'][0]
        self.assertEqual(t['exit_price_lower'],t['stop'])
        self.assertEqual(t['exit_price_upper'],t['take_profit'])
        self.assertLess(t['net_lower_usd'],0);self.assertGreater(t['net_upper_usd'],0)

    def test_observed_open_gap_is_exact_and_adverse(self):
        f=fixture();at=next(iter(f[0].values()))[8]
        for row,offset in zip(f[1][at],(D(0),D('.2'))):
            update(row,open=990+offset,low=989+offset,high=991+offset,close=990+offset)
        r=run(f);t=r['trades'][0]
        self.assertEqual(t['exit_price_lower'],D(990))
        self.assertEqual(t['net_lower_usd'],t['net_upper_usd'])
        self.assertLess(t['net_lower_usd'],-25)

    def test_cash_interval_cannot_choose_a_favorable_entry_branch(self):
        f=fixture(('2019-01-02','2019-01-03'))
        days=list(f[0].values());at=days[0][8]
        for stamp in days[1]:
            for row in f[1][stamp]:
                for field in ('open','high','low','close'):row[field]+=4000
        hs=hours_for(f[1]);del f[1][at]
        hs[at//bounds.HOUR*bounds.HOUR][0]['low']=1
        hs[at//bounds.HOUR*bounds.HOUR][0]['high']=2000
        # A severe conditional gap makes the next day's margin eligibility uncertain.
        with self.assertRaisesRegex(ValueError,'cash_interval_changes_entry'):run(f,hs)

    def test_null_never_creates_trade_or_uses_missing_envelope(self):
        f=fixture();del f[1][next(iter(f[0].values()))[8]]
        r=run(f,{},null=True)
        self.assertEqual((r['entries'],r['net_lower_usd'],r['net_upper_usd']),(0,0,0))


if __name__=='__main__':unittest.main()
