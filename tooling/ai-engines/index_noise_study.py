"""Frozen US500 M1 development study; modeled fills, never broker/prop authority."""
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import json
import os
from pathlib import Path
import sys
import time

from forex_study_batch import configure_source_root
from sealed_m1_review import cash_sessions, digest, review

D = Decimal
CANDIDATE = 'us500-m1-noise14-opposite-hardstop-r025-v1'
MINUTE = 60000
LEGACY_COST_SCENARIO = 'us500-declared-commission05-v1'
FTMO_ZERO_COMMISSION = 'ftmo-index-zero-commission-public-20261108'
COMMISSION_SCENARIOS = {LEGACY_COST_SCENARIO: D('.5'), FTMO_ZERO_COMMISSION: D(0)}


def commission_for_scenario(cost_scenario):
    if not isinstance(cost_scenario, str) or cost_scenario not in COMMISSION_SCENARIOS:
        raise ValueError('unknown_index_cost_scenario')
    return COMMISSION_SCENARIOS[cost_scenario]


def bind_core(source_root: Path):
    configure_source_root(source_root)
    global protective_exit_for_bar, size_for_market_stop, CostModel, InstrumentSpec, calculate_round_trip_cost
    global event_logger, failure_details
    sys.path.insert(0, str(source_root/'scripts'))
    from forex_h4_pilot import event_logger, failure_details
    from trading_workspace_v2.execution_semantics import protective_exit_for_bar
    from trading_workspace_v2.research_market import size_for_market_stop
    from trading_workspace_v2.retained import CostModel, InstrumentSpec, calculate_round_trip_cost


def market(slippage, *, cost_scenario=LEGACY_COST_SCENARIO):
    commission = commission_for_scenario(cost_scenario)
    instrument = InstrumentSpec.from_mapping(dict(instrument_id='US500', asset_class='index_cfd',
        base_ccy='US500', quote_ccy='USD', account_ccy='USD', tick_size='.001', pip_size='1',
        contract_size='1', quantity_min='.01', quantity_step='.01', effective_from_utc='2022-01-01T00:00:00Z'))
    version = 'us500-declared-'+str(slippage) if cost_scenario == LEGACY_COST_SCENARIO else cost_scenario+'-slip-'+str(slippage)
    model = CostModel.from_mapping(dict(version=version, spread_basis='bid_ask_embedded',
        commission_per_side_account='0', commission_per_side_per_quantity_account=str(commission),
        minimum_fee_account='0', slippage_price_per_side=str(slippage), financing_account='0',
        quote_to_account_rate='1', account_ccy='USD', rounding_decimals=2))
    return instrument, model


def midpoint(pair, key):
    return (D(str(pair[0][key]))+D(str(pair[1][key])))/2


def bands(history, current_open, previous_close, slot):
    if len(history) != 14 or current_open is None or previous_close is None:
        return None
    if any(day['open'] is None or slot not in day['closes'] for day in history):
        return None
    sigma = sum((abs(day['closes'][slot]/day['open']-1) for day in history), D(0))/14
    return min(current_open, previous_close)*(1-sigma), max(current_open, previous_close)*(1+sigma)


