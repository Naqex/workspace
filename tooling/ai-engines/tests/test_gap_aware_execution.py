from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_sl_active_kernel import fixture
from prop_campaign_source import stamp
from quant_core.ftmo_execution_and_calendar import SessionSchedule, execution_schedule
from quant_core.gap_aware_execution import GapAwarePathIndex, replay_gap_aware
import independent_ledger_auditor as oracle


class GapAwareTests(unittest.TestCase):
    def run_case(self, bars, m, mode="P0", events=()):
        index = GapAwarePathIndex(bars, asset="XAUUSD", schedule=SessionSchedule(events))
        result = replay_gap_aware(index, m, mode)
        i = 0
        trade = dict(symbol="XAUUSD", direction="BUY" if m["side"][i] == 1 else "SELL",
            entry_time=int(m["entry_at"][i]), entry_price=str(m["entry_price"][i]/1000),
            sl_price=str(m["stop"][i]/1000), exit_time=int(result["exit_at"][i]),
            exit_price=str(result["exit_price"][i]/1000), lots="1",
            reason=str(result["reason"][i]), mode=mode, horizon="24H",
            scheduled_deadline=int(result["scheduled_deadline"][i]),
            effective_deadline=int(result["effective_deadline"][i]),
            source_uncertain=bool(result["source_uncertain"][i]))
        spec = dict(contract=100, scale=1000, step=60000, gap_policy="V13_NEXT_QUOTE",
                    session_events={r["day"]:r for r in events})
        flats = [int(m["deadline"][i])] + [stamp(r["day"]+"T"+r["flat_utc"])
                                         for r in events if r.get("flat_utc")]
        audited = oracle.audit_trade(trade, (bars["t"], bars), spec, flats)
        self.assertTrue(audited["passed"], audited)
        return result, trade, spec

    def test_unknown_gap_is_priced_but_never_relabelled_verified(self):
        b, m = fixture([(100,101,99,100)]*3)
        b["t"][1:] += 120000
        m["deadline"] = b["t"][-1:]
        r, _, _ = self.run_case(b, m)
        self.assertTrue(r["valid"][0])
        self.assertTrue(r["source_uncertain"][0])
        self.assertEqual(r["evidence"][0], "DECLARED_NEXT_QUOTE_SCENARIO")

    def test_long_gap_through_stop_fills_adverse_open_immediately(self):
        b,m=fixture([(100,101,99,100),(87,91,85,88),(88,89,87,88)])
        b["t"][1:] += 60000;m["deadline"]=b["t"][-1:]
        r,_,_=self.run_case(b,m)
        self.assertEqual(r["exit_price"][0],87000)
        self.assertEqual(r["exit_at"][0],b["t"][1])
        self.assertLess(r["model"]["SYM"]["net_R"][0],-1)

    def test_short_gap_through_stop_uses_ask_open(self):
        b,m=fixture([(100,101,99,100),(115,118,112,116),(116,117,115,116)])
        b["t"][1:] += 60000;m["deadline"]=b["t"][-1:]
        m.update(side=np.array([-1]),entry_price=np.array([100000]),
                 stop=np.array([110000]),natural=np.array([10.]))
        r,_,_=self.run_case(b,m)
        self.assertEqual(r["exit_price"][0],115100)
        self.assertEqual(r["exit_at"][0],b["t"][1])

    def test_missing_horizon_defers_forward_without_hindsight_previous_close(self):
        b,m=fixture([(100,101,99,100),(104,105,103,104),(105,106,104,105)])
        b["t"][1:] += 180000
        r,_,_=self.run_case(b,m)
        self.assertEqual(r["exit_at"][0],b["t"][1])
        self.assertEqual(r["exit_price"][0],104000)
        self.assertTrue(r["deferred_endpoint"][0])

    def test_deferred_horizon_open_checks_stop_before_time_close(self):
        b,m=fixture([(100,101,99,100),(87,91,85,88),(88,89,87,88)])
        b["t"][1:] += 180000
        r,_,_=self.run_case(b,m)
        self.assertEqual(r["reason"][0],"SL")
        self.assertTrue(r["endpoint_open_stop"][0])

    def test_endpoint_future_extremes_cannot_create_stop_or_tp(self):
        b,m=fixture([(100,101,99,100),(102,180,50,120),(120,121,119,120)])
        m["deadline"]=b["t"][1:2]
        r,_,_=self.run_case(b,m,"P2")
        self.assertEqual(r["reason"][0],"HORIZON")
        self.assertEqual(r["exit_price"][0],102000)

    def test_P1_protection_survives_gap_and_gap_loss_can_exceed_floor(self):
        b,m=fixture([(100,120,99,118),(100,102,98,100),(100,101,99,100)])
        b["t"][1:] += 60000;m["deadline"]=b["t"][-1:]
        r,_,_=self.run_case(b,m,"P1")
        self.assertEqual(r["reason"][0],"PROTECT")
        self.assertEqual(r["exit_price"][0],100000)
        self.assertLess(r["model"]["SYM"]["net_R"][0],.15)

    def test_daily_break_deferral_charges_crossed_rollover(self):
        b,m=fixture([(100,101,99,100)]*3)
        b["t"]=np.array([stamp("2023-01-09T21:59"),stamp("2023-01-09T23:00"),
                         stamp("2023-01-09T23:01")])
        m.update(at=b["t"][:1],entry_at=b["t"][:1],deadline=np.array([stamp("2023-01-09T22:10")]))
        r,_,_=self.run_case(b,m)
        self.assertEqual(r["scheduled_deadline"][0],stamp("2023-01-09T23:00"))
        self.assertFalse(r["source_uncertain"][0])
        self.assertAlmostEqual(r["model"]["SYM"]["funding"][0],-.4)

    def test_FX_has_no_metals_daily_maintenance_break(self):
        s=SessionSchedule([])
        self.assertEqual(s.off_kind(stamp("2023-01-09T22:15"),"XAUUSD"),"DAILY_BREAK")
        self.assertIsNone(s.off_kind(stamp("2023-01-09T22:15"),"EURUSD"))

    def test_early_guard_clamp_is_predetermined_not_last_observed_quote(self):
        event=dict(day="2023-03-06",kind="DECLARED_METALS_EARLY_GUARD",flat_utc="10:01")
        b,m=fixture([(100,101,99,100)]*4)
        r,_,_=self.run_case(b,m,events=[event])
        self.assertEqual(r["exit_at"][0],b["t"][1])

    def test_oracle_detects_erased_source_uncertainty(self):
        b,m=fixture([(100,101,99,100)]*3)
        b["t"][1:]+=60000;m["deadline"]=b["t"][-1:]
        r,t,spec=self.run_case(b,m)
        t["source_uncertain"]=False
        a=oracle.audit_trade(t,(b["t"],b),spec,[int(m["deadline"][0])])
        self.assertIn("SOURCE_UNCERTAINTY_LABEL",a["errors"])

    def test_calendar_keeps_verified_2021_normal_hours_and_conservative_guard(self):
        s=execution_schedule(stamp("2018-01-01"),stamp("2024-01-01"))
        row=s.events["2021-12-31"]
        self.assertNotEqual(row["kind"],"CLOSED")
        self.assertEqual(row["flat_utc"],"16:58")
        self.assertIn("VERIFIED_FTMO_NORMAL",row["target_time_status"])


if __name__ == "__main__":
    unittest.main()
