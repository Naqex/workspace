from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import ftmo_free_trial_adapter as app


def stamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


FIRST = stamp("2022-05-02T10:00:00")
IDENTITY = "XAUUSD|F3:compression=BB:n=60:quantile=0.1:multiple=1|48H|P0"
WEIGHTS = {IDENTITY: 1,
           "EURUSD|F5:tf=H4:n=5:adx=25:buffer=0.1|DAY|P0": 1,
           "XAUUSD|F4:hour=15:impulse=1:timing=MONTH:multiple=1|24H|P1": 1}


def spec(asset):
    return dict(trade_contract_size=100 if asset == "XAUUSD" else 100000,
        volume_min=.01, volume_step=.01, volume_max=100, point=.001 if asset == "XAUUSD" else .00001,
        trade_tick_size=.01 if asset == "XAUUSD" else .00001, swap_long=-45, swap_short=-5,
        swap_mode=1, trade_stops_level=0, trade_freeze_level=0, trade_mode=4)


def calendar():
    return dict(known_at_msc=FIRST - 86400000, from_msc=FIRST - 86400000,
                to_msc=FIRST + 7 * 86400000, source="OFFLINE_TEST_FIXTURE", coverage_complete=True,
                events=[], days={})


def account():
    return dict(login=1234, server="FTMO-OFFLINE-FIXTURE", trade_mode=0, currency="USD")


def mark(at=FIRST):
    return dict(known_at_msc=at, midnight_msc=app.prague_midnight(at), history_query_complete=True,
                equity=50000, midnight_balance=50000, initial_balance=50000)


def plan():
    a = account()
    return dict(policy="V19", profile=dict(name="BASE_GUARD", gamma=None, weights=dict(WEIGHTS)),
        phase="FREE_TRIAL", from_msc=FIRST, to_msc=FIRST + 24 * 3600000,
        binding=dict(server=a["server"], account_hash=app.account_hash(a["login"], a["server"])),
        news=calendar(), holidays=calendar(), specs={a: spec(a) for a in app.ASSETS},
        closed_M1_times={"XAUUSD": list(range(FIRST - 30 * 60000, FIRST, 60000))})


def tick(at=FIRST, bid=2000, ask=2000.34):
    return dict(asset="XAUUSD", time_msc=at, known_at_msc=at, bid=bid, ask=ask)


def intent(identity=IDENTITY):
    return dict(id=identity, asset="XAUUSD", side="BUY", decision_msc=FIRST,
                stop_units=1990000, mode=identity.rsplit("|", 1)[-1], intent_id="test-intent")


def paper():
    p = plan()
    shadow = app.ShadowPaper(p, p["from_msc"], p["to_msc"])
    shadow.mark = mark()
    return shadow


class BindingCollectorTests(unittest.TestCase):
    def test_adapter_has_no_broker_submission_API_even_if_a_caller_changes_the_flag(self):
        import ast
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ("order_send", "order_check", "login")
                             for n in ast.walk(tree)))
        self.assertIs(app.ALLOW_LIVE_ORDER_SEND, False)

    def test_real_or_unverified_account_cannot_be_accepted(self):
        p = plan()
        for value in (2, False, None):
            a = account()
            a["trade_mode"] = value
            with self.assertRaises(app.AdapterError):
                app.verify_account(a, p["binding"])
        with self.assertRaises(app.AdapterError):
            app.verify_account(dict(account(), login=999), p["binding"])

    def test_capture_keeps_spread_and_spec_but_does_not_claim_slippage(self):
        payload = dict(schema="ftmo-readonly-bridge-v1", account=account(),
                       specs={a: spec(a) for a in app.ASSETS}, ticks=[tick()])
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "bridge.json"
            path.write_text(json.dumps(payload))
            result = app.collect(app.FileBridge(path), plan()["binding"], FIRST, FIRST + 1000, observed_at=FIRST + 1000)
        self.assertFalse(result["execution_capability"])
        self.assertFalse(result["slippage_measured"])
        self.assertAlmostEqual(result["spread_by_UTC_hour"]["XAUUSD"]["10"]["median"], .34)
        self.assertNotIn("login", result["binding"])

    def test_symbol_grid_divergence_is_not_silently_rounded_or_scaled(self):
        with self.assertRaises(app.AdapterError):
            app.validate_spec("XAUUSD", dict(spec("XAUUSD"), volume_step=.1))

    def test_capture_interval_cannot_read_future(self):
        with self.assertRaises(app.AdapterError):
            app.collect(None, {}, FIRST, FIRST + 2000, observed_at=FIRST + 1000)


