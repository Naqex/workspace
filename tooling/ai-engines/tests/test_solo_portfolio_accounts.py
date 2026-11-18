from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_campaign_source import DTYPE, START, END, FINAL, HOUR, stamp
from prop_portfolio_accounts import (
    ASSETS, THREE_ASSETS, JOINT, PortfolioAccount, QuoteAgeCoverage,
    S03_REPLAY_SCOPE, entry_exit_fee, joint_dtype, joint_hour, prague_midnights, replay,
)

MINUTE = 60000
RISK = {"XAUUSD": 150, "EURUSD": 75, "GBPUSD": 75}
AT = stamp("2023-06-20T08:00:00")


class Reader:
    cutoff = END

    def __init__(self, rows):
        self.rows = rows
        self.files = set(rows)

    def hour(self, at):
        return self.rows[at]


def record(asset="XAUUSD", **extra):
    gold = asset == "XAUUSD"
    value = dict(asset=asset, role="CORE" if gold else "SATELLITE",
        recipe="A" if gold else "SWEEP", side="BUY", day="2023-06-20",
        decision_msc=AT, entry_msc=AT, entry_quote_index=0,
        entry_price_units=2000000 if gold else 120010,
        stop_units=1990000 if gold else 119910,
        exit_msc=AT + HOUR, exit_quote_index=0,
        exit_price_units=2010000 if gold else 120110,
        deadline_msc=AT + HOUR, reason="DAY", signal_id=asset)
    value.update(extra)
    return value


def quote(at=AT):
    row = np.zeros(1, dtype=joint_dtype(THREE_ASSETS, True))[0]
    row["t"], row["event_asset"], row["event_ordinal"] = at, 2, 0
    for rank, pair in enumerate(((1999900, 2000000), (120000, 120010), (120000, 120010))):
        row[f"b{rank}"], row[f"a{rank}"] = pair
        row[f"quote_t{rank}"] = at
        row[f"quote_hour{rank}"] = at // HOUR * HOUR
        row[f"quote_ordinal{rank}"] = 0
    return row


def account(**extra):
    options = dict(assets=THREE_ASSETS, fixed_asset_risk=RISK, track_quote_age=True)
    options.update(extra)
    return PortfolioAccount(AT, AT + 2 * HOUR, "ASYM_FLAT", **options)


