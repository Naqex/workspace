"""Bounded, declared-cost Gold M1 diagnostic. No broker or qualified path claims.

Reuse Trader's indicator, sizing, stop, cost and money/calendar semantics. This
adapter owns only source ordering and evidence quality, not another prop engine.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / 'projects/trader/foundation_v2'
sys.path.insert(0, str(V2))
from trading_workspace_v2.forex_h4 import Candle, H4Builder
from trading_workspace_v2.forex_h4_candidates import METAL_SMA, ResearchH4Candidate
from trading_workspace_v2.research_market import MetalStudyMarket, size_for_market_stop
from trading_workspace_v2.retained import CostModel, InstrumentSpec, calculate_round_trip_cost
from trading_workspace_v2.replay_execution import ReplayOpenPosition
from trading_workspace_v2.execution_semantics import protective_exit_for_bar
from trading_workspace_v2.forex_pilot_risk import _stop_at_fill
from trading_workspace_v2.prop_session import (
    PropPhaseSpec, MoneyOracleInput, money_oracle, calendar_oracle,
    PropProfileSnapshot, PropSessionSnapshot, ChallengeAttemptSnapshot,
    PhaseStateSnapshot, PropLifecycleEvent, evaluate_prop_lifecycle_event,
)

UTC = timezone.utc
START = int(datetime(2010, 1, 1, tzinfo=UTC).timestamp())
END = int(datetime(2010, 4, 1, tzinfo=UTC).timestamp())
SEED = int(datetime(2009, 11, 1, tzinfo=UTC).timestamp())
RAW_SHA = 'd209df9a5ce871f1992eb312595ebef2c19a884c1fe0a1be6bfb76d86cf471b9'


def utc(at):
    return datetime.fromtimestamp(at, UTC)


def write_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, default=str, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def peak_working_set_bytes():
    if sys.platform != 'win32':
        return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    kernel, psapi = ctypes.WinDLL('kernel32'), ctypes.WinDLL('psapi')
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError('GetProcessMemoryInfo failed')
    return counters.PeakWorkingSetSize


def phase_spec(index=1):
    return PropPhaseSpec(phase_index=index, initial_capital='50000', currency='USD',
        profit_target={'threshold': {'percent': '10' if index == 1 else '5'}, 'basis': 'balance', 'comparator': 'gte'},
        daily_loss={'threshold': {'percent': '5'}, 'basis': 'equity', 'comparator': 'lt'},
        daily_anchor_basis='balance',
        overall_drawdown={'threshold': {'percent': '10'}, 'basis': 'equity', 'comparator': 'lt', 'kind': 'static'},
        reset_timezone='Europe/Prague', reset_order='reset_then_fees',
        min_qualifying_days=4, max_calendar_days=None, carry_policy='reset', position_policy='must_be_flat')


def native_context(start=START, end=END):
    profile = PropProfileSnapshot(profile_id='gold-B1-declared', terms_version='v1.1',
        profile_hash='sha256:gold-B1-declared', effective_from=date(2026, 11, 13),
        source_kind='custom', phases=[phase_spec(), phase_spec(2)])
    session = PropSessionSnapshot(workspace_id='offline', session_id='B1', profile=profile, status='running')
    attempt = ChallengeAttemptSnapshot(workspace_id='offline', session_id='B1', attempt_id='B1',
        profile_id=profile.profile_id, terms_version=profile.terms_version, profile_hash=profile.profile_hash,
        data_version=RAW_SHA, cost_version='legacy-stress40', engine_version='B1-M1', status='running',
        virtual_start_utc=utc(start), virtual_cutoff_utc=utc(end))
    phase = PhaseStateSnapshot(workspace_id='offline', session_id='B1', attempt_id='B1',
        profile_hash=profile.profile_hash, phase_index=1, initial_balance='50000', balance='50000',
        equity='50000', floating_pl='0', high_water_mark='50000', daily_anchor='50000',
        virtual_time_utc=utc(start), evaluation_quality='approximate')
    return session, attempt, phase


def lifecycle_probe(session, attempt, phase, at, *, balance, floating=0, quality='approximate',
                    qualifying=False, positions=0, pending=0, resume=None, kind='simulation_snapshot', swap=0):
    event = PropLifecycleEvent(workspace_id=attempt.workspace_id, session_id=attempt.session_id,
        attempt_id=attempt.attempt_id, profile_hash=attempt.profile_hash,
        operation_id=f'B1-{attempt.revision}', expected_revision=attempt.revision,
        event_sequence=phase.last_event_sequence + 1, kind=kind, virtual_time_utc=utc(at),
        balance_before_separate_costs=balance, floating_pl=floating, swap=swap,
        accounting='costs_separate' if swap else 'costs_included', open_positions=positions,
        pending_orders=pending, qualifying_day=qualifying, evaluation_quality=quality)
    return evaluate_prop_lifecycle_event(session, attempt, phase, event, resume_state=resume)


@dataclass(frozen=True)
class Minute:
    at: int
    o: D
    h: D
    l: D
    c: D


def read_prefix(path):
    """Full admitted-file hash, bounded parsing; never opens 2025-26 prices."""
    if digest(path) != RAW_SHA:
        raise ValueError('raw hash differs from frozen admitted source')
    result, previous = [], None
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream)
        if next(reader) != ['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume']:
            raise ValueError('M1 schema mismatch')
        for row in reader:
            if row[0] >= '2010.04.01':
                break
            at = int(datetime.strptime(row[0] + row[1], '%Y.%m.%d%H:%M:%S').replace(tzinfo=UTC).timestamp())
            values = [D(v) for v in row[2:6]]
            volume = D(row[6])
            o, h, l, c = values
            if (not SEED <= at < END or at % 60 or previous is not None and at <= previous
                    or any(not v.is_finite() or v <= 0 or v % D('.001') for v in values)
                    or not volume.is_finite() or volume < 0 or not l <= min(o, c) <= max(o, c) <= h):
                raise ValueError('M1 order/scope/grid/OHLC/volume invalid')
            result.append(Minute(at, *values))
            previous = at
    if not result or result[0].at >= START or result[-1].at < START:
        raise ValueError('missing canonical seed or evaluation prefix')
    return result


class QualityPath:
    def __init__(self, start, end):
        self.spec = phase_spec()
        self.start, self.end, self.clock = start, end, start
        self.anchor = D('50000')
        self.unknown = []
        self.resets = []
        self.first_supported_breach = self.first_conditional_breach = None
        self.points = dict(peak=D('50000'), peak_dd=D(0), daily_loss=D(0), static_loss=D(0))
        self.envelope = dict(self.points)

    def uncertain(self, reason, start, end):
        self.unknown.append(dict(reason=reason, start=start, end=end))

    def boundaries(self, through, balance, held, exact_quote=False):
        cal = calendar_oracle(self.spec, virtual_start_utc=utc(self.start),
            previous_virtual_utc=utc(self.clock), current_virtual_utc=utc(through))
        for item in cal['reset_boundaries']:
            at = int(item['boundary_utc'].timestamp())
            self.anchor = balance
            known = not held or exact_quote and at == through
            self.resets.append(dict(at=at, cash_anchor=str(balance), contemporaneous_price_known=known,
                price_quality='flat_no_quote_needed' if not held else 'M1_open_model' if known else 'missing'))
            if not known:
                self.uncertain('missing_reset_price', at, at)
        self.clock = through

    def mark(self, at, balance, floating, *, conditional=False, label='M1_point'):
        oracle = money_oracle(self.spec, MoneyOracleInput(initial_capital=D('50000'),
            daily_anchor=self.anchor, balance_before_separate_costs=balance, floating_pl=floating,
            high_water_mark=max(D('50000'), balance + floating)))
        metrics = self.envelope if conditional else self.points
        equity = oracle['equity']
        metrics['peak'] = max(metrics['peak'], equity)
        metrics['peak_dd'] = max(metrics['peak_dd'], metrics['peak'] - equity)
        metrics['daily_loss'] = max(metrics['daily_loss'], self.anchor - equity)
        metrics['static_loss'] = max(metrics['static_loss'], D('50000') - equity)
        if not conditional:
            self.envelope['peak'] = max(self.envelope['peak'], equity)
            for k in ('peak_dd', 'daily_loss', 'static_loss'):
                self.envelope[k] = max(self.envelope[k], metrics[k])
        if oracle['terminal_precedence']:
            field = 'first_conditional_breach' if conditional else 'first_supported_breach'
            if getattr(self, field) is None:
                setattr(self, field, dict(at=at, label=label, equity=str(equity),
                    daily_anchor=str(self.anchor), daily=oracle['daily_loss']['breached'],
                    overall=oracle['overall_drawdown']['breached'], prior_unknown=bool(self.unknown)))


class GoldPrefix:
    def __init__(self, budget, *, start=START, end=END):
        self.budget = D(budget)
        if self.budget not in (D('125'), D('200')):
            raise ValueError('B1 endpoints only')
        self.start, self.end = start, end
        market = MetalStudyMarket(starting_balance_usd='50000')
        base = market.execution('B1-stress', D('.2'), RAW_SHA, start * 1000)
        self.instrument = InstrumentSpec.from_mapping(base.instrument_spec)
        self.model = CostModel.from_mapping(base.cost_model)
        self.strategy, self.builder = ResearchH4Candidate(METAL_SMA), H4Builder()
        self.position = self.pending = self.hour = None
        self.balance = D('50000')
        self.finance = self.position_finance = D(0)
        self.counter = self.margin_rejections = self.rows = self.warmup_h4 = 0
        self.previous = self.last_bid = None
        self.path = QualityPath(start, end)
        self.trades, self.decisions, self.fees, self.events = [], [], [], []
        self.signal_trace, self.entry_dates = [], set()
        self.next_funding = int(utc(start).replace(hour=22, minute=0, second=0).timestamp())
        if self.next_funding < start:
            self.next_funding += 86400

    def net(self, bid):
        if self.position is None:
            return D(0)
        p = self.position
        return D(str(calculate_round_trip_cost(self.model, p.side, p.quantity,
            self.instrument.contract_size, p.entry_bid, p.entry_ask, bid, bid + 1)['net_account']))

    def close(self, at, bid, reason):
        p = self.position
        costs = calculate_round_trip_cost(self.model, p.side, p.quantity, self.instrument.contract_size,
            p.entry_bid, p.entry_ask, bid, bid + 1)
        value = D(str(costs['net_account']))
        self.balance += value
        self.trades.append(dict(position_id=p.position_id, side=p.side, quantity=str(p.quantity),
            entry_time_msc=p.opened_time_utc * 1000, exit_time_msc=at, reason=reason,
            entry_fill=str(p.entry_fill), exit_fill=str(bid if p.side == 'BUY' else bid + 1),
            price_net_usd=str(value), timed_financing_usd=str(self.position_finance),
            net_usd=str(value - self.position_finance), costs=costs))
        self.position, self.position_finance = None, D(0)
        self.path.mark(at, self.balance, D(0), label='settled_cash')

    def scheduled(self, through, exact_quote=False):
        # Cash anchor is exact even when no price exists at a reset. Process each
        # funding boundary separately so a later reset sees already-posted cash.
        while self.next_funding <= through:
            at = self.next_funding
            self.path.boundaries(at, self.balance, self.position is not None,
                exact_quote=exact_quote and at == through)
            if utc(at).weekday() < 5 and self.position is not None:
                multiplier = 3 if utc(at).weekday() == 2 else 1
                debit = (40 * self.position.quantity * multiplier).quantize(D('.01'), rounding=ROUND_HALF_UP)
                self.balance -= debit
                self.finance += debit
                self.position_finance += debit
                self.fees.append(dict(at=at, event_id=f'funding-{at}', debit_usd=str(debit),
                    position_id=self.position.position_id, multiplier=multiplier))
            self.next_funding += 86400
        self.path.boundaries(through, self.balance, self.position is not None, exact_quote=exact_quote)

    def finalize_hour(self):
        hour = self.hour
        if hour is None:
            return
        bar = self.builder.add(Candle(hour[0], *[p + D('.5') for p in hour[1:]]))
        self.hour = None
        if bar is None:
            return
        signal, distance = self.strategy.observe(bar,
            side=self.position.side if self.position else None,
            position_id=self.position.position_id if self.position else None)
        if bar.timestamp < self.start:
            self.warmup_h4 += 1
            return
        at = bar.timestamp + 14400
        self.signal_trace.append(dict(at=at, atr=str(self.strategy.atr),
            difference=str(self.strategy.previous_difference), signal=signal))
        if signal:
            qty = size_for_market_stop(distance, instrument=self.instrument, model=self.model,
                budget=self.budget) if signal != 'EXIT' else None
            action = dict(time=at, signal=signal, distance=str(distance),
                quantity=str(qty) if qty is not None else None,
                status='skipped_minimum_lot' if signal != 'EXIT' and qty is None else 'queued')
            self.decisions.append(action)
            if action['status'] == 'queued':
                self.pending = action

    def fill(self, at, bid):
        action, self.pending = self.pending, None
        if action is None:
            return
        if at < action['time']:
            raise ValueError('fill before intent')
        if action['signal'] == 'EXIT':
            if self.position:
                self.close(at * 1000, bid, 'strategy_exit')
            return
        if self.position:
            raise ValueError('entry conflicts with held position')
        side, qty = action['signal'], D(action['quantity'])
        entry = bid + 1 if side == 'BUY' else bid
        # Frozen comparator uses fixed starting collateral at leverage10, not
        # FTMO target margin or dynamic available broker equity.
        if entry * qty * 100 / 10 > 50000:
            self.margin_rejections += 1
            return
        self.counter += 1
        self.position = ReplayOpenPosition(position_id=f'B1-{self.counter}', source_operation_id=f'intent-{len(self.decisions)}',
            side=side, quantity=qty, entry_bid=bid, entry_ask=bid + 1, entry_fill=entry,
            stop_loss=_stop_at_fill(side, entry, D(action['distance']), self.instrument.tick_size),
            take_profit=None, opened_cursor_index=self.rows, opened_time_utc=at)
        self.events.append(dict(kind='entry', at=at, position=self.position.model_dump(mode='json'),
            intent_time=action['time']))
        self.entry_dates.add(utc(at).astimezone(ZoneInfo('Europe/Prague')).date().isoformat())

    def step(self, bar):
        if self.previous is not None and bar.at <= self.previous:
            raise ValueError('source cursor not increasing')
        if self.hour is not None and bar.at // 3600 * 3600 != self.hour[0]:
            self.finalize_hour()
        if bar.at >= self.start:
            self.rows += 1
            if self.previous is not None and bar.at > self.previous + 60 and self.position:
                self.path.uncertain('held_source_gap', self.previous + 60, bar.at)
            self.scheduled(bar.at, exact_quote=True)
            self.path.mark(bar.at * 1000, self.balance, self.net(bar.o), label='M1_open_declared_ask')
            if self.position:
                p = self.position
                opening = bar.o if p.side == 'BUY' else bar.o + 1
                gap = protective_exit_for_bar(side=p.side, bar=dict.fromkeys(('open','high','low','close'), opening),
                    stop_loss=p.stop_loss, take_profit=None, spread_price=0, tick_size='.001', allow_open_gap=True)
                if gap:
                    self.close(bar.at * 1000, D(gap['exit_price']) - (1 if p.side == 'SELL' else 0), gap['reason'])
            self.fill(bar.at, bar.o)
            self.path.mark(bar.at * 1000, self.balance, self.net(bar.o), label='after_intent')
            if self.position:
                p = self.position
                prices = [v + (1 if p.side == 'SELL' else 0) for v in (bar.o, bar.h, bar.l, bar.c)]
                stop = protective_exit_for_bar(side=p.side, bar=dict(zip(('open','high','low','close'), prices)),
                    stop_loss=p.stop_loss, take_profit=None, spread_price=0, tick_size='.001', allow_open_gap=True)
                if stop:
                    self.path.uncertain('unordered_stop_minute', bar.at, bar.at + 60)
                    # Neither the low after liquidation nor the high before an
                    # unknown stop time is a witnessed held-position extremum.
                    self.close((bar.at + 60) * 1000 - 1,
                        D(stop['exit_price']) - (1 if p.side == 'SELL' else 0), stop['reason'])
                else:
                    favorable, adverse = (bar.h, bar.l) if p.side == 'BUY' else (bar.l, bar.h)
                    self.path.mark(bar.at * 1000, self.balance, self.net(favorable), conditional=True,
                        label='held_M1_extremum_unordered')
                    self.path.mark(bar.at * 1000, self.balance, self.net(adverse), conditional=True,
                        label='held_M1_extremum_unordered')
                    self.path.mark((bar.at + 60) * 1000 - 1, self.balance, self.net(bar.c), label='M1_close_time_proxy')
            else:
                self.path.mark((bar.at + 60) * 1000 - 1, self.balance, D(0), label='flat_cash')
            self.last_bid = bar.c
        bucket = bar.at // 3600 * 3600
        if self.hour is None:
            self.hour = [bucket, bar.o, bar.h, bar.l, bar.c]
        else:
            self.hour[2], self.hour[3], self.hour[4] = max(self.hour[2], bar.h), min(self.hour[3], bar.l), bar.c
        self.previous = bar.at

    def finish(self):
        if self.hour is not None and self.hour[0] + 3600 <= self.end:
            self.finalize_hour()
        self.scheduled(self.end - 1)
        if self.position and self.previous + 60 < self.end:
            self.path.uncertain('open_right_censored_gap', self.previous + 60, self.end)
        expected = D('50000') + sum((D(t['price_net_usd']) for t in self.trades), D(0)) - self.finance
        if self.balance != expected:
            raise ValueError('cash identity failed')

    def checkpoint(self):
        return dict(budget=str(self.budget), start=self.start, end=self.end,
            strategy=self.strategy.export_state().model_dump(mode='json'), builder=self.builder.export_state().model_dump(mode='json'),
            position=self.position.model_dump(mode='json') if self.position else None,
            pending=self.pending, hour=self.hour, balance=self.balance, finance=self.finance,
            position_finance=self.position_finance, counter=self.counter, margin_rejections=self.margin_rejections,
            rows=self.rows, warmup_h4=self.warmup_h4, previous=self.previous, last_bid=self.last_bid,
            next_funding=self.next_funding, trades=self.trades, decisions=self.decisions, fees=self.fees,
            events=self.events, signal_trace=self.signal_trace, entry_dates=sorted(self.entry_dates),
            path={k: v for k, v in vars(self.path).items() if k != 'spec'})

    @classmethod
    def restore(cls, raw):
        result = cls(raw['budget'], start=raw['start'], end=raw['end'])
        result.strategy = ResearchH4Candidate.from_state(raw['strategy'])
        result.builder = H4Builder.from_state(raw['builder'])
        result.position = ReplayOpenPosition.model_validate(raw['position']) if raw['position'] else None
        for key in ('balance', 'finance', 'position_finance', 'last_bid'):
            setattr(result, key, D(raw[key]) if raw[key] is not None else None)
        result.hour = [raw['hour'][0], *map(D, raw['hour'][1:])] if raw['hour'] else None
        for key in ('pending', 'counter', 'margin_rejections', 'rows', 'warmup_h4', 'previous', 'next_funding',
                    'trades', 'decisions', 'fees', 'events', 'signal_trace'):
            setattr(result, key, raw[key])
        result.entry_dates = set(raw['entry_dates'])
        for key, val in raw['path'].items():
            if key == 'anchor':
                val = D(val)
            if key in ('points', 'envelope'):
                val = {k: D(v) for k, v in val.items()}
            setattr(result.path, key, val)
        return result

    def result(self):
        s, a, p = native_context(self.start, self.end)
        probe = lifecycle_probe(s, a, p, self.end - 1, balance=self.balance,
            floating=self.net(self.last_bid), positions=int(self.position is not None), pending=int(self.pending is not None))
        return dict(schema='gold-B1-prefix-v1', risk_budget_usd=str(self.budget), initial_balance_usd='50000',
            net_cash_usd=str(self.balance - 50000), floating_usd=str(self.net(self.last_bid)),
            net_marked_equity_usd=str(self.balance + self.net(self.last_bid) - 50000),
            mark_time_proxy_msc=(self.previous + 60) * 1000 - 1, mark_staleness_seconds=self.end - self.previous - 60,
            closed_trades=len(self.trades), entries=self.counter, margin_rejections=self.margin_rejections,
            funding_debit_usd=str(self.finance), warmup_h4=self.warmup_h4, observed_m1_rows=self.rows,
            calendar_minutes=(self.end-self.start)//60, calendar_coverage_pct=str(D(self.rows)*100/D((self.end-self.start)//60)),
            qualifying_entry_dates=sorted(self.entry_dates), point_metrics=self.path.points,
            conditional_held_minute_envelope=self.path.envelope,
            first_supported_breach=self.path.first_supported_breach, first_conditional_breach=self.path.first_conditional_breach,
            unknown_intervals=self.path.unknown, resets=self.path.resets,
            lifecycle=probe['objectives'], lifecycle_attempt_status=probe['attempt'].status,
            qualification='INCONCLUSIVE_M1_MODEL_AND_GAPS_NO_FULL_PATH_SURVIVAL',
            trades=self.trades, decisions=self.decisions, financing_events=self.fees,
            open_position=self.position.model_dump(mode='json') if self.position else None, pending=self.pending,
            signal_trace=self.signal_trace, broker_calls=0, source_root=str(V2))


def reward_contract(first_trade, at, *, balance, positions=0, pending=0, contract_known=True):
    """Synthetic contract fixture only; potential reward is never approved cash."""
    if not contract_known:
        return dict(status='payout_contract_incomplete', received_cash=None)
    due = first_trade + 14 * 86400
    eligible = at >= due and positions == 0 and pending == 0 and balance - D('50000') >= 20
    return dict(status='eligible_at_natural_flat' if eligible else 'waiting', eligibility_time=due,
        eligible_profit=max(D(0), balance-D('50000')) if eligible else D(0),
        potential_reward=(balance-D('50000'))*D('.80') if eligible else D(0),
        approved_receivable=None, received_cash=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--protocol', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    registration = json.loads((args.out / 'registration.json').read_text(encoding='utf-8-sig'))
    if digest(args.protocol) != registration['protocol_sha256']:
        raise ValueError('registered protocol changed')
    manifest = json.loads((args.out / 'source-binding.json').read_text(encoding='utf-8-sig'))
    for relative, sha in manifest['native_modules'].items():
        if digest(V2 / relative) != sha:
            raise ValueError('native source binding changed: ' + relative)
    if digest(__file__) != manifest['harness_sha256']:
        raise ValueError('harness source changed after registration')
    if digest(args.out / 'source-binding.json') != registration['source_binding_sha256']:
        raise ValueError('source binding receipt changed')
    if any((args.out / f'prefix-{b}.json').exists() for b in (125, 200)):
        raise ValueError('completed numerical output exists; no implicit rerun')
    stage, started = 'prepare', time.perf_counter()
    try:
        rows = read_prefix(args.raw)
        prep = time.perf_counter() - started
        for budget in ('125', '200'):
            stage, began, cpu = f'prefix-{budget}', time.perf_counter(), time.process_time()
            engine = GoldPrefix(budget)
            for index, row in enumerate(rows):
                if index % 10000 == 0:
                    write_json(args.out / 'status.json', dict(stage=stage, row=index, total=len(rows), pid=__import__('os').getpid()))
                    write_json(args.out / f'checkpoint-{budget}.json', engine.checkpoint())
                    print(json.dumps(dict(stage=stage, row=index, total=len(rows))), flush=True)
                    if (args.out / 'CANCEL').exists():
                        raise RuntimeError('cancel_requested')
                    if time.perf_counter() - began > 900:
                        raise TimeoutError('900s_case_deadline')
                engine.step(row)
            engine.finish()
            result = engine.result()
            result['timing'] = dict(prep_shared_wall_seconds=prep, loop_and_metrics_wall_seconds=time.perf_counter()-began,
                cpu_seconds=time.process_time()-cpu, process_peak_working_set_bytes=peak_working_set_bytes())
            result['binding'] = dict(raw_sha256=RAW_SHA, protocol_sha256=digest(args.protocol),
                harness_sha256=digest(__file__), source_root=str(V2),
                source_binding_sha256=digest(args.out / 'source-binding.json'))
            write_json(args.out / f'prefix-{budget}.json', result)
            write_json(args.out / f'checkpoint-{budget}.json', engine.checkpoint())
        write_json(args.out / 'status.json', dict(stage='completed_bounded_only', wall_seconds=time.perf_counter()-started))
    except BaseException as exc:
        write_json(args.out / f'failure-{time.time_ns()}.json', dict(stage=stage, error_type=type(exc).__name__, code=str(exc),
            wall_seconds=time.perf_counter()-started))
        raise


if __name__ == '__main__':
    main()