class CalendarGuardTests(unittest.TestCase):
    def test_prague_reset_changes_with_DST(self):
        winter = stamp("2026-01-12T12:00:00")
        summer = stamp("2026-07-12T12:00:00")
        self.assertEqual(app.prague_midnight(winter), stamp("2026-01-11T23:00:00"))
        self.assertEqual(app.prague_midnight(summer), stamp("2026-07-11T22:00:00"))

    def test_daily_equality_counts_as_halt_and_includes_equity(self):
        value = mark()
        value["equity"] = 48900
        self.assertEqual(app.daily_guard(value, FIRST), "DAILY_2P2_HALT")
        value["equity"] = 48900.01
        self.assertIsNone(app.daily_guard(value, FIRST))

    def test_daily_unknown_or_stale_anchor_blocks(self):
        self.assertIsNotNone(app.daily_guard(None, FIRST))
        self.assertIsNotNone(app.daily_guard(mark(), FIRST + 60001))
        self.assertIsNotNone(app.daily_guard(dict(mark(), midnight_msc=0), FIRST))

    def test_news_window_is_inclusive_and_program_phase_is_explicit(self):
        news = calendar()
        news["events"] = [dict(at_msc=FIRST + 120000, assets=["XAUUSD"])]
        self.assertEqual(app.news_guard(news, FIRST, "XAUUSD", "FUNDED_STANDARD"), "RESTRICTED_NEWS_2MIN")
        self.assertIsNone(app.news_guard(news, FIRST - 1, "XAUUSD", "FUNDED_STANDARD"))
        self.assertIsNone(app.news_guard(news, FIRST, "XAUUSD", "CHALLENGE", simulate_funded_rules=False))
        self.assertEqual(app.news_guard(news, FIRST, "XAUUSD", "unknown"), "PROGRAM_PHASE_UNKNOWN")

    def test_empty_calendar_requires_declared_complete_coverage(self):
        self.assertIsNotNone(app.news_guard({}, FIRST, "XAUUSD", "FUNDED_STANDARD"))
        self.assertIsNotNone(app.news_guard(dict(calendar(), coverage_complete=False), FIRST, "XAUUSD", "FUNDED_STANDARD"))
        self.assertIsNone(app.news_guard(calendar(), FIRST, "XAUUSD", "FUNDED_STANDARD"))

    def test_friday_and_early_close_are_known_calendar_deadlines(self):
        friday = stamp("2022-05-06T10:00:00")
        self.assertEqual(app.session_deadline(friday, calendar()), stamp("2022-05-06T20:30:00"))
        c = calendar()
        c["days"] = {"2022-05-06": dict(flat_utc="17:30")}
        self.assertEqual(app.session_deadline(friday, c), stamp("2022-05-06T17:30:00"))


