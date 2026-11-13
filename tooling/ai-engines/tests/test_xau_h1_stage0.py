from array import array
from datetime import datetime,timezone
from decimal import Decimal as D
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eurusd_b0_source import digest
from xau_intraday_source import source_views,RAW_SHA,END as CACHE_END
from xau_h1_stage0_source import mechanisms,signal_features,HOUR,END
from xau_h1_stage0_scan import funding_events,economics,entry_geometry,quote_at,verdict


def stamp(text):return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()*1000)


class H1Stage0Tests(unittest.TestCase):
    def test_narrow_source_never_decodes_synthetic_2024_price(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            (p/'times.bin').write_bytes(array('q',[END//1000-60,END//1000]).tobytes())
            for name,value in zip(('o','h','l','c'),(2000000,2001000,1999000,2000500)):
                (p/(name+'.bin')).write_bytes(array('i',[value,-999]).tobytes())
            manifest=dict(raw_sha256=RAW_SHA,scope_end_exclusive=CACHE_END//1000,rows=2,
                byteorder=sys.byteorder,files={name:digest(p/name) for name in ('times.bin','o.bin','h.bin','l.bin','c.bin')})
            (p/'manifest.json').write_text(json.dumps(manifest))
            minutes,views=source_views(p,end_msc=END)
            self.assertEqual(list(minutes),[END-60000])
            self.assertEqual(minutes[END-60000],[2000000,2001000,1999000,2000500])
            with self.assertRaisesRegex(ValueError,'XAU_source_scope_or_holdout'):source_views(p,end_msc=CACHE_END+1)

    def test_h4_bias_is_causal_under_future_bar_mutation(self):
        start=stamp('2021-11-01T00:00:00')
        rows=[[start+i*HOUR,2000000+i*1000,2002000+i*1000,1999000+i*1000,2001000+i*1000,60] for i in range(120)]
        before=signal_features(rows[:112]);after=signal_features(rows[:112]+[[r[0],1500000,1600000,1400000,1450000,60] for r in rows[112:]])
        self.assertEqual(before,after[:112])
        self.assertEqual(before[-1]['bias'],'BUY')
        self.assertLessEqual(before[-1]['bias_at'],before[-1]['at'])

    def test_asian_stop_uses_opposite_range_not_a_fee_floor(self):
        f=dict(at=stamp('2022-01-04T09:00:00'),bar=[0,1999000,2006000,1998000,2005000,60],
            previous=[-HOUR,1997000,2000000,1995000,1995000,60],atr_before=D(10000),ma_before=D(1999000),
            bias='BUY',bias_at=0,recent=[])
        result=next(r for r in mechanisms(f,(2000000,1980000)) if r['recipe']=='H1A_ASIA')
        self.assertEqual(result['stop_units'],1979000)

    def test_reclaim_uses_locked_ma_and_two_bar_structure(self):
        f=dict(at=stamp('2022-01-04T09:00:00'),bar=[0,1999500,2005000,1998000,2004000,60],
            previous=[-HOUR,2001000,2002000,1997000,1999000,60],atr_before=D(10000),ma_before=D(2000000),
            bias='BUY',bias_at=0,recent=[])
        r=mechanisms(f,None)
        self.assertEqual([x['recipe'] for x in r],['H1B_RECLAIM'])
        self.assertEqual(r[0]['stop_units'],1996000)

    def test_momentum_uses_three_adjacent_higher_lows(self):
        bars=[[-2*HOUR,1990000,2001000,1989000,1999000,60],[-HOUR,1999000,2002000,1990000,2000000,60],
              [0,2000000,2016000,1999000,2015000,60]]
        f=dict(at=stamp('2022-01-04T09:00:00'),bar=bars[-1],previous=bars[-2],atr_before=D(10000),ma_before=D(2000000),bias='BUY',bias_at=0,recent=bars)
        r=next(r for r in mechanisms(f,None) if r['recipe']=='H1C_MOMENTUM')
        self.assertEqual(r['stop_units'],1988000)
        f['recent'][0][3]=1991000
        self.assertNotIn('H1C_MOMENTUM',[r['recipe'] for r in mechanisms(f,None)])

    def test_wednesday_triple_and_rollover_endpoint_inclusion(self):
        events=funding_events(stamp('2022-01-04T21:00:00'),stamp('2022-01-05T23:00:00'))
        self.assertEqual([r['multiplier'] for r in events],[1,3])
        at=stamp('2022-01-05T22:00:00')
        self.assertEqual(funding_events(at,at),[])
        self.assertEqual(funding_events(at-1,at)[0]['multiplier'],3)

    def test_swap_proxy_has_no_saturday_sunday_events(self):
        events=funding_events(stamp('2022-01-07T21:00:00'),stamp('2022-01-09T23:00:00'))
        self.assertEqual([r['multiplier'] for r in events],[1])

    def test_buy_economics_spread_commission_slip_and_swap(self):
        a=stamp('2022-01-04T09:00:00');b=a+24*HOUR
        e=economics((a,2000000,2000300),(b,2005000,2005400),'BUY')
        self.assertAlmostEqual(e['signed_mid_move_usd_per_oz'],5.05)
        self.assertAlmostEqual(e['spread_usd_per_oz'],.35)
        self.assertAlmostEqual(e['gross_after_spread_usd_per_oz'],4.7)
        self.assertAlmostEqual(e['commission_usd_per_oz'],.0280371)
        self.assertEqual(e['rollover_units'],1)
        self.assertAlmostEqual(e['stress_net_usd_per_oz'],3.8719629)

    def test_sell_and_short_horizon_zero_funding(self):
        a=stamp('2022-01-04T09:00:00');b=a+4*HOUR
        e=economics((a,2000000,2000300),(b,1995000,1995400),'SELL')
        self.assertAlmostEqual(e['gross_after_spread_usd_per_oz'],4.6)
        self.assertEqual(e['stress_financing_usd_per_oz'],0)

    def test_geometry_never_widens_stop_to_pass_cost(self):
        s=dict(side='BUY',stop_units=1998300)
        g=entry_geometry(s,(0,2000000,2000300))
        self.assertEqual(g['natural_sl_usd_per_oz'],2)
        self.assertFalse(g['pass15']);self.assertEqual(s['stop_units'],1998300)

    def test_missing_and_new_year_quotes_are_not_carried(self):
        at=stamp('2023-12-29T09:00:00')
        self.assertIsNone(quote_at({at:[]},at,at)[0])
        self.assertEqual(quote_at({},END,END)[1],'outside_development')
        self.assertIsNone(quote_at({at:[(at+60001,1,2)]},at,at)[0])

    def test_stage0_gate_does_not_promote_positive_partial_mean(self):
        def year(y,net=1,missing=0):return dict(year=y,raw_signals=80,entry_quote_missing=0,invalid_stops=0,
            scale_ratio_of_medians=.1,fraction_pass12=.6,markouts=[dict(hours=8,missing=missing,stress_net=dict(mean=net),execution_friction=dict(mean=.75))])
        self.assertEqual(verdict([year(2022),year(2023)],8)['status'],'STAGE0_MODEL_SCREEN_PASS_NOT_EDGE')
        self.assertIn('ECONOMIC_2023',verdict([year(2022),year(2023,-.1)],8)['reasons'])
        self.assertIn('NET_SMALLER_THAN_FRICTION_2023',verdict([year(2022),year(2023,.5)],8)['reasons'])
        self.assertIn('PRIMARY_ENDPOINTS_MISSING_2023',verdict([year(2022),year(2023,2,1)],8)['reasons'])


if __name__=='__main__':unittest.main()
