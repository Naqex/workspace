import unittest
from prop_campaign_source import stamp
from prop_v16_paths import CausalFlatSchedule
from prop_v15_accounts import exact_quantity
from independent_ledger_auditor import audit_tick_continuity,v16_causal_cutoff


class V16SourceAndCausalityTests(unittest.TestCase):
    def test_gold_P1_short_protection_checks_previous_grid_after_commission_rounding(self):
        import numpy as np
        from quant_core.vectorized_sl_active_kernel import net_level
        level=net_level("XAUUSD",np.array([-1]),np.array([1880418]),np.array([12.598]),
            np.array([1604930400000]),np.array([1604933880000]),.15)
        self.assertEqual(int(level[0]),1878102)

    def test_v12_path_archive_does_not_require_old_endpoint_only_fields(self):
        import numpy as np
        from prop_v16_scan import measurement
        fields=("at","entry_at","side","entry_price","stop","natural","friction","ratio",
            "years","deadline","admitted")
        archive={"0:"+k:np.array([.1 if k=="ratio" else 1]) for k in fields}
        row=dict(source_cell=0,asset="XAUUSD",recipe="frozen",family="F1")
        self.assertTrue(measurement(archive,row)["admitted"][0])

    def test_nearby_endpoints_and_zero_ticks_do_not_prove_feed_continuity(self):
        r=audit_tick_continuity([(0,100,101),(180000,100,101)],60000,180000,1,80,{})
        self.assertEqual(r["status"],"RECORDED_ZERO_TICKS_CONTINUITY_UNKNOWN")
        self.assertFalse(r["market_or_broker_guarantee"])

    def test_recorded_quotes_without_stop_are_not_lossless_feed_proof(self):
        r=audit_tick_continuity([(60000,100,101)],0,120000,1,80,{})
        self.assertEqual(r["status"],"RECORDED_NO_SL_CONTINUITY_UNKNOWN")

    def test_feed_certificate_needs_sequence_and_interval_not_an_export_filename(self):
        p=dict(complete_interval=True,unfiltered_quotes=True,sequence_checked=True,
            missing_sequence_count=0,first=0,end=120000)
        r=audit_tick_continuity([],0,120000,1,80,p)
        self.assertEqual(r["status"],"TICK_VERIFIED_NO_SL_IN_DECLARED_FEED")
        p["missing_sequence_count"]=1
        self.assertFalse(audit_tick_continuity([],0,120000,1,80,p)["declared_feed_continuity"])
        p["missing_sequence_count"]=0;p["end"]=119999
        self.assertFalse(audit_tick_continuity([],0,120000,1,80,p)["declared_feed_continuity"])

    def test_short_stop_uses_ask_and_observed_hit_overrides_continuity(self):
        r=audit_tick_continuity([(0,100,110)],0,1,-1,105,{})
        self.assertEqual(r["status"],"RECORDED_SL_HIT")

    def test_bad_tick_order_and_crossed_quote_are_rejected(self):
        for q in ([(2,100,101),(1,100,101)],[(0,101,100)]):
            with self.assertRaises(ValueError):audit_tick_continuity(q,0,10,1,80,{})

    def test_daily_deadline_has_no_future_price_or_gap_argument(self):
        entry=stamp("2023-03-06T10:00")
        schedule=CausalFlatSchedule([])
        self.assertEqual(schedule.target(entry,entry+172800000,"XAUUSD"),stamp("2023-03-06T20:30"))
        self.assertEqual(schedule.target(entry,entry+3600000,"XAUUSD"),entry+3600000)

    def test_earlier_registered_holiday_close_wins(self):
        events=[dict(day="2023-11-24",flat_utc="17:30")]
        entry=stamp("2023-11-24T10:00")
        schedule=CausalFlatSchedule(events)
        self.assertEqual(schedule.target(entry,entry+172800000,"XAUUSD"),stamp("2023-11-24T17:30"))
        self.assertEqual(schedule.target(entry,entry+172800000,"XAUUSD"),
            v16_causal_cutoff(entry,entry+172800000,"XAUUSD",schedule.events))

    def test_us500_local_session_close_respects_DST(self):
        schedule=CausalFlatSchedule([])
        for date,expected in (("2023-03-06","21:00"),("2023-03-13","20:00")):
            at=stamp(date+"T10:00")
            want=min(stamp(date+"T20:30"),stamp(date+"T"+expected))
            self.assertEqual(schedule.target(at,at+172800000,"US500"),want)
            self.assertEqual(want,v16_causal_cutoff(at,at+172800000,"US500",{}))

    def test_close_request_is_known_before_an_unexpected_outage(self):
        at=stamp("2023-03-06T10:00")
        schedule=CausalFlatSchedule([])
        # An outage at 14:01 must not magically create a 14:00 close.
        self.assertNotEqual(schedule.target(at,at+172800000,"EURUSD"),stamp("2023-03-06T14:00"))

    def test_higher_gold_price_alone_does_not_reduce_stop_risk_quantity(self):
        low=dict(asset="XAUUSD",entry_price_units=1800000,stop_units=1790000)
        high=dict(asset="XAUUSD",entry_price_units=3000000,stop_units=2990000)
        self.assertEqual(exact_quantity(low,150),exact_quantity(high,150))
        high["stop_units"]=2980000
        self.assertLess(exact_quantity(high,150),exact_quantity(low,150))
