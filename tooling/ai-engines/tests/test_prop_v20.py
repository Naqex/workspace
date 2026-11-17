import unittest
from decimal import Decimal
from types import SimpleNamespace

from prop_v20_accounts import V20Account, V20LedgerOracle


def profile(k=1., house_money=True):
    return dict(name="O2_UNSCALED" if k == 1 else "O2_VOL_CUSHION" if house_money else "O2_VOL",
                k=k, house_money=house_money, weights={"XAUUSD|F3:test|DAY|P0": 1.})


class V20PolicyTests(unittest.TestCase):
    def test_global_scale_follows_throttle_and_sleeve_then_cent_floor(self):
        p=profile(1.25);p["weights"]["XAUUSD|F3:test|DAY|P0"]=1.1
        a=V20Account(0,1000,"SYM_FLAT",rolling=True,profile=p)
        a.current_request=0;a._trades=[dict(id="XAUUSD|F3:test|DAY|P0")]
        self.assertEqual(a.risk_request(50000000,"CORE",1),412.5)
        self.assertEqual(a.risk_request(47500000,"CORE",1),206.25)
        self.assertEqual(a.risk_request(46500000,"CORE",1),103.12)

    def test_house_money_is_existing_realized_phase1_bonus_not_new_sqrt(self):
        for use,expected in ((True,687.5),(False,375.)):
            a=V20Account(0,1000,"SYM_FLAT",rolling=True,profile=profile(1.25,use))
            a.current_request=0;a._trades=[dict(id="XAUUSD|F3:test|DAY|P0")]
            a.balance=51500000;a.cushion_armed=True
            self.assertEqual(a.risk_request(51500000,"CORE",1),expected)
            a.phase=3
            self.assertEqual(a.risk_request(51500000,"CORE",1),234.37)

    def test_invalid_profile_cannot_be_treated_as_an_admitted_scale(self):
        for k in (0.,-1.,float("inf"),float("nan"),2.01):
            with self.assertRaises(ValueError):
                V20Account(0,1000,"SYM_FLAT",profile=profile(k))
        p=profile();p["house_money"]=1
        with self.assertRaises(ValueError):V20Account(0,1000,"SYM_FLAT",profile=p)

    def test_scaled_account_matches_separate_cash_equity_and_admission_oracle(self):
        from test_sl_active_kernel import fixture
        from prop_v14_paths import build
        from quant_core.gap_aware_execution import GapAwarePathIndex
        from quant_core.ftmo_execution_and_calendar import SessionSchedule
        from quant_core.prop_lifecycle_and_parity import simulate,bindings
        from prop_v18_costs import cost_bindings
        import prop_v14_review as review
        bars,m=fixture([(100,101,99,100),(100,104,99,103),(103,108,101,107)])
        m.update(asset="XAUUSD",_index=GapAwarePathIndex(bars,asset="XAUUSD",schedule=SessionSchedule([])))
        trades,readers,missing=build({"XAUUSD|F3:test|DAY|P0":m},"OPEN_LOW_HIGH_CLOSE",{"XAUUSD":bars,"EURUSD":bars})
        self.assertFalse(missing)
        for t in trades:t["spread_units"]=int(bars["ao"][0])-int(bars["bo"][0])
        for k,use,pct in ((1.,True,100),(1.0060868252930228,True,150),(1.0060868252930228,False,100)):
            first,end=int(bars["t"][0]),int(bars["t"][-1])+60000
            a=V20Account(first,end,"SYM_FLAT",rolling=True,profile=profile(k,use),friction_pct=pct)
            with cost_bindings(pct):
                rows=simulate(trades,readers,[a],first,end,SimpleNamespace(events={}))
                with bindings(review,V14LedgerOracle=V20LedgerOracle):
                    checked=review.audit_accounts(rows,trades,readers,SimpleNamespace(events={}),first,end)
            self.assertEqual(checked[0]["entries"],1)
            self.assertEqual(a.internal_floor_milli,48900000)
            self.assertEqual(a.open_cap_milli,1000000)


if __name__ == "__main__":unittest.main()