class JointSourceTests(unittest.TestCase):
    def test_three_asset_ties_have_scalar_merge_parity_and_provenance(self):
        readers = {
            "XAUUSD": Reader({0: np.array([(10, 100, 101), (20, 110, 111), (20, 120, 121)], dtype=DTYPE)}),
            "EURUSD": Reader({0: np.array([(10, 200, 201), (20, 210, 211), (20, 220, 221)], dtype=DTYPE)}),
            "GBPUSD": Reader({0: np.array([(10, 300, 301), (20, 310, 311)], dtype=DTYPE)}),
        }
        rows, maps = joint_hour(readers, 0, None, assets=THREE_ASSETS, provenance=True)
        expected = sorted((int(t["t"]), rank, ordinal, int(t["b"]), int(t["a"]))
                          for rank, asset in enumerate(THREE_ASSETS)
                          for ordinal, t in enumerate(readers[asset].hour(0)))
        current = {}
        for got, (at, rank, ordinal, bid, ask) in zip(rows, expected):
            current[rank] = (at, ordinal, bid, ask)
            self.assertEqual((got["t"], got["event_asset"], got["event_ordinal"]), (at, rank, ordinal))
            for asset_rank in range(3):
                seen = current.get(asset_rank)
                self.assertEqual(got[f"b{asset_rank}"], seen[2] if seen else 0)
                self.assertEqual(got[f"quote_t{asset_rank}"], seen[0] if seen else -1)
                self.assertEqual(got[f"quote_ordinal{asset_rank}"], seen[1] if seen else -1)
        self.assertEqual([len(x) for x in maps], [3, 3, 2])
        empty = {asset: Reader({}) for asset in THREE_ASSETS}
        empty["XAUUSD"] = Reader({HOUR: np.array([(HOUR + 1, 130, 131)], dtype=DTYPE)})
        later, _ = joint_hour(empty, HOUR, rows[-1], assets=THREE_ASSETS, provenance=True)
        self.assertEqual(later[0]["quote_t1"], 20)
        self.assertEqual(later[0]["quote_ordinal1"], 2)

    def test_default_layout_and_prices_remain_two_asset(self):
        readers = {a: Reader({0: np.array([(10, 100, 101)], dtype=DTYPE)}) for a in ASSETS}
        legacy, _ = joint_hour(readers, 0, None)
        richer, _ = joint_hour(readers, 0, None, provenance=True)
        self.assertEqual(legacy.dtype, JOINT)
        for field in JOINT.names:
            np.testing.assert_array_equal(legacy[field], richer[field])

    def test_missing_future_and_same_ms_future_quote_are_rejected(self):
        a = account()
        for change in (
                {"quote_t2": -1}, {"quote_t2": AT + 1},
                {"quote_hour2": AT - HOUR}, {"quote_ordinal2": -1},
                {"event_asset": 1}, {"event_ordinal": 0, "quote_ordinal2": 1}):
            q = quote()
            for name, value in change.items():
                q[name] = value
            with self.assertRaisesRegex(ValueError, "provenance|future"):
                a.quote_provenance(AT, q, ["GBPUSD"])

    def test_final_prague_midnight_and_dst_spacing(self):
        values = list(prague_midnights(stamp("2023-12-30"), stamp("2024-01-01")))
        self.assertIn(stamp("2023-12-31T23:00:00"), values)
        spring = list(prague_midnights(stamp("2023-03-24"), stamp("2023-03-29")))
        autumn = list(prague_midnights(stamp("2023-10-27"), stamp("2023-11-01")))
        self.assertIn(23 * HOUR, np.diff(spring))
        self.assertIn(25 * HOUR, np.diff(autumn))

    def test_consumer_segments_are_clipped_to_account_time_window(self):
        class Capture(PortfolioAccount):
            def segment(self, rows, trades, cache):
                self.seen.extend(int(t) for t in rows["t"])
                super().segment(rows, trades, cache)
        a = Capture(AT + 5, AT + 15, "ASYM_FLAT")
        a.seen = []
        readers = {asset: Reader({}) for asset in ASSETS}
        readers["XAUUSD"] = Reader({AT: np.array(
            [(AT, 1999900, 2000000), (AT + 10, 2001000, 2001100),
             (AT + 20, 2010000, 2010100)], dtype=DTYPE)})
        trade = record(exit_msc=AT + 20, deadline_msc=AT + 20, exit_quote_index=2)
        replay([trade], readers, [a], end=AT + HOUR)
        self.assertEqual(a.seen, [AT + 10])