class PaperHarnessTests(unittest.TestCase):
    def test_invalid_or_unregistered_signal_cannot_be_reinterpreted_as_sell(self):
        for fields in (dict(side="BUYY"), dict(mode="P2"), dict(id="XAUUSD|new|DAY|P0"),
                       dict(stop_units=1990000.5), dict(decision_msc=float(FIRST))):
            with self.assertRaises(app.AdapterError):
                paper().offer(dict(intent(), **fields), FIRST)

    def test_paper_initial_phase_controls_risk_instead_of_only_changing_a_label(self):
        risks = {}
        for phase in ("CHALLENGE", "VERIFICATION", "FUNDED_STANDARD"):
            value = plan()
            value["phase"] = phase
            p = app.ShadowPaper(value, FIRST, FIRST + 3600000)
            p.mark = mark()
            p.offer(intent(), FIRST)
            p.advance(tick())
            risks[phase] = p.account.accepted[0]["risk_usd"]
        self.assertEqual(risks, dict(CHALLENGE=300, VERIFICATION=262.5, FUNDED_STANDARD=187.5))

    def test_one_intent_one_paper_entry_and_no_broker_send(self):
        p = paper()
        p.offer(intent(), FIRST)
        p.offer(intent(), FIRST)
        p.advance(tick())
        result = p.report()
        self.assertEqual(result["account"]["entries"], 1)
        self.assertEqual(result["broker_orders_sent"], 0)
        self.assertFalse(app.ALLOW_LIVE_ORDER_SEND)
        self.assertFalse(result["broker_execution_ready"])

    def test_intent_mutation_is_not_treated_as_same_signal(self):
        p = paper()
        p.offer(intent(), FIRST)
        with self.assertRaises(app.AdapterError):
            p.offer(dict(intent(), stop_units=1980000), FIRST)

    def test_gap_stop_fills_at_observed_quote_not_guaranteed_stop(self):
        p = paper()
        p.offer(intent(), FIRST)
        p.advance(tick())
        p.advance(tick(FIRST + 1000, 1980, 1980.34))
        result = p.report()
        self.assertEqual(result["expected_fills"][-1]["price"], 1980)
        self.assertLess(result["account"]["net_usd"], -300)
        self.assertEqual(result["log"][-2]["reason"], "SL")

    def test_feed_timeout_exits_on_next_quote_and_records_causality(self):
        p = paper()
        p.offer(intent(), FIRST)
        p.advance(tick())
        p.advance(tick(FIRST + 180000, 2000, 2000.34))
        exits = [r for r in p.log if r["kind"] == "PAPER_EXIT"]
        self.assertEqual(exits[0]["known_at_msc"], FIRST + 180000)
        self.assertEqual(exits[0]["reason"], "FEED_TIMEOUT_NEXT_QUOTE")

    def test_missing_recent_M1_or_news_coverage_blocks_entry(self):
        for missing in ("closed_M1_times", "news"):
            p = paper()
            p.plan[missing] = {}
            p.offer(intent(), FIRST)
            p.advance(tick())
            self.assertEqual(len(p.account.accepted), 0)

    def test_lot_max_and_natural_stop_tick_grid_are_pretrade_guards(self):
        p = paper()
        p.plan["specs"]["XAUUSD"]["volume_max"] = .01
        p.offer(intent(), FIRST)
        p.advance(tick())
        self.assertEqual(len(p.account.accepted), 0)
        p = paper()
        p.offer(dict(intent(), stop_units=1990001), FIRST)
        p.advance(tick())
        self.assertEqual(len(p.account.accepted), 0)

    def test_P1_arms_only_after_prior_minute_closes(self):
        p = paper()
        i = intent("XAUUSD|F4:hour=15:impulse=1:timing=MONTH:multiple=1|24H|P1")
        p.offer(i, FIRST)
        p.advance(tick())
        p.advance(tick(FIRST + 30000, 2017, 2017.34))
        self.assertIsNone(p.trades[0]["activation_time"])
        p.advance(tick(FIRST + 60000, 2016, 2016.34))
        self.assertEqual(p.trades[0]["activation_time"], FIRST + 60000)
        p.advance(tick(FIRST + 90000, 2001, 2001.34))
        self.assertTrue(any(r.get("reason") == "PROTECT" for r in p.log))

    def test_P1_uses_observed_favorable_extreme_of_completed_minute_not_only_its_close(self):
        p = paper()
        p.offer(intent("XAUUSD|F4:hour=15:impulse=1:timing=MONTH:multiple=1|24H|P1"), FIRST)
        p.advance(tick())
        p.advance(tick(FIRST + 30000, 2017, 2017.34))
        p.advance(tick(FIRST + 59000, 2010, 2010.34))
        self.assertIsNone(p.trades[0]["activation_time"])
        p.advance(tick(FIRST + 60000, 2010, 2010.34))
        self.assertEqual(p.trades[0]["activation_time"], FIRST + 60000)

    def test_pre_news_flat_uses_known_deadline_before_restricted_window(self):
        p = paper()
        p.plan["news"]["events"] = [dict(at_msc=FIRST + 600000, assets=["XAUUSD"])]
        p.offer(intent(), FIRST)
        p.advance(tick())
        for n in range(1, 8):
            p.advance(tick(FIRST + n * 60000))
        p.advance(tick(FIRST + 450000))
        exits = [r for r in p.log if r["kind"] == "PAPER_EXIT"]
        self.assertEqual(exits[0]["reason"], "NEWS_PRE_FLAT")
        self.assertLess(exits[0]["known_at_msc"], FIRST + 480000)

    def test_future_initial_M1_or_nonfinite_quote_is_rejected(self):
        value = plan()
        value["closed_M1_times"]["XAUUSD"].append(FIRST)
        with self.assertRaises(app.AdapterError):
            app.ShadowPaper(value, FIRST, FIRST + 3600000)
        with self.assertRaises(app.AdapterError):
            paper().advance(tick(bid=float("nan")))

    def test_reducer_rejects_future_or_duplicate_record(self):
        value = plan()
        quote = dict(tick(), kind="quote", record_id="same")
        bundle = dict(account=account(), events=[quote, quote])
        with self.assertRaises(app.AdapterError):
            app.reduce_bridge(bundle, value)

    def test_quote_before_signal_was_known_cannot_supply_entry_fill(self):
        p = paper()
        p.offer(intent(), FIRST + 500)
        p.advance(dict(tick(FIRST), known_at_msc=FIRST + 500))
        self.assertEqual(len(p.account.accepted), 0)
        p.advance(tick(FIRST + 501))
        self.assertEqual(len(p.account.accepted), 1)

    def test_stale_tick_waits_for_fresh_quote_without_cancelling_valid_entry_window(self):
        p = paper()
        p.offer(intent(), FIRST)
        p.advance(dict(tick(FIRST + 1000), known_at_msc=FIRST + 5000))
        self.assertFalse(p.intents["test-intent"]["consumed"])
        p.advance(tick(FIRST + 5001))
        self.assertEqual(len(p.account.accepted), 1)

    def test_friction_equality_and_adjacent_native_stop_units(self):
        identity = "EURUSD|F5:tf=H4:n=5:adx=25:buffer=0.1|DAY|P0"
        for stop, accepted in ((128063, 1), (128064, 1), (128065, 0)):
            with self.subTest(stop=stop):
                p = paper()
                p.plan["closed_M1_times"]["EURUSD"] = list(p.plan["closed_M1_times"]["XAUUSD"])
                p.offer(dict(intent(identity), asset="EURUSD", stop_units=stop), FIRST)
                p.advance(dict(tick(), asset="EURUSD", bid=1.28175, ask=1.28184))
                self.assertEqual(len(p.account.accepted), accepted)
                if not accepted:
                    self.assertEqual(p.log[-2]["reason"], "FRICTION_OVER_15PCT_OF_NATURAL_SL")

    def test_native_friction_matches_independent_decimal_commission_rounding(self):
        from quant_core.cost_gates import stress_market_friction_units
        from quant_core.vectorized_sl_active_kernel import money
        for asset, scale, bid, ask in (("EURUSD", 100000, 128175, 128184),
                                       ("XAUUSD", 1000, 2000000, 2000340),
                                       ("XAUUSD", 1000, 2007142, 2007143),
                                       ("XAUUSD", 1000, 2007143, 2007483)):
            if asset == "XAUUSD":
                fees = sum((Decimal(price) / scale * Decimal("0.000007")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP) for price in (bid, ask))
                expected = Decimal(ask - bid) + (fees + Decimal(".4")) * scale
            else:
                expected = Decimal(ask - bid + 9)
            cost = stress_market_friction_units(asset, bid, ask)
            self.assertEqual(cost, Fraction(expected))
            for side in (1, -1):
                entry, exit_px = (ask, bid) if side == 1 else (bid, ask)
                old = -money(asset, "SYM", np.array([side]), [entry], [exit_px],
                             [FIRST], [FIRST], ["MARKET"])["net"][0]
                self.assertAlmostEqual(float(cost) / scale, old, places=10)

    def test_gold_friction_equality_both_sides_and_adjacent_broker_ticks(self):
        from quant_core.cost_gates import stress_market_friction_units
        self.assertEqual(stress_market_friction_units("XAUUSD", 2000000, 2000340), 768)
        for side, entry in (("BUY", 2000340), ("SELL", 2000000)):
            for distance, accepted in ((5110, 0), (5120, 1), (5130, 1)):
                with self.subTest(side=side, distance=distance):
                    p = paper()
                    stop = entry - distance if side == "BUY" else entry + distance
                    p.offer(dict(intent(), side=side, stop_units=stop), FIRST)
                    p.advance(tick())
                    self.assertEqual(len(p.account.accepted), accepted)

    def test_other_held_asset_age_uses_source_clock_not_arrival_clock(self):
        p = paper()
        p.offer(intent(), FIRST)
        p.advance(dict(tick(), known_at_msc=FIRST + 500))
        self.assertEqual(len(p.account.active), 1)
        identity = "EURUSD|F5:tf=H4:n=5:adx=25:buffer=0.1|DAY|P0"
        for age, expected in ((120000, None), (120001, "OTHER_ACTIVE_ASSET_QUOTE_STALE")):
            with self.subTest(age=age):
                now = FIRST + age
                p.mark = mark(now)
                p.quotes["EURUSD"] = dict(bid_units=110000, ask_units=110009,
                                         known_at_msc=now, source_msc=now)
                p.plan["closed_M1_times"]["EURUSD"] = list(range(
                    now // app.MINUTE * app.MINUTE - 30 * app.MINUTE,
                    now // app.MINUTE * app.MINUTE, app.MINUTE))
                incoming = dict(intent(identity), asset="EURUSD", decision_msc=now, stop_units=109000)
                row = dict(tick(now), asset="EURUSD", bid=1.1, ask=1.10009)
                self.assertEqual(p.entry_reason(incoming, now, row), expected)

    def test_stale_position_path_never_creates_a_backdated_market_fill(self):
        p = paper()
        p.offer(intent(), FIRST)
        p.advance(tick())
        p.advance(dict(tick(FIRST + 1000, 1989, 1989.34), known_at_msc=FIRST + 5000))
        self.assertTrue(p.path_uncertain)
        self.assertEqual(len(p.account.closed), 0)
        p.advance(tick(FIRST + 5001, 1988, 1988.34))
        self.assertEqual(p.expected[-1]["requested_at_msc"], FIRST + 5001)
        self.assertEqual(p.expected[-1]["price"], 1988)
        p.offer(dict(intent(), intent_id="after-stale", decision_msc=FIRST + 5001), FIRST + 5001)
        p.advance(tick(FIRST + 5002))
        self.assertEqual(len(p.account.accepted), 1)
        self.assertIsNotNone(p.halted_reason)

    def test_unfrozen_policy_is_not_a_v19_live_shadow_configuration(self):
        value = plan()
        value["profile"]["gamma"] = .5
        with self.assertRaises(app.AdapterError):
            app.ShadowPaper(value, FIRST, FIRST + 3600000)


class SignalAndReconciliationTests(unittest.TestCase):
    def test_native_H1_requires_sixty_closed_M1_and_matching_OHLC(self):
        dtype = [("time", "<i8")] + [(k, "<f8") for k in ("open", "high", "low", "close")]
        hour = np.array([(FIRST // 1000 - 3600, 2000, 2001, 1999, 2000)], dtype=dtype)
        minutes = np.array([(FIRST // 1000 - 3600 + n * 60, 2000, 2001, 1999, 2000)
                            for n in range(60)], dtype=dtype)
        class SDK:
            TIMEFRAME_H1, TIMEFRAME_M1 = 1, 2
            minute_rows = minutes
            def copy_rates_from_pos(self, *args):
                return hour
            def copy_rates_range(self, *args):
                return self.minute_rows
        reader = object.__new__(app.NativeMT5Reader)
        reader.sdk = SDK()
        self.assertEqual(len(reader.hourly("XAUUSD", FIRST)), 1)
        reader.sdk.minute_rows = minutes[:-1]
        self.assertEqual(reader.hourly("XAUUSD", FIRST), [])
        reader.sdk.minute_rows = minutes.copy()
        reader.sdk.minute_rows["high"][3] = 2002
        with self.assertRaises(app.AdapterError):
            reader.hourly("XAUUSD", FIRST)

    def test_inclusive_live_tick_boundary_preserves_duplicates_and_detects_revision(self):
        a = dict(tick(), flags=1)
        saved = [(FIRST, a["bid"], a["ask"], 1)]
        later = dict(a, time_msc=FIRST + 1)
        self.assertEqual(app.new_live_ticks([a, a, later], (FIRST, saved)), [a, later])
        with self.assertRaises(app.AdapterError):
            app.new_live_ticks([dict(a, bid=1999)], (FIRST, saved))

    def test_native_shadow_gateway_can_be_replayed_without_any_broker_submission(self):
        p = plan()
        class Reader:
            def account(self):
                return account()
            def spec(self, asset):
                return spec(asset)
            def closed_minutes(self, asset, now):
                return list(range(FIRST - 30 * 60000, FIRST, 60000))
            def account_mark(self, now, initial):
                value[0] += 10
                return mark(now)
            def hourly(self, asset, now):
                value[0] += 20
                return [dict(t=FIRST - n * 3600000, bo=2000000, bh=2001000, bl=1999000, bc=2000000)
                        for n in range(400, 0, -1)]
            def ticks(self, asset, first, end):
                value[0] += 10
                values = sorted(set([first, end - 1]))
                if asset == "XAUUSD":
                    return [dict(tick(at), flags=1) for at in values]
                return [dict(asset=asset, time_msc=at, bid=1.1, ask=1.1001, flags=1) for at in values]
        value = [FIRST]
        def clock():
            return value[0]
        def sleep(seconds):
            value[0] += round(seconds * 1000)
        def signals(hourly, asset, now, calendar):
            return [intent()] if asset == "XAUUSD" else []
        with tempfile.TemporaryDirectory() as root, patch.object(app, "signals_from_closed_hours", signals):
            out = Path(root)
            p["signal_seeds"] = {}
            for asset in app.ASSETS:
                seed = dict(schema="v16-closed-hour-seed-v1", first=1509494400000,
                            known_at_msc=FIRST - 1,
                            rows=[dict(t=1509494400000, bo=2000000, bh=2001000, bl=1999000, bc=2000000)])
                seed_path = out / (asset + "-seed.json")
                seed_path.write_text(json.dumps(seed))
                p["signal_seeds"][asset] = dict(path=str(seed_path),
                    sha256=app.hashlib.sha256(seed_path.read_bytes()).hexdigest())
            live = app.run_native_shadow(Reader(), p, out, max_seconds=2, poll_seconds=1,
                                         clock=clock, sleeper=sleep)
            effective = json.loads((out / "effective-paper-plan.json").read_text())
            events = [json.loads(line) for line in (out / "native-shadow-events.jsonl").read_text().splitlines()]
            replay = app.reduce_bridge(dict(account=account(), events=events), effective)
        self.assertEqual(live["account"], replay["account"])
        self.assertEqual(live["expected_fills"], replay["expected_fills"])
        self.assertEqual(live["actual_broker_orders"], 0)
        self.assertGreater(live["expected_fills"][0]["requested_at_msc"], FIRST)

    def test_seed_change_future_and_overlap_divergence_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "seed.json"
            row = dict(t=1509494400000, bo=100, bh=101, bl=99, bc=100)
            path.write_text(json.dumps(dict(schema="v16-closed-hour-seed-v1", first=row["t"],
                                           known_at_msc=FIRST - 1, rows=[row])))
            bound = dict(path=str(path), sha256=app.hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(app.known_hour_seed(bound, [row], FIRST), [row])
            with self.assertRaises(app.AdapterError):
                app.known_hour_seed(bound, [dict(row, bc=101)], FIRST)
            with self.assertRaises(app.AdapterError):
                app.known_hour_seed(dict(bound, sha256="0" * 64), [], FIRST)
            with self.assertRaises(app.AdapterError):
                app.known_hour_seed(bound, [], row["t"])

    def test_native_recipe_reuse_preserves_first_event_day_context(self):
        hours = np.zeros(400, dtype=[(k, "<i8") for k in ("t", "bo", "bh", "bl", "bc")])
        hours["t"] = FIRST - np.arange(400, 0, -1) * 3600000
        recipe = dict(id="F3:compression=BB:n=60:quantile=0.1:multiple=1",
                      at=np.array([FIRST]), side=np.array([1]), stop=np.array([1990000]))
        with patch("quant_core.native_hourly_source.native_recipes", return_value=[recipe]) as native:
            r = app.signals_from_closed_hours(hours, "XAUUSD", FIRST, object())
        self.assertEqual(r[0]["id"], IDENTITY)
        self.assertEqual(native.call_args.args[2], FIRST // 86400000 * 86400000)

    def test_unfinished_hour_is_never_used(self):
        hours = np.zeros(400, dtype=[("t", "<i8")])
        hours["t"] = FIRST - np.arange(399, -1, -1) * 3600000
        with self.assertRaises(app.AdapterError):
            app.signals_from_closed_hours(hours, "XAUUSD", FIRST, object())

    def test_hourly_bridge_never_truncates_fractional_integer_grid(self):
        row = dict(t=FIRST - 3600000, bo=100, bh=101, bl=99, bc=100.5)
        with self.assertRaises(app.AdapterError):
            app.validate_closed_hours([row], FIRST)
        row["bc"] = 100
        app.validate_closed_hours([row], FIRST)
        with self.assertRaises(app.AdapterError):
            app.validate_closed_hours([row, row], FIRST)

    def test_partial_fills_use_weighted_price_and_signed_slippage(self):
        expected = [dict(intent_id="a", asset="XAUUSD", side="BUY", price=2000, volume=.3, requested_at_msc=10)]
        fills = [dict(intent_id="a", deal_id=i, asset="XAUUSD", side="BUY", price=px,
                      volume=volume, filled_at_msc=20) for i, px, volume in ((1, 2000.1, .1), (2, 2000.4, .2))]
        result = app.reconcile_fills(expected, fills)[0]
        self.assertEqual(result["status"], "MATCHED")
        self.assertAlmostEqual(result["adverse_slippage_price_units"], .3)
        self.assertIsNone(result["commission"])
        self.assertEqual(result["actual_cost_status"], "INCOMPLETE")

    def test_fill_from_another_account_cannot_match_a_shared_strategy_intent(self):
        e = [dict(intent_id="a", account_hash="expected-account", asset="XAUUSD", side="BUY",
                  price=2000, volume=.1, requested_at_msc=10)]
        f = [dict(intent_id="a", account_hash="other-account", deal_id=1, asset="XAUUSD", side="BUY",
                  price=2000.1, volume=.1, filled_at_msc=20, commission=-.1, swap=0, fee=0)]
        self.assertEqual(app.reconcile_fills(e, f)[0]["status"], "ACCOUNT_BINDING_MISMATCH")

    def test_missing_duplicate_or_pre_request_fills_not_counted_as_valid(self):
        e = [dict(intent_id="a", asset="XAUUSD", side="SELL", price=2000, volume=.1, requested_at_msc=10)]
        self.assertIn("UNMEASURED", app.reconcile_fills(e, [])[0]["status"])
        f = dict(intent_id="a", deal_id=1, asset="XAUUSD", side="SELL", price=2000, volume=.1, filled_at_msc=5)
        self.assertIn("BEFORE_REQUEST", app.reconcile_fills(e, [f])[0]["status"])
        self.assertEqual(app.reconcile_fills(e, [f, f])[0]["status"], "DUPLICATE_DEAL_ID")


if __name__ == "__main__":
    unittest.main()
