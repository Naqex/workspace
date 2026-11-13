from datetime import datetime, timezone
from decimal import Decimal as D
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gold_continuous_b1 import (
    GoldPrefix, Minute, QualityPath, START, END, phase_spec, native_context,
    lifecycle_probe, reward_contract, utc, ResearchH4Candidate, Candle,
    calendar_oracle, money_oracle, MoneyOracleInput, size_for_market_stop,
)
from trading_workspace_v2.prop_session import TransitionIntent, apply_prop_lifecycle_command
from trading_workspace_v2.research_market import MetalStudyMarket


def stamp(value):
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())


def minute(at, o='1000', h='1001', l='999', c='1000'):
    return Minute(at, *map(D, (o, h, l, c)))


def pending(at, side='BUY', distance='20', quantity='.05'):
    return dict(time=at, signal=side, distance=distance, quantity=quantity, status='queued')


def serialized(engine):
    return json.loads(json.dumps(engine.checkpoint(), default=str))


class GoldB1Tests(unittest.TestCase):
    def test_geometry_explicit_capital_endpoints_and_no_guard_defaults(self):
        engine = GoldPrefix('125')
        self.assertEqual(engine.instrument.contract_size, 100)
        self.assertEqual(engine.instrument.tick_size, D('.001'))
        self.assertEqual(engine.balance, 50000)
        self.assertEqual(engine.path.anchor, 50000)
        for risk in ('125', '200'):
            engine = GoldPrefix(risk)
            qty = size_for_market_stop(D('20'), instrument=engine.instrument, model=engine.model, budget=engine.budget)
            perlot = D('20.401') * 100 + 5
            self.assertLessEqual(qty * perlot, engine.budget)
            self.assertGreater((qty + D('.01')) * perlot, engine.budget)
        for wrong in ('25', '100', '500'):
            with self.assertRaises(ValueError):
                GoldPrefix(wrong)
        with self.assertRaises(ValueError):
            MetalStudyMarket(contract_size='100000')

    def test_full_seed_differs_from_truncated_wilder_seed(self):
        bars = [Candle(i*14400, D(1000+i), D(1010+i+i%13), D(980+i-i%7), D(1000+i)) for i in range(180)]
        full, truncated = ResearchH4Candidate('xauusd-h4-sma20-80-atr14-r025-v1'), ResearchH4Candidate('xauusd-h4-sma20-80-atr14-r025-v1')
        for bar in bars:
            full.observe(bar)
        for bar in bars[-100:]:
            truncated.observe(bar)
        self.assertNotEqual(full.atr, truncated.atr)
        self.assertEqual(full.previous_difference, truncated.previous_difference)
        restored = ResearchH4Candidate.from_state(full.export_state().model_dump(mode='json'))
        self.assertEqual(full.observe(Candle(180*14400, D(1180), D(1200), D(1170), D(1190))),
                         restored.observe(Candle(180*14400, D(1180), D(1200), D(1170), D(1190))))

    def test_prewarm_observations_create_no_position_or_pending(self):
        engine = GoldPrefix('125')
        for i in range(400):
            at = START - (400-i)*3600
            engine.step(minute(at, h='1100', c=str(1000+i%80)))
        engine.finalize_hour()
        self.assertGreater(engine.warmup_h4, 80)
        self.assertIsNone(engine.position)
        self.assertIsNone(engine.pending)
        self.assertEqual(engine.counter, 0)

    def test_completed_h4_only_and_fill_after_intent(self):
        engine = GoldPrefix('125')
        for i in range(4):
            engine.step(minute(START + i*3600))
        self.assertEqual(len(engine.strategy.history), 0)
        engine.step(minute(START + 14400))
        self.assertEqual(len(engine.strategy.history), 1)
        engine.pending = pending(START+14460)
        with self.assertRaisesRegex(ValueError, 'before intent'):
            engine.fill(START+14400, D('1000'))

    def test_missing_hour_excluded_not_padded(self):
        engine = GoldPrefix('125')
        for hour in (0, 1, 3, 4):
            engine.step(minute(START + hour*3600))
        self.assertEqual(len(engine.strategy.history), 0)
        self.assertIn(START, engine.builder.excluded)

    def test_minlot_margin_rejection_and_rounding(self):
        engine = GoldPrefix('125')
        self.assertIsNone(size_for_market_stop(D('200000'), instrument=engine.instrument, model=engine.model, budget=D('125')))
        engine.pending = pending(START, quantity='10')
        engine.fill(START, D('1000'))
        self.assertEqual(engine.margin_rejections, 1)
        self.assertIsNone(engine.position)
        engine.pending = pending(START, distance='20.0001')
        engine.fill(START, D('1000'))
        self.assertEqual(engine.position.stop_loss, D('980.999'))

    def test_cost_posting_stop_and_no_postexit_extrema(self):
        engine = GoldPrefix('125')
        engine.pending = pending(START, distance='10', quantity='.10')
        engine.step(minute(START, h='1200', l='1'))
        self.assertIsNone(engine.position)
        self.assertEqual(len(engine.trades), 1)
        self.assertEqual(D(engine.trades[0]['price_net_usd']), D('-104.50'))
        self.assertEqual(engine.balance, D('49895.50'))
        self.assertEqual(engine.path.envelope['static_loss'], D('104.50'))
        self.assertEqual(engine.path.unknown[0]['reason'], 'unordered_stop_minute')
        self.assertEqual(engine.trades[0]['exit_time_msc'], (START+60)*1000-1)

    def test_short_ask_stop_geometry(self):
        engine = GoldPrefix('125')
        engine.pending = pending(START, side='SELL', distance='10', quantity='.10')
        engine.step(minute(START, h='1009', l='990'))
        self.assertEqual(engine.trades[0]['exit_fill'], '1010')
        self.assertEqual(D(engine.trades[0]['price_net_usd']), D('-104.50'))

    def test_gap_stop_precedes_pending_strategy_exit(self):
        engine = GoldPrefix('125')
        engine.pending = pending(START)
        engine.step(minute(START))
        engine.pending = pending(START+60, side='EXIT')
        engine.step(minute(START+60, o='970', h='971', l='969', c='970'))
        self.assertEqual(engine.trades[0]['reason'], 'stop_loss_gap')
        self.assertEqual(engine.trades[0]['exit_time_msc'], (START+60)*1000)

    def test_year_boundary_held_pending_and_serialized_resume(self):
        start, end = stamp('2010-12-31T21:59:00Z'), stamp('2011-01-01T23:02:00Z')
        uninterrupted = GoldPrefix('125', start=start, end=end)
        uninterrupted.pending = pending(start, distance='100')
        uninterrupted.step(minute(start))
        uninterrupted.pending = pending(stamp('2011-01-01T00:00:00Z'), side='EXIT')
        restored = GoldPrefix.restore(serialized(uninterrupted))
        self.assertIsNotNone(restored.position)
        self.assertIsNotNone(restored.pending)
        for at in (stamp('2011-01-01T00:00:00Z'), end-60):
            uninterrupted.step(minute(at))
            restored.step(minute(at))
        uninterrupted.finish()
        restored.finish()
        self.assertEqual(serialized(uninterrupted), serialized(restored))
        self.assertEqual(len(restored.trades), 1)
        self.assertEqual(restored.counter, 1)
        self.assertEqual(len(restored.fees), 1)

    def test_wednesday_funding_restart_no_duplicate(self):
        start, end = stamp('2010-01-06T21:59:00Z'), stamp('2010-01-06T22:02:00Z')
        engine = GoldPrefix('200', start=start, end=end)
        engine.pending = pending(start, quantity='.1', distance='100')
        engine.step(minute(start))
        before = GoldPrefix.restore(serialized(engine))
        engine.step(minute(start+60))
        before.step(minute(start+60))
        after = GoldPrefix.restore(serialized(engine))
        after.scheduled(start+60, exact_quote=True)
        self.assertEqual(engine.finance, D('12'))
        self.assertEqual(serialized(engine), serialized(before))
        self.assertEqual(engine.fees, after.fees)
        self.assertEqual(engine.balance, after.balance)

    def test_prague_dst_days_23_and_25_hours(self):
        spec = phase_spec()
        for start_text, end_text, hours in (
            ('2010-03-27T23:00:00Z', '2010-03-28T22:00:00Z', 23),
            ('2010-10-30T22:00:00Z', '2010-10-31T23:00:00Z', 25)):
            start, end = stamp(start_text), stamp(end_text)
            result = calendar_oracle(spec, virtual_start_utc=utc(start), previous_virtual_utc=utc(start), current_virtual_utc=utc(end))
            self.assertEqual(len(result['reset_boundaries']), 1)
            self.assertEqual((end-start)//3600, hours)

    def test_reset_then_exact_fee_cash_anchor_without_stale_floating(self):
        start, end = stamp('2010-03-29T21:59:00Z'), stamp('2010-03-29T22:02:00Z')
        engine = GoldPrefix('125', start=start, end=end)
        engine.pending = pending(start, quantity='.1', distance='100')
        engine.step(minute(start))
        engine.step(minute(start+60))
        self.assertEqual(engine.path.anchor, D('50000'))
        self.assertEqual(engine.balance, D('49996'))
        self.assertTrue(engine.path.resets[0]['contemporaneous_price_known'])
        self.assertGreaterEqual(engine.path.points['daily_loss'], 4)

    def test_missing_reset_quote_latches_uncertainty_after_recovery(self):
        start, end = stamp('2010-01-04T22:59:00Z'), stamp('2010-01-04T23:03:00Z')
        engine = GoldPrefix('125', start=start, end=end)
        engine.pending = pending(start, distance='100')
        engine.step(minute(start))
        engine.step(minute(start+120))
        self.assertFalse(engine.path.resets[0]['contemporaneous_price_known'])
        self.assertEqual(engine.path.anchor, engine.balance)
        self.assertIn('missing_reset_price', [g['reason'] for g in engine.path.unknown])
        engine.step(minute(start+180))
        self.assertIn('missing_reset_price', [g['reason'] for g in engine.path.unknown])

    def test_known_breach_after_unknown_latches_and_equality_not_breach(self):
        path = QualityPath(START, END)
        path.uncertain('prior_missing', START, START+60)
        path.mark(START+120, D('47500'), D(0))
        self.assertIsNone(path.first_supported_breach)
        path.mark(START+180, D('47499.99'), D(0))
        witness = dict(path.first_supported_breach)
        path.mark(START+240, D('55000'), D(0))
        self.assertEqual(path.first_supported_breach, witness)
        self.assertTrue(witness['prior_unknown'])
        q = QualityPath(START, END)
        q.mark(START, D('50000'), D('-6000'), conditional=True)
        self.assertIsNone(q.first_supported_breach)
        self.assertIsNotNone(q.first_conditional_breach)

    def test_native_approximate_cannot_pass_or_advance_anchors(self):
        s, a, p = native_context()
        r = lifecycle_probe(s, a, p, START+86400, balance='60000', quality='approximate')
        self.assertEqual(r['objectives']['technical_status'], 'blocked_by_data')
        self.assertFalse(r['objectives']['pass_ready'])
        self.assertEqual(r['phase'].daily_anchor, p.daily_anchor)
        self.assertEqual(r['phase'].virtual_time_utc, p.virtual_time_utc)

    def test_native_breach_priority_over_target(self):
        s, a, p = native_context()
        r = lifecycle_probe(s, a, p, START+3600, balance='55000', floating='-10001', quality='full_for_declared_model')
        self.assertEqual(r['attempt'].status, 'failed_breach')

    def test_native_minimum_days_flat_pending_and_phase2_reset(self):
        s, a, p = native_context()
        resume = {}
        def roll(at):
            nonlocal a, p, resume
            boundaries = calendar_oracle(phase_spec(), virtual_start_utc=utc(START),
                previous_virtual_utc=p.virtual_time_utc, current_virtual_utc=utc(at))['reset_boundaries']
            for boundary in boundaries:
                r = lifecycle_probe(s, a, p, int(boundary['boundary_utc'].timestamp()), balance=p.balance,
                    quality='full_for_declared_model', resume=resume, kind='calendar_boundary', positions=p.open_positions)
                a, p, resume = r['attempt'], r['phase'], r['resume_state']
        for day in range(4):
            roll(START+day*86400+3600)
            r = lifecycle_probe(s, a, p, START+day*86400+3600, balance='55000', qualifying=True,
                positions=1, quality='full_for_declared_model', resume=resume)
            a, p, resume = r['attempt'], r['phase'], r['resume_state']
            self.assertEqual(a.status, 'running')
        roll(START+4*86400)
        r = lifecycle_probe(s, a, p, START+4*86400, balance='55000', pending=1,
            quality='full_for_declared_model', resume=resume)
        self.assertEqual(r['attempt'].status, 'running')
        a, p, resume = r['attempt'], r['phase'], r['resume_state']
        r = lifecycle_probe(s, a, p, START+4*86400+1, balance='55000',
            quality='full_for_declared_model', resume=resume)
        a, p, resume = r['attempt'], r['phase'], r['resume_state']
        self.assertEqual(a.status, 'phase_passed')
        # Signal state is owned by the adapter, not the prop cash reducer.
        engine = GoldPrefix('125')
        engine.strategy.observe(Candle(START-14400, D('1000'), D('1002'), D('998'), D('1001')))
        original_indicator = engine.strategy.export_state()
        r = apply_prop_lifecycle_command(s, a, p, TransitionIntent(workspace_id='offline', session_id='B1',
            attempt_id='B1', profile_hash=p.profile_hash, intent_id='next', expected_revision=a.revision,
            event_sequence=p.last_event_sequence, action='next_phase'), resume_state=resume)
        self.assertEqual(r['phase'].phase_index, 2)
        self.assertEqual(r['phase'].balance, 50000)
        self.assertEqual(r['phase'].daily_anchor, 50000)
        self.assertEqual(r['phase'].qualifying_days, 0)
        self.assertEqual(engine.strategy.export_state(), original_indicator)

    def test_reward_earliest_not_periodic_flat_newaccount_and_loss_carry(self):
        for after, positions, orders, balance, expected in (
            (14*86400-1, 0, 0, '50100', 'waiting'),
            (14*86400, 1, 0, '50100', 'waiting'),
            (14*86400, 0, 1, '50100', 'waiting'),
            (14*86400, 0, 0, '49900', 'waiting'),
            (30*86400, 0, 0, '50019', 'waiting'),
            (30*86400, 0, 0, '50100', 'eligible_at_natural_flat')):
            result = reward_contract(START, START+after, balance=D(balance), positions=positions, pending=orders)
            self.assertEqual(result['status'], expected)
            self.assertIsNone(result['received_cash'])
        self.assertEqual(result['potential_reward'], 80)
        self.assertIsNone(result['approved_receivable'])
        self.assertEqual(reward_contract(START+30*86400, START+31*86400, balance=D('50100'))['status'], 'waiting')
        self.assertEqual(reward_contract(START, END, balance=D('50100'), contract_known=False)['status'], 'payout_contract_incomplete')


if __name__ == '__main__':
    unittest.main()