def simulate(sessions, pairs, *, slippage, null_control=False, progress=None, deadline=None,
             cost_scenario=LEGACY_COST_SCENARIO):
    began, cpu = time.perf_counter(), time.process_time()
    instrument, model = market(slippage, cost_scenario=cost_scenario)
    history = deque(maxlen=14)
    previous_close = None
    balance = D('10000')
    position, pending = None, None
    trades, decisions, gaps, rejected = [], [], [], []
    count = unavailable = 0

    def close(pair, stamp, price, reason):
        nonlocal position, balance
        costs = calculate_round_trip_cost(model, position['side'], position['quantity'], instrument.contract_size,
                                          position['bid'], position['ask'], price, price)
        net = D(str(costs['net_account']))
        balance += net
        trades.append(dict(position_id=position['id'], side=position['side'],
            quantity=str(position['quantity']), entry_time_msc=position['time'],
            exit_time_msc=stamp if reason != 'stop_loss' else None,
            exit_interval_msc=[stamp, stamp+MINUTE] if reason == 'stop_loss' else [stamp, stamp],
            entry_fill=str(position['ask'] if position['side'] == 'BUY' else position['bid']),
            exit_fill=str(price), stop=str(position['stop']), net_usd=str(net), costs=costs,
            path_unresolved=position['path_unresolved'], reason=reason))
        position = None

    for number, (day, expected) in enumerate(sessions.items(), 1):
        if deadline is not None and time.perf_counter() > deadline:
            raise TimeoutError('index_study_deadline')
        current_open = midpoint(pairs[expected[0]], 'open') if expected[0] in pairs else None
        closes = {}
        for slot, stamp in enumerate(expected):
            pair = pairs.get(stamp)
            if pair is None:
                if position:
                    position['path_unresolved'] = True
                    gaps.append(dict(time_msc=stamp, position_id=position['id'], reason='missing_cash_minute'))
                if pending and pending['fill_time'] == stamp:
                    rejected.append(dict(time_msc=stamp, reason='pending_fill_minute_missing'))
                    pending = None
                continue
            bid, ask = D(str(pair[0]['open'])), D(str(pair[1]['open']))
            if position and slot == 0:
                position['path_unresolved'] = True
                gaps.append(dict(time_msc=stamp, position_id=position['id'], reason='unresolved_overnight'))
                close(pair, stamp, bid if position['side'] == 'BUY' else ask, 'delayed_cash_flat')
            if slot == len(expected)-1:
                pending = None
                if position:
                    close(pair, stamp, bid if position['side'] == 'BUY' else ask, 'scheduled_cash_flat')
            else:
                if position:
                    opening = bid if position['side'] == 'BUY' else ask
                    protection = protective_exit_for_bar(side=position['side'],
                        bar=dict(open=opening, high=opening, low=opening, close=opening),
                        stop_loss=position['stop'], take_profit=None, spread_price=0,
                        tick_size=instrument.tick_size, allow_open_gap=True)
                    if protection:
                        close(pair, stamp, protection['exit_price'], protection['reason'])
                action = None
                if pending and pending['fill_time'] <= stamp:
                    action, pending = pending, None
                if action:
                    if action['fill_time'] != stamp:
                        raise ValueError('pending_not_at_registered_fill_time')
                    if position and position['side'] != action['side']:
                        close(pair, stamp, bid if position['side'] == 'BUY' else ask, 'opposite_band')
                    if position is None:
                        side = action['side']
                        entry = ask if side == 'BUY' else bid
                        rounding = ROUND_FLOOR if side == 'BUY' else ROUND_CEILING
                        stop = (action['stop']/instrument.tick_size).to_integral_value(rounding=rounding)*instrument.tick_size
                        distance = entry-stop if side == 'BUY' else stop-entry
                        quantity = size_for_market_stop(distance, instrument=instrument, model=model) if distance > 0 else None
                        margin = entry*quantity*instrument.contract_size/10 if quantity else D(0)
                        if quantity is None or quantity > 50 or margin > balance:
                            rejected.append(dict(time_msc=stamp, reason='stop_minlot_maxlot_or_margin'))
                        else:
                            count += 1
                            position = dict(id=f'index-{count}', side=side, bid=bid, ask=ask,
                                            quantity=quantity, stop=stop, time=stamp, path_unresolved=False)
                if position:
                    prices = pair[0] if position['side'] == 'BUY' else pair[1]
                    protection = protective_exit_for_bar(side=position['side'],
                        bar={key: prices[key] for key in ('open', 'high', 'low', 'close')},
                        stop_loss=position['stop'], take_profit=None, spread_price=0,
                        tick_size=instrument.tick_size, allow_open_gap=True)
                    if protection:
                        close(pair, stamp, protection['exit_price'], protection['reason'])
            closes[slot] = midpoint(pair, 'close')
            # Slot29 closes at10:00; fill at10:01, after one full minute of delay.
            elapsed = slot+1
            if elapsed % 30 == 0 and 30 <= elapsed < len(expected)-1:
                boundary = bands(history, current_open, previous_close, slot)
                if boundary is None:
                    unavailable += 1
                    continue
                lower, upper = boundary
                side = 'BUY' if closes[slot] > upper else 'SELL' if closes[slot] < lower else None
                if null_control:
                    side = None
                decisions.append(dict(time_msc=stamp+MINUTE, side=side,
                    close=str(closes[slot]), lower=str(lower), upper=str(upper)))
                if side and (position is None or position['side'] != side):
                    pending = dict(side=side, stop=lower if side == 'BUY' else upper, fill_time=stamp+2*MINUTE)
        history.append(dict(open=current_open, closes=closes))
        previous_close = closes.get(len(expected)-1)
        if progress and number % 25 == 0:
            progress(number, len(sessions))
    if balance != D('10000')+sum((D(t['net_usd']) for t in trades), D(0)):
        raise ValueError('cash_does_not_reconcile')
    floating = D(0)
    if position:
        last = next((pairs[t] for t in reversed(list(pairs)) if t >= position['time']), None)
        if last is None:
            raise ValueError('missing_open_position_mark')
        floating = D(str(calculate_round_trip_cost(model, position['side'], position['quantity'], instrument.contract_size,
            position['bid'], position['ask'], D(str(last[0]['close'])), D(str(last[1]['close'])))['net_account']))
    return dict(candidate=CANDIDATE, slippage_per_side=str(slippage), null_control=null_control,
        cost_scenario=cost_scenario, commission_per_lot_per_side_usd=str(commission_for_scenario(cost_scenario)),
        net_equity_usd=str(balance+floating-10000), balance_usd=str(balance), floating_usd=str(floating),
        entries=count, closed_trades=len(trades), open_position=position, pending_action=pending,
        trades=trades, decisions=decisions, gap_events=gaps, rejected=rejected,
        unavailable_history_decisions=unavailable, wall_seconds=time.perf_counter()-began,
        cpu_seconds=time.process_time()-cpu, qualification='development_modeled_M1_only',
        intrabar_drawdown='not_certified', broker_spec_verified=False, prop_evaluated=False,
        broker_calls=0, model_calls=0)


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        stream.write('\n')


