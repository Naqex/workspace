from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

import numpy as np

from native_ftmo_swing import (
    TREND, INDEX, SwingMarket, Signal, d1_stop, next_entry, path, rollover_units, signals,
)
from native_ftmo_monfri_seal import STOP
from selective_win_diagnosis import LABELS, UNKNOWN, breakdown, classify, classify_trade, dev_scope


def stamp(t):
    return int(datetime.fromisoformat(t).replace(tzinfo=timezone.utc).timestamp())


class SwingScreenTests(unittest.TestCase):
    def test_rollover_applies_once_over_weekend_with_broker_triple_day(self):
        friday=stamp('2024-02-02')
        monday=stamp('2024-02-05')
        self.assertEqual(rollover_units(friday,monday,5),3)
        self.assertEqual(rollover_units(friday,monday,3),1)
        self.assertEqual(rollover_units(stamp('2024-01-31'),stamp('2024-02-01'),3),3)

    def test_gap_fills_at_open_and_sell_triggers_on_ask(self):
        market=SimpleNamespace(spread=.2)
        self.assertEqual(d1_stop(market,95,1,92,90,96),('SL_GAP',92))
        reason,price=d1_stop(market,105,-1,104,103,104.9)
        self.assertEqual(reason,'SL')
        self.assertAlmostEqual(price,104.8)

    def test_index_friday_entry_rule_and_holdout_fence(self):
        thu,fri,mon=(stamp(t) for t in ('2024-02-01','2024-02-02','2024-02-05'))
        m=SimpleNamespace(feed={'t':[thu,fri,mon]})
        self.assertEqual(next_entry(m,Signal(INDEX,'US500.cash',fri,0,1,2.,{}),'SWING'),
                         (None,'INDEX_ENTRY_SCHEDULE'))
        self.assertEqual(next_entry(m,Signal(TREND,'EURUSD',fri,0,1,2.,{}),'FRIDAY_OPEN'),
                         (None,'FRIDAY_ENTRY_VETO'))
        m.feed['t'][2]=STOP
        self.assertEqual(next_entry(m,Signal(TREND,'EURUSD',mon,1,1,2.,{}),'SWING'),
                         (None,'UNRESOLVED_ENTRY'))

    def test_same_index_trade_can_cross_weekend_without_changing_entry(self):
        wed,thu,fri,mon,tue=(stamp(t) for t in ('2024-01-31','2024-02-01','2024-02-02','2024-02-05','2024-02-06'))
        feed={'t':np.array([wed,thu,fri,mon,tue]), 'complete':np.array([thu,fri,fri+86400,tue,tue+86400]),
              'o':[100.,100.,99.,104.,107.],'l':[99.,98.,98.,103.,106.],
              'h':[101.,102.,101.,107.,110.], 'c':[100.,99.,100.,106.,109.], 'atr':[5.]*5}
        spec=dict(trade_contract_size=1,volume_min=.01,volume_step=.01,volume_max=100,
                  point=.01,swap_long=-2,swap_short=-3,swap_rollover3days=5,swap_mode=1,
                  currency_margin='USD',currency_profit='USD')
        observed={'US500.cash':dict(bid=100.,ask=100.2,sides={k:dict(margin_100_usd=10.) for k in ('BUY','SELL')})}
        market=SwingMarket('US500.cash',{'US500.cash':feed},spec,{'median':.2},observed)
        s=Signal(INDEX,'US500.cash',thu,0,1,5.,{})
        swing,_=path(market,s,[100.,102.,102.,102.,102.],'SWING')
        friday,_=path(market,s,[100.,102.,102.,102.,102.],'FRIDAY_OPEN')
        self.assertEqual((swing['entry'],friday['entry']),(thu,thu))
        self.assertEqual((swing['exit'],friday['exit']),(tue,fri))
        self.assertEqual((swing['reason'],friday['reason']),('INDEX_TIME','FRIDAY_CUTOFF'))
        self.assertAlmostEqual(swing['swap']-friday['swap'],-.08)

    def test_entry_signal_uses_completed_bar_not_next_open_or_close(self):
        start=stamp('2018-01-01')
        clock=np.arange(start,start+202*86400,86400)
        close=np.r_[np.linspace(100.,101.,200),104.,50.]
        f={'t':clock,'complete':clock+86400,'c':close,'h':close+.1,'l':close-.1,'o':close,'atr':np.ones(202)}
        m=SimpleNamespace(spec={'swap_long':1.,'swap_short':-3.})
        out,_=signals('EURUSD',f,m)
        self.assertTrue(any(t.family==TREND and t.decision==clock[201] for t in out))
        f['c'][-1]=500.
        changed,_=signals('EURUSD',f,m)
        self.assertEqual(out,changed)


class WinnerDiagnosisTests(unittest.TestCase):
    def test_five_labels_and_missing_higher_priority_have_no_overlap(self):
        base=dict(net_R=.8,swap_R=0.,mfe_R=1.2,mae_R=.4,holding_hours=4,calendar_exit=False,paired_net_R=None)
        self.assertEqual(classify(base),LABELS[3])
        self.assertEqual(classify(base|{'calendar_exit':True}),UNKNOWN)
        self.assertEqual(classify(base|{'calendar_exit':True,'paired_net_R':1.5,'swap_R':.5}),LABELS[0])
        self.assertEqual(classify(base|{'swap_R':.3,'mfe_R':None}),LABELS[1])
        self.assertEqual(classify(base|{'net_R':2.5,'mfe_R':4.,'holding_hours':73}),LABELS[2])
        self.assertEqual(classify(base|{'mfe_R':.9}),LABELS[4])
        self.assertIsNone(classify(base|{'net_R':0.}))

    def test_future_features_post_fields_and_holdout_fail_closed(self):
        t=stamp('2022-01-02')
        def record(features):
            return classify_trade('key',t,t,t+7200,'EURUSD',features,.5,0.,1.,.2,1.,.5,source='TEST')
        with self.assertRaisesRegex(ValueError,'known at entry'):
            record({'known_at':t+1,'trend':'UP'})
        with self.assertRaisesRegex(ValueError,'post-entry'):
            record({'known_at':t,'capture_efficiency':.5})
        with self.assertRaisesRegex(ValueError,'outside Development'):
            dev_scope(STOP-3, STOP-2, STOP)

    def test_base_rates_include_losers_and_top_concentration_uses_winner_pool(self):
        t=stamp('2022-01-02')
        cohort=[classify_trade(str(i),t,t,t+7200,'EURUSD',{'known_at':t,'trend':'UP'},
                net,0.,max(1.,net),.2,1.,net,source='TEST') for i,net in enumerate((.6,.7,.9,-1.))]
        report=breakdown(cohort)
        rate=report['entry_base_rates']['trend']['UP']
        self.assertEqual((rate['n'],rate['winrate'],rate['lossrate']),(4,.75,.25))
        self.assertAlmostEqual(report['top']['top2']['profit_share'],1.6/2.2)
        self.assertAlmostEqual(report['top']['top2']['net_R_excluding'],-.4)
