from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_v8_common import START, DEV_END, BACK_START, BACK_END, HOUR, DAY, stamp
from prop_v8_source import Calendar, Prices, cache_bars
from prop_v8_signals import contexts, normalize, realize
from prop_v8_campaign import gates, temporary_bindings, SystemAccount
from prop_v8_review import Oracle
from prop_campaign_source import DTYPE
from test_prop_v7 import Reader
from test_prop_v5 import trade, quote


class V8Tests(unittest.TestCase):
    def test_target_metals_normal_dec31_overrides_federal_holiday_proxy_only(self):
        from prop_v8_calendar_correction import corrected_data
        from prop_v8_common import CALENDAR, read
        old = {r["day"]:r for r in read(CALENDAR)["events"]}
        new = {r["day"]:r for r in corrected_data()["events"]}
        self.assertEqual(new["2021-12-31"]["flat_utc"],"16:58")
        self.assertNotEqual(new["2021-12-31"]["kind"],"CLOSED")
        self.assertEqual({k:v for k,v in old.items() if k!="2021-12-31"},
                         {k:v for k,v in new.items() if k!="2021-12-31"})

    def test_registration_creates_its_private_directory(self):
        import prop_v8_common as common
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "new-job"
            with patch.object(common, "JOB", target), patch.object(common, "pins", return_value=[]):
                common.register()
                self.assertTrue((target / "registration.json").exists())

    def test_backward_price_access_blocked_before_release(self):
        with self.assertRaisesRegex(ValueError, "backward_prices_locked"):
            cache_bars(BACK_START, BACK_END)

    def test_validation_price_access_blocked_during_design(self):
        with self.assertRaisesRegex(ValueError, "development_fence"):
            cache_bars(START, DEV_END + DAY)

    def test_prior_twenty_asian_days_do_not_include_current_day(self):
        hours = [[START + d * DAY + j * HOUR, 100, 100 + d + 1, 100, 100, 60]
                 for d in range(21) for j in range(6)]
        a = contexts(hours, START)
        self.assertIsNone(a[START + 19 * DAY]["ratio"])
        self.assertAlmostEqual(a[START + 20 * DAY]["ratio"], 21 / 10.5)
        changed = [r[:] for r in hours]
        for r in changed[-6:]:
            r[2] += 1000
        b = contexts(changed, START)
        self.assertEqual(a[START + 19 * DAY], b[START + 19 * DAY])

    def test_structural_stop_has_expected_side_and_atr_buffer(self):
        for side, stop, expected in (("BUY", 1800000, 1999500), ("SELL", 2200000, 2010500)):
            row = dict(side=side, stop_units=stop, decision_msc=START + 10 * HOUR, day="2022-01-01",
                       bar_units=[2000000,2010000,2000000,2005000], atr_h1_before_units="5000")
            out, _ = normalize([row], {}, "N2", 2)
            self.assertEqual(out[0]["stop_units"], expected)

    def test_stop_is_never_replaced_by_farther_h1_structure(self):
        row = dict(side="BUY", stop_units=2001000, decision_msc=START, day="2022-01-01",
                   bar_units=[2000000,2010000,2000000,2005000], atr_h1_before_units="5000")
        out, _ = normalize([row], {}, "N2", 2)
        self.assertEqual(out[0]["stop_units"], 2001000)

    def test_compression_filter_abstains_without_prior_context(self):
        row = dict(side="BUY", decision_msc=START, day="2022-01-01")
        out, rejects = normalize([row], {}, "N1", 2)
        self.assertFalse(out)
        self.assertEqual(rejects[0]["reason"], "COMPRESSION_OR_CONTEXT")

    def test_five_ounce_floor_bounds_rounding_error_at_all_budgets(self):
        for width in (6.3, 12.1, 24.99, 25):
            for budget in (125,150,200):
                q = int(budget // width)
                self.assertGreaterEqual(q, 5)
                self.assertLess(1 - q * width / budget, .20)

    def test_backward_calendar_generates_friday_and_holiday_deadlines(self):
        first, end = stamp("2020-11-01"), stamp("2020-12-01")
        data = dict(events=[dict(day="2020-11-26", kind="EARLY", flat_utc="16:58")])
        c = Calendar(data, first, end)
        self.assertEqual(c.deadline(stamp("2020-11-25T10:00"))[0], stamp("2020-11-26T16:58"))
        self.assertEqual(c.deadline(stamp("2020-11-20T10:00"))[0], stamp("2020-11-20T20:30"))

    def test_registration_gates_do_not_pick_profit_with_failed_retention(self):
        row = dict(year=2022, model="SYM", endpoint_coverage_pct=100, admitted=23, retained_pct=45,
                   raw=51, cost_rejected=28, scale_ratio=.16,
                   budgets={str(r):dict(net_R=10,mean_R=.4) for r in (125,150,200)})
        self.assertFalse(gates([row],False)["eligible"])

    def test_runner_bindings_restore_after_failure(self):
        module = SimpleNamespace(event="old")
        with self.assertRaises(ValueError):
            with temporary_bindings(module, dict(event="new")):
                self.assertEqual(module.event,"new")
                raise ValueError()
        self.assertEqual(module.event,"old")

    def test_account_and_oracle_agree_on_system_admission(self):
        at = START + 8 * HOUR
        t = dict(trade(at), v8_systems=["NORMALIZED"])
        a = SystemAccount(START, DEV_END, "SYM_FLAT", rolling=True, policy="GOLD_V4")
        a.v8_system = "BASELINE"
        a._trades = [t]
        a.action("entry",at,0,[t],quote(at))
        e = dict(a.dump(),v8_system="BASELINE")
        o = Oracle(e,[t])
        o.entry(0,at,quote(at))
        self.assertFalse(o.open)
        self.assertTrue(o.finish()["cash_bridge"])

    def test_quote_reader_checks_boundaries_before_opening_price_file(self):
        p = Prices({}, START, DEV_END)
        with self.assertRaisesRegex(ValueError,"price_fence"):
            p.hour(BACK_START)
        with self.assertRaisesRegex(ValueError,"path_fence"):
            p.path(BACK_START,START)


if __name__ == "__main__":
    unittest.main()