class FixedAccountTests(unittest.TestCase):
    def test_three_asset_replay_uses_shared_caps_money_and_accepted_coverage(self):
        end = AT + 20 * MINUTE
        readers = {}
        trades = []
        for rank, asset in enumerate(THREE_ASSETS):
            gold = asset == "XAUUSD"
            bid, ask = (1999900, 2000000) if gold else (120000, 120010)
            finish = 2010000 if gold else 120110
            readers[asset] = Reader({AT: np.array(
                [(AT + rank, bid, ask), (end + rank, finish, finish + (100 if gold else 10))],
                dtype=DTYPE)})
            trades.append(record(asset, decision_msc=AT + rank, entry_msc=AT + rank,
                exit_msc=end + rank, exit_quote_index=1, deadline_msc=end + rank,
                exit_price_units=finish))
        baseline = account(included_assets=ASSETS)
        candidate = account()
        old, new = replay(trades, readers, [baseline, candidate],
                          assets=THREE_ASSETS, end=AT + HOUR)
        self.assertEqual((old["entries"], new["entries"]), (2, 3))
        self.assertEqual(old["rejections"], {"ASSET_NOT_IN_SYSTEM": 1})
        self.assertEqual(old["quote_age_coverage"]["assets"]["GBPUSD"]["held_ms"], 0)
        self.assertEqual(new["quote_age_coverage"]["assets"]["GBPUSD"]["unknown_ms"], 5 * MINUTE)
        self.assertEqual(new["maximum_open_stop_risk_pct"], .6)
        self.assertTrue(new["cash_bridge_verified"])
        self.assertAlmostEqual(new["net_usd"] - old["net_usd"], 68.24)

    def test_fixed_risk_all_phases_without_equity_throttle(self):
        for phase in (1, 2, 3):
            a = account(rolling=True)
            a.phase = phase
            a.balance = a.anchor = a.peak = 47900000
            trades = [record("XAUUSD"), record("EURUSD"), record("GBPUSD")]
            for i in range(3):
                a.action("entry", AT, i, trades, quote())
            self.assertEqual([x["risk_usd"] for x in a.accepted], [150, 75, 75])

    def test_nonrolling_measures_losses_beyond_first_threshold(self):
        a = account()
        trade = record()
        a._trades = [trade]
        a.active = {0: (100, 150)}
        a.accrued = {0: 0}
        rows = np.array([quote(AT), quote(AT + 1), quote(AT + 2)], dtype=joint_dtype(THREE_ASSETS, True))
        rows["b0"] = [1999900, 1970000, 1940000]
        a.segment(rows, [trade], {})
        self.assertIsNone(a.breach)
        self.assertEqual(a.static, 6020000)
        self.assertEqual(a.float, -6020000)

    def test_breach_snapshot_is_exact_midsegment_and_open_fx_bridge(self):
        a = account(rolling=True)
        trade = record("GBPUSD")
        a._trades = [trade]
        a.active = {0: (100, 75)}
        a.accrued = {0: 0}
        a.balance -= entry_exit_fee(trade, trade["entry_price_units"], 100)
        a.accepted = [dict(trade=0, at=AT, quantity_steps=100, risk_usd=75)]
        rows = np.array([quote(AT), quote(AT + 1), quote(AT + 2)], dtype=joint_dtype(THREE_ASSETS, True))
        rows["b2"] = [120000, 117000, 110000]
        a.last_quote = quote(AT - 1)
        a.segment(rows, [trade], {})
        result = a.dump()
        self.assertEqual(result["first_breach"]["at"], AT + 1)
        self.assertEqual(result["breach_snapshot"]["quotes"]["GBPUSD"]["quote_msc"], AT + 1)
        self.assertEqual(result["breach_snapshot"]["quotes"]["GBPUSD"]["bid_units"], 117000)
        self.assertTrue(result["cash_bridge_verified"])
        self.assertFalse(result["breach_snapshot"]["liquidated"])
        self.assertEqual(result["closed_trades"], 0)
        before = result["breach_snapshot"]
        a.action("exit", AT + HOUR, 0, [trade], quote(AT + HOUR))
        self.assertEqual(a.dump()["breach_snapshot"], before)

    def test_baseline_exclusion_does_not_need_gbp_quote(self):
        a = account(included_assets=ASSETS)
        q = quote()
        q["quote_t2"] = -1
        q["b2"] = 0
        a.action("entry", AT, 0, [record("GBPUSD")], q)
        self.assertEqual(a.rejected["ASSET_NOT_IN_SYSTEM"], 1)
        self.assertEqual(a.rejection_records[0]["reason"], "ASSET_NOT_IN_SYSTEM")
        self.assertFalse(a.active)

    def test_common_r_is_cash_not_sum_of_trade_specific_r(self):
        a = account()
        a._trades = []
        a.closed = [dict(net_usd=150, net_R=1), dict(net_usd=75, net_R=1)]
        a.balance += 225000
        a.dd = 300000
        result = a.dump()
        self.assertEqual(result["net_R"], 2)
        self.assertEqual(result["portfolio_common_R"], 1.5)
        self.assertEqual(result["equity_DD_common_R"], 2)

    def test_empty_replay_and_closed_cutoff(self):
        readers = {asset: Reader({}) for asset in THREE_ASSETS}
        result = replay([], readers, [account()], assets=THREE_ASSETS, end=AT + HOUR)
        self.assertEqual(result[0]["quote_age_coverage"]["elapsed_held_ms"], 0)
        with self.assertRaisesRegex(ValueError, "Development_cutoff"):
            replay([], readers, [account()], assets=THREE_ASSETS, end=END + HOUR)
        with self.assertRaisesRegex(ValueError, "outside_replay_scope"):
            replay([record(exit_msc=AT + HOUR)], readers, [account()], assets=THREE_ASSETS, end=AT + HOUR)

    def test_missing_held_hour_fails_instead_of_carrying_quote(self):
        readers = {asset: Reader({}) for asset in THREE_ASSETS}
        readers["XAUUSD"] = Reader({
            AT: np.array([(AT, 1999900, 2000000)], dtype=DTYPE),
            AT + 2 * HOUR: np.array([(AT + 2 * HOUR, 2010000, 2010100)], dtype=DTYPE)})
        trade = record(exit_msc=AT + 2 * HOUR, deadline_msc=AT + 2 * HOUR)
        with self.assertRaisesRegex(ValueError, "held_asset_tick_hour_unadmitted"):
            replay([trade], readers, [account()], assets=THREE_ASSETS, end=AT + 3 * HOUR)

    def test_shared_cap_and_natural_reserve_ignore_future_exit(self):
        a = account()
        trades = [record("XAUUSD", decision_msc=AT + i, signal_id=str(i)) for i in range(4)]
        for i in range(4):
            a.action("entry", AT + i, i, trades, quote(AT + i))
        self.assertEqual(len(a.accepted), 3)
        self.assertEqual(a.rejection_records[0]["reason"], "OPEN_STOP_RISK_1PCT_CAP")
        t = record("GBPUSD")
        reserve = a.reserve_floor(trades + [t], 4, 75, 1880)
        changed = dict(t, exit_msc=AT + 999 * HOUR, exit_price_units=9999999)
        self.assertEqual(a.reserve_floor(trades + [changed], 4, 75, 1880), reserve)

    def test_midnight_reports_stale_gbp_despite_fresh_gold(self):
        a = account()
        trade = record("GBPUSD")
        a.action("entry", AT, 0, [trade], quote())
        q = quote(AT + 20 * MINUTE)
        q["quote_t2"], q["quote_hour2"] = AT, AT // HOUR * HOUR
        a.action("reset", AT + 20 * MINUTE, None, [trade], q)
        mark = a.stale_resets[-1]["assets"]["GBPUSD"]
        self.assertEqual(mark["age_ms"], 20 * MINUTE)
        self.assertEqual(a.anchor, a.balance)

    def test_phase_transition_blocks_same_time_signal_and_reward_bridge(self):
        a = account(rolling=True)
        a._trades = []
        a.balance = 55000000
        a.phase_days = {"1", "2", "3", "4"}
        a.check(AT, 0)
        self.assertEqual(a.phase, 2)
        a.action("entry", AT, 0, [record("GBPUSD")], quote())
        self.assertEqual(a.rejected["PRESTART_OR_PHASE_GATE"], 1)
        a.phase = 3
        a.funded_first = AT - 31 * 24 * HOUR
        a.balance = 50100000
        a.reward(AT + 1)
        self.assertEqual(a.balance, 50000000)
        self.assertEqual(a.payouts[-1]["gross_removed_usd"], 100)
        self.assertEqual(a.payouts[-1]["trader_usd"], 80)


