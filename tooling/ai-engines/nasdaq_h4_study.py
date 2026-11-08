"""Registered NASDAQ H4 research with separate-side H1 proxies, never broker orders."""
from collections import deque
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path
import time

from forex_study_batch import configure_source_root

HOUR = 3_600_000
H4 = 4 * HOUR
DAY = 24 * HOUR
GRID = D('.001')
CANDIDATE = 'nasdaq100-h4-bid-sma20-80-atr14x2-r025-h1proxy-v1'
SCENARIOS = {'reference': (D('.25'), D('.08')), 'stress': (D('.75'), D('.16'))}


def bind_core(source_root: Path):
    configure_source_root(source_root)
    global Candle, advance_atr14, protective_exit_for_bar, size_for_market_stop
    global InstrumentSpec, CostModel, calculate_round_trip_cost
    from trading_workspace_v2.forex_h4 import Candle, advance_atr14
    from trading_workspace_v2.execution_semantics import protective_exit_for_bar
    from trading_workspace_v2.research_market import size_for_market_stop
    from trading_workspace_v2.retained import InstrumentSpec, CostModel, calculate_round_trip_cost


def market(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('unregistered_nasdaq_cost_scenario')
    slip, annual = SCENARIOS[scenario]
    instrument = InstrumentSpec.from_mapping(dict(instrument_id='USATECH.IDX/USD',
        asset_class='index_cfd', base_ccy='NASDAQ100', quote_ccy='USD', account_ccy='USD',
        contract_size='1', tick_size=str(GRID), pip_size='1', quantity_min='.01',
        quantity_step='.01', effective_from_utc='2019-01-01T00:00:00Z'))
    model = CostModel.from_mapping(dict(version='nasdaq-declared-'+scenario+'-v1',
        spread_basis='bid_ask_embedded', commission_per_side_account='0',
        commission_per_side_per_quantity_account='0', minimum_fee_account='0',
        slippage_price_per_side=str(slip), financing_account='0',
        quote_to_account_rate='1', account_ccy='USD', rounding_decimals=2))
    return instrument, model, annual


def validate_pairs(pairs):
    stamps = list(pairs)
    if not stamps or any(type(t) is not int or t < 0 or t % HOUR for t in stamps):
        raise ValueError('invalid_H1_clock')
    if stamps != sorted(set(stamps)):
        raise ValueError('unordered_or_duplicate_hours')
    for stamp, pair in pairs.items():
        if len(pair) != 2:
            raise ValueError('missing_side')
        for row in pair:
            if row['timestamp'] != stamp:
                raise ValueError('side_clock_mismatch')
            values = {k: D(str(row[k])) for k in ('open', 'high', 'low', 'close')}
            if any(not p.is_finite() or p <= 0 or p % GRID for p in values.values()):
                raise ValueError('invalid_source_price_grid')
            if not values['low'] <= min(values['open'], values['close']) <= max(values['open'], values['close']) <= values['high']:
                raise ValueError('invalid_source_OHLC')
        if any(D(str(pair[1][k])) < D(str(pair[0][k])) for k in ('open', 'close')):
            raise ValueError('crossed_pair_endpoints')


def completed_h4(pairs):
    """Only Bid chart bars whose four source hours actually exist."""
    groups, result = {}, {}
    for stamp, (bid, _) in pairs.items():
        groups.setdefault(stamp // H4 * H4, []).append((stamp, bid))
    for begin, rows in groups.items():
        if [t for t, _ in rows] != [begin + n * HOUR for n in range(4)]:
            continue
        result[begin + H4] = Candle(timestamp=begin//1000,
            open=D(str(rows[0][1]['open'])), high=max(D(str(r['high'])) for _, r in rows),
            low=min(D(str(r['low'])) for _, r in rows), close=D(str(rows[-1][1]['close'])))
    return result


class BidSmaSignal:
    def __init__(self):
        self.history = deque(maxlen=80)
        self.seed, self.atr, self.previous_difference = [], None, None

    def observe(self, candle, side=None):
        previous = self.history[-1].close if self.history else None
        self.atr = advance_atr14(candle, previous, self.seed, self.atr)
        self.history.append(candle)
        action = difference = None
        if len(self.history) == 80:
            closes = [c.close for c in self.history]
            difference = sum(closes[-20:], D(0))/20 - sum(closes, D(0))/80
            if (side == 'BUY' and difference <= 0) or (side == 'SELL' and difference >= 0):
                action = 'EXIT'
            elif side is None and self.previous_difference is not None:
                if self.previous_difference <= 0 < difference:
                    action = 'BUY'
                elif self.previous_difference >= 0 > difference:
                    action = 'SELL'
            self.previous_difference = difference
        return dict(side=action, distance=self.atr*2 if self.atr is not None else None,
                    difference=difference, completed_count=len(self.history), atr=self.atr)


def simulate(pairs, *, start, end, scenario, progress=None, deadline=None):
    began, cpu = time.perf_counter(), time.process_time()
    validate_pairs(pairs)
    if (type(start) is not int or type(end) is not int or start % DAY or end % DAY
            or end <= start or any(t >= end for t in pairs)):
        raise ValueError('invalid_evaluation_interval')
    instrument, model, annual = market(scenario)
    candles = completed_h4(pairs)
    signal = BidSmaSignal()
    for known, candle in candles.items():
        if known <= start:
            signal.observe(candle)
    times = [t for t in pairs if t >= start]
    if not times:
        raise ValueError('empty_evaluation_book')
    position = pending = None
    balance, entries = D(10000), 0
    decisions, trades, funding, gaps, rejected = [], [], [], [], []
    previous = None
    charge_time = start + 22*HOUR

    def post_funding(boundary):
        nonlocal charge_time, balance
        while charge_time <= boundary:
            if position is not None and position['entry_time_msc'] < charge_time:
                debit = (position['entry_quote']*position['quantity']*instrument.contract_size*annual/365).quantize(D('.01'), rounding=ROUND_HALF_UP)
                balance -= debit
                position['funding_usd'] += debit
                funding.append(dict(time_msc=charge_time, position_id=position['id'], debit_usd=debit))
            charge_time += DAY

    def close(stamp, price, reason):
        nonlocal balance, position
        cost = calculate_round_trip_cost(model, position['side'], position['quantity'], instrument.contract_size,
            position['bid'], position['ask'], price, price)
        net = D(str(cost['net_account']))
        balance += net
        trades.append(dict(**position, exit_quote=price, exit_time_msc=None if reason == 'stop_loss' else stamp,
            exit_interval_msc=[stamp, stamp+HOUR] if reason == 'stop_loss' else [stamp, stamp],
            reason=reason, price_net_usd=net, net_usd=net-position['funding_usd'], costs=cost))
        position = None

    def protect(stamp, row, *, opening=False):
        if position is None:
            return
        bar = {k: row['open'] if opening else row[k] for k in ('open', 'high', 'low', 'close')}
        hit = protective_exit_for_bar(side=position['side'], bar=bar, stop_loss=position['stop'],
            take_profit=None, spread_price=0, tick_size=GRID, allow_open_gap=True)
        if hit:
            close(stamp, hit['exit_price'], hit['reason'])

    for i, stamp in enumerate(times):
        if i % 128 == 0:
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError('nasdaq_study_deadline')
            if progress:
                progress(i, len(times))
        pair = pairs[stamp]
        post_funding(stamp)
        if position and previous is not None and stamp != previous+HOUR:
            position['path_unresolved'] = True
            gaps.append(dict(after_time_msc=previous, before_time_msc=stamp, position_id=position['id']))
        if position:
            protect(stamp, pair[0 if position['side'] == 'BUY' else 1], opening=True)
        action = None
        if pending and pending['fill_time_msc'] <= stamp:
            action, pending = pending, None
            if action['fill_time_msc'] != stamp:
                rejected.append(dict(**action, reason='missing_exact_fill_hour'))
                action = None
        bid, ask = D(str(pair[0]['open'])), D(str(pair[1]['open']))
        if action:
            expected_id = position['id'] if position else None
            if action['position_id'] != expected_id:
                rejected.append(dict(**action, reason='position_changed_before_fill'))
            elif action['side'] == 'EXIT':
                if position:
                    close(stamp, bid if position['side'] == 'BUY' else ask, 'strategy_exit')
            elif position is None:
                side, distance = action['side'], action['distance']
                quantity = size_for_market_stop(distance, instrument=instrument, model=model)
                entry = ask if side == 'BUY' else bid
                stop = entry-distance if side == 'BUY' else entry+distance
                stop = (stop/GRID).to_integral_value(rounding=ROUND_FLOOR if side == 'BUY' else ROUND_CEILING)*GRID
                margin = entry*quantity*instrument.contract_size/10 if quantity else D(0)
                if stop <= 0 or quantity is None or quantity > 50 or margin > balance:
                    rejected.append(dict(**action, reason='invalid_stop_min_max_unit_or_margin'))
                else:
                    entries += 1
                    position = dict(id=f'nasdaq-{entries}', side=side, quantity=quantity,
                        bid=bid, ask=ask, entry_quote=entry, stop=stop,
                        entry_time_msc=stamp, decision_time_msc=action['decision_time_msc'],
                        funding_usd=D(0), path_unresolved=False)
        if position:
            protect(stamp, pair[0 if position['side'] == 'BUY' else 1])
        known = stamp+HOUR
        if known in candles:
            observed = signal.observe(candles[known], side=position['side'] if position else None)
            decisions.append(dict(time_msc=known, **observed, position_id=position['id'] if position else None))
            if observed['side']:
                if pending:
                    raise ValueError('unexpected_overlapping_pending_actions')
                pending = dict(**observed, decision_time_msc=known, fill_time_msc=known+HOUR,
                               position_id=position['id'] if position else None)
        previous = stamp
    post_funding(end-1)
    total_funding = sum((f['debit_usd'] for f in funding), D(0))
    if balance != D(10000)+sum((t['price_net_usd'] for t in trades), D(0))-total_funding:
        raise ValueError('nasdaq_cash_reconciliation')
    floating = D(0)
    if position:
        pair = pairs[times[-1]]
        floating = D(str(calculate_round_trip_cost(model, position['side'], position['quantity'], instrument.contract_size,
            position['bid'], position['ask'], pair[0]['close'], pair[1]['close'])['net_account']))
        if times[-1]+HOUR < end:
            position['path_unresolved'] = True
            gaps.append(dict(after_time_msc=times[-1], before_time_msc=end, position_id=position['id'], reason='unobserved_final_tail'))
    return dict(candidate=CANDIDATE, scenario=scenario, source_instrument='USATECH.IDX/USD',
        qualification='development_separate_side_H1_model_only', broker_spec_verified=False,
        prop_evaluated=False, clean_oos=False, broker_calls=0, model_calls=0, execution_authorized=False,
        balance_usd=balance, floating_usd=floating, net_equity_usd=balance+floating-10000,
        entries=entries, closed_trades=len(trades), open_position=position, pending_action=pending,
        trades=trades, decisions=decisions, funding_events=funding, funding_total_usd=total_funding,
        gap_events=gaps, rejected=rejected, start_time_msc=start, end_time_msc=end,
        last_mark_time_msc=times[-1]+HOUR, complete_H4_evaluation_count=len(decisions),
        wall_seconds=time.perf_counter()-began, cpu_seconds=time.process_time()-cpu)
