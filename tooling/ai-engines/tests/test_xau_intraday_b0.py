from datetime import datetime,timezone
from decimal import Decimal as D,ROUND_HALF_UP
from pathlib import Path
import sys
import unittest
import json
import tempfile
from array import array

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import xau_intraday_b0 as b0
from xau_intraday_source import signal,HOUR,source_views,RAW_SHA,END
from eurusd_b0_source import digest

ROOT=Path(__file__).resolve().parents[3]
b0.bind_native(ROOT/'projects/trader/foundation_v2')
AT=int(datetime(2022,1,4,9,15,tzinfo=timezone.utc).timestamp()*1000)


def candidate(at=AT,side='BUY',stop=1985000):
    return dict(day='2022-01-04',decision_msc=at,side=side,stop_units=stop)


class XauTests(unittest.TestCase):
    def test_source_correction_is_bound_to_original_and_observed_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=[2000000,2000150,2000000,2000100]
            (root/'times.bin').write_bytes(array('q',[AT//1000]).tobytes())
            for name,value in zip(('o','h','l','c'),original):
                (root/(name+'.bin')).write_bytes(array('i',[value]).tobytes())
            files={p.name:digest(p) for p in root.glob('*.bin')}
            (root/'manifest.json').write_text(json.dumps(dict(raw_sha256=RAW_SHA,scope_end_exclusive=END//1000,rows=1,files=files,byteorder=sys.byteorder)))
            raw=dict(timestamp=AT//HOUR*HOUR,multiplier=.001,bid=2000,ask=2000.3,
                times=[AT%HOUR,1000],bids=[0,100],asks=[0,100],bidVolumes=[0,0],askVolumes=[0,0])
            raw_path=root/'raw.json';raw_path.write_text(json.dumps(raw))
            patch=dict(at=AT,original=original,corrected=[2000000,2000100,2000000,2000100],raw_path=str(raw_path),raw_sha256=digest(raw_path))
            packet=dict(schema='XAU-A0-observed-tick-M1-corrections-v1',patches=[patch])
            correction=root/'corrections.json';correction.write_text(json.dumps(packet))
            minutes,_=source_views(root,correction)
            self.assertEqual(minutes[AT],patch['corrected'])
            patch['corrected'][1]+=1;correction.write_text(json.dumps(packet))
            with self.assertRaisesRegex(ValueError,'correction_not_native_observed_ohlc'):source_views(root,correction)
            patch['at']=END;correction.write_text(json.dumps(packet))
            with self.assertRaisesRegex(ValueError,'correction_clock_or_holdout'):source_views(root,correction)

    def test_commission_matches_independent_decimal_per_leg(self):
        for units in (1234567,2000000,2060371):
            for steps in (1,7,19,100):
                expected=(D(units)/1000*100*D(steps)/100*D('.000007')).quantize(D('.01'),rounding=ROUND_HALF_UP)
                self.assertEqual(b0.commission_cents(units,steps),int(expected*100))
        self.assertEqual(b0.commission_cents(2000000,100),140)
        self.assertEqual(b0.round_div(-5,10),-1)

    def test_natural_stop_not_widened_to_pass_friction(self):
        c=candidate(stop=1999000)
        row=b0.admission(c,2000000,2000300)
        self.assertEqual(row['status'],'friction_cap_rejected')
        self.assertEqual(row['stop_units'],1999000)

    def test_sizing_reserves_both_cost_legs_and_grid(self):
        row=b0.admission(candidate(),2000000,2000300)
        self.assertEqual(row['status'],'cost_admitted')
        self.assertLessEqual(row['planned_stress_risk_usd'],150)
        self.assertLessEqual(row['planned_stress_friction_r0'],.12)
        self.assertEqual(row['take_units']-row['entry_units'],2*(row['entry_units']-row['stop_units']))

    def test_two_entries_cap_counter_keeps_third_raw_signal(self):
        cs=[candidate(AT+i*45*60000) for i in range(3)]
        qs=[]
        for c in cs:qs.extend([(c['decision_msc'],2000000,2000300),(c['decision_msc']+1000,2031000,2031300)])
        accounts={s:b0.Account() for s in ('reference','stress')}
        d=b0.run_day('2022-01-04',cs,qs,accounts)
        self.assertEqual(d['counters']['raw_signals'],3)
        self.assertEqual(d['counters']['cost_admitted'],3)
        self.assertEqual(d['counters']['filled_entries'],2)
        self.assertEqual(d['counters']['daily_cap_rejected'],1)
        self.assertTrue(all(t['exit_reason']=='TP_2R' for t in d['trades']))

    def test_same_ms_tick_order_and_stop_gap(self):
        qs=[(AT,2000000,2000300),(AT,1984000,1984300),(AT,2031000,2031300)]
        a={s:b0.Account() for s in ('reference','stress')}
        d=b0.run_day('2022-01-04',[candidate()],qs,a)
        self.assertEqual(d['trades'][0]['exit_reason'],'SL')
        self.assertEqual(d['trades'][0]['exit_units'],1984000)
        self.assertEqual(d['trades'][0]['exit_ordinal'],1)

    def test_time_stop_has_observed_quote_and_no_forced_flat(self):
        qs=[(AT+i*60000,2000000,2000300) for i in range(121)]
        a={s:b0.Account() for s in ('reference','stress')}
        d=b0.run_day('2022-01-04',[candidate()],qs,a)
        self.assertEqual(d['trades'][0]['exit_reason'],'TIME_STOP_2H')
        self.assertEqual(d['trades'][0]['holding_minutes'],120)
        a={s:b0.Account() for s in ('reference','stress')}
        d=b0.run_day('2022-01-04',[candidate()],qs[:2],a)
        self.assertIsNotNone(d['unresolved_position'])

    def test_sell_geometry_and_account_cash_bridge(self):
        c=candidate(side='SELL',stop=2015000)
        a={s:b0.Account() for s in ('reference','stress')}
        d=b0.run_day('2022-01-04',[c],[(AT,2000000,2000300),(AT+1000,1969000,1969300)],a)
        t=d['trades'][0]
        self.assertEqual(t['exit_reason'],'TP_2R')
        for s in a:
            v=t['results'][s]
            self.assertAlmostEqual(v['gross_after_spread_usd']-v['commission_usd']-v['slippage_usd'],v['conditional_net_usd'])
            self.assertEqual(a[s].cash,b0.INITIAL+round(v['conditional_net_usd']*100))
        self.assertLess(t['results']['stress']['conditional_net_usd'],t['results']['reference']['conditional_net_usd'])

    def test_signal_uses_locked_prior_zone_and_no_body_filter(self):
        f=dict(bar=[AT-900000,2000400,2000500,1999900,2000300,15],bias='BUY',atr_before=D(1000),
               ma_before=D(2000000),previous_close=D(2000400))
        self.assertIsNotNone(signal(f,AT))  # red candle, still closes beyond zone
        f['previous_close']=D(2000100)
        self.assertIsNone(signal(f,AT))

    def test_midnight_and_1600_not_admitted(self):
        f=dict(bar=[0,2000400,2000500,1999900,2000300,15],bias='BUY',atr_before=D(1000),
               ma_before=D(2000000),previous_close=D(2000400))
        for offset in (0,16*HOUR):
            at=AT//86400000*86400000+offset;f['bar'][0]=at-900000
            self.assertIsNone(signal(f,at))

    def test_entry_quote_wait_limit_and_open_position_rejection(self):
        a={s:b0.Account() for s in ('reference','stress')}
        d=b0.run_day('2022-01-04',[candidate()],[(AT+60001,2000000,2000300)],a)
        self.assertEqual(d['counters']['entry_quote_unavailable'],1)
        cs=[candidate(),candidate(AT+15*60000)]
        qs=[(AT+i*60000,2000000,2000300) for i in range(121)]
        d=b0.run_day('2022-01-04',cs,qs,{s:b0.Account() for s in ('reference','stress')})
        self.assertEqual(d['counters']['position_active_rejected'],1)


if __name__=='__main__':unittest.main()