class CoverageTests(unittest.TestCase):
    def coverage(self, held, next_at=20 * MINUTE, cap=25 * MINUTE):
        c = QuoteAgeCoverage(THREE_ASSETS)
        c.observe("GBPUSD", 0, np.array([(0, 100, 101), (next_at, 100, 101)], dtype=DTYPE))
        c.finish(cap)
        a = account()
        a.end = cap
        a.accepted = [dict(trade=i, at=start) for i, (start, _) in enumerate(held)]
        trades = [dict(asset="GBPUSD", exit_msc=end) for _, end in held]
        return c, a, trades

    def test_all_streams_quiet_then_fresh_does_not_erase_outage(self):
        c, a, trades = self.coverage([(0, 20 * MINUTE)])
        r = c.account(a, trades)
        gbp = r["assets"]["GBPUSD"]
        self.assertEqual((gbp["fresh_ms"], gbp["middle_ms"], gbp["unknown_ms"]),
                         (MINUTE, 14 * MINUTE, 5 * MINUTE))
        self.assertEqual(r["unknown_wall_fraction"], .25)
        self.assertFalse(r["path_complete"])

    def test_overlap_union_and_breach_clips_unknown(self):
        c, a, trades = self.coverage([(0, 10 * MINUTE), (5 * MINUTE, 20 * MINUTE)])
        self.assertEqual(c.account(a, trades)["elapsed_held_ms"], 20 * MINUTE)
        a.breach = {"at": 17 * MINUTE}
        result = c.account(a, trades)
        self.assertEqual(result["unknown_over_15min_ms"], 2 * MINUTE)
        self.assertEqual(result["assets"]["GBPUSD"]["unknown_intervals"][0]["end_msc"], 17 * MINUTE)

    def test_terminal_gap_and_late_entry(self):
        c = QuoteAgeCoverage(THREE_ASSETS)
        c.observe("GBPUSD", 0, np.array([(0, 100, 101)], dtype=DTYPE))
        c.finish(25 * MINUTE)
        a = account()
        a.end = 25 * MINUTE
        a.accepted = [dict(trade=0, at=10 * MINUTE)]
        result = c.account(a, [dict(asset="GBPUSD", exit_msc=25 * MINUTE)])
        gbp = result["assets"]["GBPUSD"]
        self.assertEqual((gbp["fresh_ms"], gbp["middle_ms"], gbp["unknown_ms"]),
                         (0, 5 * MINUTE, 10 * MINUTE))

    def test_same_ms_ordinals_do_not_add_duration(self):
        c = QuoteAgeCoverage(THREE_ASSETS)
        c.observe("GBPUSD", 0, np.array([(0, 100, 101), (0, 102, 103), (20 * MINUTE, 104, 105)], dtype=DTYPE))
        c.finish(20 * MINUTE)
        self.assertEqual(len(c.gaps["GBPUSD"]), 1)
        self.assertEqual(c.gaps["GBPUSD"][0]["source_ordinal"], 1)


