from datetime import date, timedelta
from unittest import TestCase

import pass10_institutional_flow as flow
import pass5_usdjpy_tokyo as tokyo
from quant_core.ftmo_track_replay import profiles


class Pass10Tests(TestCase):
    def test_london_uses_dst_and_values_separate_rollover_safe_horizons(self):
        day = date(2024, 3, 18)  # US DST has started, European DST has not.
        start = flow.epoch(day, 8, tokyo.LONDON)
        self.assertEqual(tokyo.date(start).hour, 8)
        self.assertEqual(tokyo.date(flow.epoch(date(2024, 7, 1), 8, tokyo.LONDON)).hour, 7)
        box = tokyo.Bar(1.100, 1.101, 1.099, 1.100)
        neutral = tokyo.Bar(1.100, 1.1005, 1.0995, 1.100)
        hourly = {start + i * 3600: neutral for i in range(14)}
        hourly[start] = box
        hourly[start + 4 * 3600] = tokyo.Bar(1.102, 1.103, 1.101, 1.102)
        hourly[start + 9 * 3600] = tokyo.Bar(1.103, 1.103, 1.103, 1.103)
        result, event = flow.london_day(day, hourly, tokyo.Costs(.001, 5, 100000))
        self.assertEqual(result, "first_touch")
        self.assertEqual(event["side"], 1)
        self.assertEqual(event["missing"], {"8h": "rollover_or_cutoff"})
        self.assertAlmostEqual(event["marks"]["hard_flat"]["Breakout"]["net"], 90)
        result = flow.orb_summary([event], "hard_flat")
        self.assertAlmostEqual(result["scale"]["friction_over_box_pct"], 5)

    def test_london_discards_dual_touch_without_peeking_at_later_bar(self):
        day = date(2024, 1, 2)
        start = flow.epoch(day, 8, tokyo.LONDON)
        bar = tokyo.Bar(1.100, 1.101, 1.099, 1.100)
        wide = tokyo.Bar(1.100, 1.102, 1.098, 1.101)
        self.assertEqual(flow.london_day(day, {start: bar, start + 3600: wide},
                                        tokyo.Costs(.001, 5, 100000)),
                         ("ambiguous_first_touch", None))
        self.assertEqual(flow.london_day(day, {start: bar, start + 7200: wide},
                                        tokyo.Costs(.001, 5, 100000)),
                         ("missing_activation", None))

    def test_tom_uses_friday_triple_and_standard_closes_before_charge(self):
        start = date(2024, 5, 31)
        days = [start, *(start + timedelta(days=i) for i in (3, 4, 5))]
        bar = tokyo.Bar(5000, 5020, 4990, 5010)
        records = dict.fromkeys(days, bar)
        specs, _ = profiles()
        indexes = [specs[x][flow.INDEX] for x in ("Swing", "Standard")]
        swing = flow.tom_event(days, records, {start: 14}, indexes[0], False)
        standard = flow.tom_event(days, records, {start: 14}, indexes[1], True)
        self.assertEqual(swing["triple_rollovers"], 1)
        self.assertAlmostEqual(swing["swap"], -1.3803 * 5)
        self.assertAlmostEqual(swing["net"], 10 - .60 - 1.50 - 1.3803 * 5)
        self.assertEqual(standard["exit_day"], start.isoformat())
        self.assertEqual(standard["swap"], 0)
        self.assertEqual(standard["held_sessions"], 1)
        self.assertIsNone(flow.tom_event(days, {start: bar}, {}, indexes[0], False))

    def test_month_dates_and_control_use_calendar_not_price_presence(self):
        days, _ = flow.calendars()
        tom, rest = flow.month_windows(days)
        self.assertEqual(len(tom), 83)
        self.assertEqual([d.isoformat() for d in tom[0]],
                         ["2018-01-31", "2018-02-01", "2018-02-02", "2018-02-05"])
        tom_days = {d for window in tom for d in window}
        self.assertTrue(all(tom_days.isdisjoint(window) for window in rest))
        self.assertTrue(all(window[-1].year < 2025 for window in tom))

    def test_standard_flattens_at_last_cash_session_if_friday_is_a_holiday(self):
        days = [date(2021, 4, 1), date(2021, 4, 5), date(2021, 4, 6), date(2021, 4, 7)]
        daily = dict.fromkeys(days, tokyo.Bar(4000, 4030, 3990, 4020))
        spec = profiles()[0]["Standard"][flow.INDEX]
        trade = flow.tom_event(days, daily, {}, spec, True)
        self.assertEqual(trade["exit_day"], "2021-04-01")
        self.assertTrue(trade["friday_clamped"])
        self.assertEqual(trade["triple_rollovers"], 0)
        self.assertEqual(trade["swap"], 0)

    def test_drawdown_duration_includes_recovery_and_excludes_idle_at_peak(self):
        def rows(net_by_day):
            return [{"day": f"2024-01-{d:02d}", "net": n} for d, n in net_by_day]
        no_drawdown = flow.curve(rows([(1, 2), (4, 0), (10, 3)]), "net")
        self.assertEqual(no_drawdown["max_underwater_days"], 0)
        recovered = flow.curve(rows([(1, 2), (4, -1), (10, 1)]), "net")
        self.assertEqual((recovered["max_dd_usd"], recovered["max_underwater_days"]), (1, 9))
        censored = flow.curve(rows([(1, 2), (4, -1), (10, 0)]), "net")
        self.assertEqual(censored["max_underwater_days"], 9)