def main(*, candidate=CANDIDATE, simulator=simulate, include_extended=False,
         additional_sources=(), study_metadata=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--calendar', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cost-scenario', choices=tuple(COMMISSION_SCENARIOS), default=LEGACY_COST_SCENARIO)
    args = parser.parse_args()
    calendar = json.loads(args.calendar.read_text(encoding='utf-8'))
    year = calendar['year']
    if year not in range(2013,2025):
        raise ValueError('unregistered_year_holdout_closed')
    frozen_calendar = Path(__file__).with_name('fixtures')/f'nyse-{year}.json'
    if digest(args.calendar) != digest(frozen_calendar):
        raise ValueError('calendar_differs_from_frozen_year')
    bind_core(args.source_root)
    args.output.mkdir(exist_ok=False)
    lock = args.output/'controller.lock'
    lock.write_text(str(os.getpid()), encoding='utf-8')
    began = time.perf_counter()
    logger, handler = event_logger(args.output)
    event_sequence = 0
    current_stage = 'initializing'
    def status(stage, **extra):
        nonlocal event_sequence, current_stage
        event_sequence += 1
        current_stage = stage
        value = dict(stage=stage, updated_at_utc=datetime.now(timezone.utc).isoformat(),
                     pid=os.getpid(), sequence=event_sequence, level='error' if stage == 'failed' else 'info',
                     elapsed_seconds=time.perf_counter()-began, **extra)
        logger.info(json.dumps(value))
        (args.output/'progress.json').write_text(json.dumps(value), encoding='utf-8')
        (args.output/'PROGRESS.md').write_text(
            f'# {candidate} — nghiên cứu offline\n\n'
            f"Bước: {stage}; năm: {year}; đã chạy: {value['elapsed_seconds']:.1f}s.\n\n"
            +json.dumps(extra, ensure_ascii=False, indent=2)
            +'\n\nM1 modeled fills; không broker/prop qualification.\n', encoding='utf-8')
        print(json.dumps(value), flush=True)
    try:
        status('verifying_sealed_inputs')
        quality = review(args.data_root, args.calendar, .001)
        if quality['instrument'] != 'usa500idxusd' or quality['year'] != year:
            raise ValueError('unregistered_index_data')
        save(args.output/'data-review.json', quality)
        sessions = cash_sessions(calendar)
        pairs = {}
        needed = {t for stamps in sessions.values() for t in stamps}
        for q in range(1, 5):
            bid = json.loads((args.data_root/f'q{q}-bid.json').read_text())
            ask = json.loads((args.data_root/f'q{q}-ask.json').read_text())
            pairs.update({b['timestamp']: (b, a) for b, a in zip(bid, ask)
                          if include_extended or b['timestamp'] in needed})
        source_paths = {Path(__file__).resolve(), Path(__file__).with_name('sealed_m1_review.py'),
                        Path(__file__).with_name('forex_study_batch.py')}
        source_paths.update(Path(p).resolve() for p in additional_sources)
        source_paths.update(Path(m.__file__).resolve() for name, m in sys.modules.copy().items()
                            if (name.startswith('trading_workspace_v2.') or name == 'forex_h4_pilot')
                            and getattr(m, '__file__', None))
        pins = {str(p): digest(p) for p in sorted(source_paths)}
        save(args.output/'manifest.json', dict(candidate=candidate, year=year, source_pins=pins,
            protocol_sha256=digest(args.protocol), calendar_sha256=digest(args.calendar),
            data_review_sha256=digest(args.output/'data-review.json'), source_root=str(args.source_root.resolve()),
            frozen_at_utc=datetime.now(timezone.utc).isoformat(), python_version=sys.version,
            starting_balance_usd='10000', planned_risk_usd='25', contract_usd_per_point_per_lot='1',
            cost_scenario=args.cost_scenario,
            commission_per_lot_per_side_usd=str(commission_for_scenario(args.cost_scenario)),
            commission_evidence_scope=('public_current_commission_only_not_historical_broker_spec'
                if args.cost_scenario == FTMO_ZERO_COMMISSION else 'declared_scenario_only'),
            leverage='10', scenarios=['.25', '.75'],
            study_metadata=study_metadata or {}, holdout_read=False, broker_calls=0, model_calls=0))
        snapshots = args.output/'source-snapshot'
        snapshots.mkdir()
        (snapshots/'protocol.md').write_bytes(args.protocol.read_bytes())
        (snapshots/'calendar.json').write_bytes(args.calendar.read_bytes())
        for number, (path, sha) in enumerate(pins.items()):
            (snapshots/f'{number:03}-{Path(path).name}').write_bytes(Path(path).read_bytes())
        results = []
        for scenario, slip, control in [('reference', D('.25'), False), ('stress', D('.75'), False),
                                        ('null-control', D('.25'), True)]:
            status('simulating', scenario=scenario)
            result = simulator(sessions, pairs, slippage=slip, null_control=control, cost_scenario=args.cost_scenario,
                progress=lambda n, total: status('simulating', scenario=scenario,
                    **{(study_metadata or {}).get('progress_unit','sessions'):n},total=total),
                deadline=began+300)
            if (result.get('cost_scenario') != args.cost_scenario or
                    D(result.get('commission_per_lot_per_side_usd', '-1')) != commission_for_scenario(args.cost_scenario)):
                raise ValueError('simulator_ignored_registered_cost_scenario')
            save(args.output/f'{scenario}.json', result)
            results.append(dict(scenario=scenario, net_equity_usd=result['net_equity_usd'],
                entries=result['entries'], closed_trades=result['closed_trades'],
                gap_events=len(result['gap_events']), open_position=result['open_position'] is not None,
                sha256=digest(args.output/f'{scenario}.json')))
        if any(digest(Path(p)) != sha for p, sha in pins.items()):
            raise ValueError('source_changed_during_study')
        if results[-1]['entries'] or D(results[-1]['net_equity_usd']):
            raise ValueError('null_control_not_flat')
        save(args.output/'result.json', dict(status='completed_development_not_qualified',
             results=results, elapsed_seconds=time.perf_counter()-began))
        status('completed_development_not_qualified', results=results)
    except Exception as error:
        details = failure_details(error, current_stage)
        details['error_code'] = 'index_noise_study_failed'
        save(args.output/'failure.json', dict(**details, elapsed_seconds=time.perf_counter()-began))
        status('failed', error_type=type(error).__name__)
        raise
    finally:
        handler.close()
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