class HistoricalValidationScopeTests(unittest.TestCase):
    def readers(self, rows=None, cutoff=FINAL):
        result = {asset: Reader((rows or {}).get(asset, {})) for asset in THREE_ASSETS}
        for reader in result.values():
            reader.cutoff = cutoff
            reader.calls = []
            original = reader.hour
            reader.hour = lambda at, r=reader, read=original: (r.calls.append(at), read(at))[1]
        return result

    def run_account(self, start=START, end=FINAL, **extra):
        return PortfolioAccount(start, end, "ASYM_FLAT", assets=THREE_ASSETS,
                                fixed_asset_risk=RISK, track_quote_age=True, **extra)

    def test_explicit_scope_accepts_2024_and_keeps_development_default(self):
        readers = self.readers()
        with self.assertRaisesRegex(ValueError, "Development_cutoff"):
            replay([], readers, [self.run_account()], end=FINAL, assets=THREE_ASSETS)
        result = replay([], readers, [self.run_account()], end=FINAL,
                        assets=THREE_ASSETS, replay_scope=S03_REPLAY_SCOPE)
        self.assertEqual(result[0]["entries"], 0)
        self.assertTrue(all(not r.calls for r in readers.values()))

    def test_scope_denials_precede_quote_reads(self):
        for mutation, message in (
            (lambda kw, rs, a: kw.update(replay_scope="S03"), "unregistered_replay_scope"),
            (lambda kw, rs, a: kw.update(end=FINAL + HOUR), "unregistered_replay_scope"),
            (lambda kw, rs, a: kw.update(end=END), "unregistered_replay_scope"),
            (lambda kw, rs, a: kw.update(end=True), "unregistered_replay_scope"),
            (lambda kw, rs, a: setattr(rs["GBPUSD"], "cutoff", END), "S03_reader_cutoff"),
            (lambda kw, rs, a: setattr(rs["GBPUSD"], "cutoff", FINAL + HOUR), "S03_reader_cutoff"),
            (lambda kw, rs, a: setattr(rs["GBPUSD"], "cutoff", None), "S03_reader_cutoff"),
            (lambda kw, rs, a: rs["GBPUSD"].files.add(FINAL), "S03_manifest_hour_scope"),
            (lambda kw, rs, a: rs["GBPUSD"].files.add(END + 1), "S03_manifest_hour_scope"),
            (lambda kw, rs, a: rs["GBPUSD"].files.add(START - HOUR), "S03_manifest_hour_scope"),
            (lambda kw, rs, a: setattr(a, "end", FINAL + HOUR), "S03_account_window"),
            (lambda kw, rs, a: setattr(a, "start", a.end), "S03_account_window"),
        ):
            with self.subTest(message=message):
                readers = self.readers()
                a = self.run_account()
                kwargs = dict(end=FINAL, assets=THREE_ASSETS, replay_scope=S03_REPLAY_SCOPE)
                mutation(kwargs, readers, a)
                with self.assertRaisesRegex(ValueError, message):
                    replay([], readers, [a], **kwargs)
                self.assertTrue(all(not r.calls for r in readers.values()))
        with self.assertRaisesRegex(ValueError, "unregistered_replay_scope"):
            replay([], {a: Reader({}) for a in ASSETS}, [],
                   end=FINAL, replay_scope=S03_REPLAY_SCOPE)

    def test_deadline_outside_closed_window_rejected_even_if_stop_earlier(self):
        readers = self.readers()
        trade = record(deadline_msc=FINAL - MINUTE)
        with self.assertRaisesRegex(ValueError, "S03_deadline_outside_scope"):
            replay([trade], readers, [self.run_account()], end=FINAL,
                   assets=THREE_ASSETS, replay_scope=S03_REPLAY_SCOPE)
        self.assertTrue(all(not r.calls for r in readers.values()))

    def fixture(self, future_exit=120110):
        rows = {asset: {} for asset in THREE_ASSETS}
        trades = []
        for day in (26, 27, 28, 29):
            at = stamp(f"2023-12-{day}T08:00:00")
            end = at + 20 * MINUTE
            rows["XAUUSD"][at] = np.array(
                [(at, 1999900, 2000000), (end, 2100000, 2100100)], dtype=DTYPE)
            trades.append(record(decision_msc=at, entry_msc=at, exit_msc=end,
                deadline_msc=end, exit_quote_index=1, exit_price_units=2100000,
                signal_id=f"gold-{day}"))
        at = stamp("2024-01-02T08:00:00")
        end = at + 20 * MINUTE
        rows["GBPUSD"][at] = np.array(
            [(at, 120000, 120010), (end, future_exit, future_exit + 10)], dtype=DTYPE)
        trades.append(record("GBPUSD", decision_msc=at, entry_msc=at,
            exit_msc=end, deadline_msc=end, exit_quote_index=1,
            exit_price_units=future_exit, signal_id="gbp-2024"))
        return rows, trades

    def test_boundary_full_state_and_sentinels_ignore_future_prices(self):
        rows, trades = self.fixture()
        dev_rows = {asset: {h: a for h, a in hours.items() if h < END}
                    for asset, hours in rows.items()}
        old_accounts = [self.run_account(end=stamp("2023-01-01")),
                        self.run_account(end=END, rolling=True)]
        before = []
        expected = replay(trades[:-1], self.readers(dev_rows, END), old_accounts,
                          end=END, assets=THREE_ASSETS, checkpoints=(END,),
                          checkpoint_callback=before.append)
        self.assertEqual(before[0]["accounts"][1]["phase"], 2)
        self.assertEqual(before[0]["accounts"][1]["balance"], 50000000)
        self.assertIn("anchor", before[0]["accounts"][1])
        self.assertIn("phase_days", before[0]["accounts"][1])
        self.assertEqual(len(before[0]["accounts"][1]["passes"]), 1)
        self.assertIn(stamp("2023-12-31T23:00:00"),
                      [r[0] for r in before[0]["accounts"][1]["daily_marks"]])
        for future_exit in (120110, 119010):
            rows, trades = self.fixture(future_exit)
            continued = self.run_account(rolling=True)
            sentinels = [self.run_account(end=stamp("2023-01-01")),
                         self.run_account(end=END, rolling=True)]
            snapshots = []
            got = replay(trades, self.readers(rows), [*sentinels, continued],
                         end=FINAL, assets=THREE_ASSETS, replay_scope=S03_REPLAY_SCOPE,
                         checkpoints=(END,), checkpoint_callback=snapshots.append)
            self.assertEqual(snapshots[0]["accounts"][:2], before[0]["accounts"])
            self.assertEqual(snapshots[0]["accounts"][2], before[0]["accounts"][1])
            self.assertEqual(snapshots[0]["stream"], before[0]["stream"])
            self.assertEqual(snapshots[0]["coverage"], before[0]["coverage"])
            for actual, old in zip(got[:2], expected):
                actual.pop("joint_tick_marks")
                self.assertEqual(actual, {k: v for k, v in old.items() if k != "joint_tick_marks"})
            self.assertEqual(continued.phase, 2)
            self.assertEqual(len(continued.accepted), 5)
            self.assertFalse(continued.active)
            snapshots[0]["accounts"][2]["accepted"].clear()
            self.assertEqual(len(continued.accepted), 5)

    def test_checkpoint_configuration_rejects_unregistered_times(self):
        for points, callback in (((END + HOUR,), lambda _: None), ((END,), None),
                                 ((), lambda _: None), ((END,), "not-callable")):
            with self.assertRaisesRegex(ValueError, "unregistered_replay_checkpoint"):
                replay([], self.readers(), [self.run_account()], end=FINAL,
                       assets=THREE_ASSETS, replay_scope=S03_REPLAY_SCOPE,
                       checkpoints=points, checkpoint_callback=callback)

    def test_only_future_trades_do_not_inject_resets_into_empty_development(self):
        snapshots = []
        before = replay([], self.readers(cutoff=END), [self.run_account(end=END)],
                        end=END, assets=THREE_ASSETS, checkpoints=(END,),
                        checkpoint_callback=snapshots.append)[0]
        rows, trades = self.fixture()
        rows = {asset: {h: data for h, data in hours.items() if h >= END}
                for asset, hours in rows.items()}
        after_snapshots = []
        sentinel = self.run_account(end=END)
        after = replay(trades[-1:], self.readers(rows), [sentinel, self.run_account()],
                       end=FINAL, assets=THREE_ASSETS, replay_scope=S03_REPLAY_SCOPE,
                       checkpoints=iter([END]), checkpoint_callback=after_snapshots.append)[0]
        self.assertEqual(snapshots[0]["accounts"][0], after_snapshots[0]["accounts"][0])
        self.assertEqual(snapshots[0]["stream"], after_snapshots[0]["stream"])
        self.assertEqual(snapshots[0]["coverage"], after_snapshots[0]["coverage"])
        self.assertEqual({k: v for k, v in before.items() if k != "joint_tick_marks"},
                         {k: v for k, v in after.items() if k != "joint_tick_marks"})
        self.assertEqual(sentinel.daily_marks, [])

    def test_expanded_run_supports_104_accounts_and_108_sentinels(self):
        rows, trades = self.fixture()
        accounts = [self.run_account(rolling=True) for _ in range(104)]
        accounts += [self.run_account(end=END, rolling=True) for _ in range(108)]
        result = replay(trades, self.readers(rows), accounts, end=FINAL,
                        assets=THREE_ASSETS, replay_scope=S03_REPLAY_SCOPE)
        self.assertEqual(len(result), 212)
        self.assertTrue(all(r["entries"] == 5 for r in result[:104]))
        self.assertTrue(all(r["entries"] == 4 for r in result[104:]))
        self.assertTrue(all(r["cash_bridge_verified"] for r in result))

    def test_terminal_gap_and_breach_coverage_match_after_future_quote(self):
        prior = END - 20 * MINUTE
        old = QuoteAgeCoverage(THREE_ASSETS)
        old.observe("XAUUSD", prior // HOUR * HOUR,
                    np.array([(prior, 100, 101)], dtype=DTYPE))
        old.finish(END)
        expanded = QuoteAgeCoverage(THREE_ASSETS)
        expanded.observe("XAUUSD", prior // HOUR * HOUR,
                         np.array([(prior, 100, 101)], dtype=DTYPE))
        expanded.observe("XAUUSD", END + HOUR,
                         np.array([(END + HOUR, 100, 101)], dtype=DTYPE))
        expanded.finish(FINAL)
        sentinel = self.run_account(end=END)
        sentinel.accepted = [dict(trade=0, at=prior)]
        trade = dict(asset="XAUUSD", exit_msc=END + HOUR)
        for breach in (None, dict(at=END - MINUTE)):
            sentinel.breach = breach
            self.assertEqual(old.account(sentinel, [trade]), expanded.account(sentinel, [trade]))


if __name__ == "__main__":
    unittest.main()
