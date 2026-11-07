"""Recompute frozen study arithmetic/fill bindings without invoking its simulator."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal as D, ROUND_HALF_UP
import json
from pathlib import Path

from sealed_m1_review import cash_sessions, digest


def inspect_scenario(result, pairs, sessions):
    if result['open_position'] is not None or result.get('pending_action') is not None:
        raise ValueError('open_or_pending_book_requires_separate_mark_review')
    slip = D(result['slippage_per_side'])
    decisions = {d['time_msc']: d for d in result['decisions']}
    flat_times = {stamps[-1] for stamps in sessions.values()}
    net_total = D(0)
    monthly = defaultdict(lambda: D(0))
    reasons = Counter()
    unresolved = []
    for trade in result['trades']:
        side, q = trade['side'], D(trade['quantity'])
        stamp = trade['entry_time_msc']
        decision = decisions[stamp-60000]
        if decision['side'] != side or not D('.01') <= q <= 50 or q % D('.01'):
            raise ValueError('entry_decision_or_lot_binding')
        bid, ask = pairs[stamp]
        entry = D(str(ask['open'] if side == 'BUY' else bid['open']))
        if entry != D(trade['entry_fill']):
            raise ValueError('entry_quote_binding')
        stop, price = D(trade['stop']), D(trade['exit_fill'])
        boundary = D(decision['lower' if side == 'BUY' else 'upper'])
        if abs(stop-boundary) >= D('.001') or (side == 'BUY' and stop > boundary) or (side == 'SELL' and stop < boundary):
            raise ValueError('stop_band_binding')
        distance = entry-stop if side == 'BUY' else stop-entry
        if distance <= 0 or (distance+D('.001')+2*slip+1)*q > 25:
            raise ValueError('planned_risk_exceeded')
        exit_stamp = trade['exit_interval_msc'][0]
        exit_row = pairs[exit_stamp][0 if side == 'BUY' else 1]
        reason = trade['reason']
        if reason == 'stop_loss':
            if price != stop or not D(str(exit_row['low'])) <= stop <= D(str(exit_row['high'])):
                raise ValueError('modeled_stop_not_in_bar')
        else:
            if price != D(str(exit_row['open'])):
                raise ValueError('exit_open_quote_binding')
            if reason == 'scheduled_cash_flat' and exit_stamp not in flat_times:
                raise ValueError('scheduled_flat_clock')
            if reason == 'stop_loss_gap' and not (price <= stop if side == 'BUY' else price >= stop):
                raise ValueError('gap_stop_direction')
        gross = (price-entry if side == 'BUY' else entry-price)*q
        net = (gross-(2*slip+1)*q).quantize(D('.01'), rounding=ROUND_HALF_UP)
        if net != D(trade['net_usd']) or net != D(str(trade['costs']['net_account'])):
            raise ValueError('trade_arithmetic')
        net_total += net
        day = next(day for day, stamps in sessions.items() if stamps[0] <= stamp <= stamps[-1])
        monthly[day[:7]] += net
        reasons[reason] += 1
        if trade['path_unresolved']:
            unresolved.append(trade['position_id'])
    if D(result['balance_usd']) != D(10000)+net_total:
        raise ValueError('cash_reconcile')
    if result['open_position'] is None and D(result['net_equity_usd']) != net_total:
        raise ValueError('closed_book_equity')
    if len(result['trades']) != result['closed_trades'] or result['entries'] != result['closed_trades']+(result['open_position'] is not None):
        raise ValueError('position_count')
    values = [D(t['net_usd']) for t in result['trades']]
    return dict(net_usd=str(net_total), closed_trades=len(values),
        wins=sum(v > 0 for v in values), losses=sum(v < 0 for v in values),
        top5_net_usd=str(sum(sorted(values, reverse=True)[:5], D(0))),
        monthly_net_usd={k: str(v) for k, v in monthly.items()},
        unresolved_positions=unresolved, reasons=dict(reasons))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('output_exists')
    manifest = json.loads((args.run/'manifest.json').read_text(encoding='utf-8'))
    snapshots = args.run/'source-snapshot'
    for number, (path, sha) in enumerate(manifest['source_pins'].items()):
        if digest(snapshots/f'{number:03}-{Path(path).name}') != sha:
            raise ValueError('snapshot_binding')
    if digest(snapshots/'protocol.md') != manifest['protocol_sha256'] or digest(snapshots/'calendar.json') != manifest['calendar_sha256']:
        raise ValueError('protocol_or_calendar_binding')
    quality = json.loads((args.run/'data-review.json').read_text(encoding='utf-8'))
    if digest(args.run/'data-review.json') != manifest['data_review_sha256']:
        raise ValueError('quality_binding')
    pairs = {}
    for q in range(1, 5):
        sides = []
        for side in ('bid', 'ask'):
            path = args.data_root/f'q{q}-{side}.json'
            seal = next(s for s in quality['source_seals'] if s['request'] == f'q{q}-{side}')
            if digest(path) != seal['sha256']:
                raise ValueError('raw_binding')
            sides.append(json.loads(path.read_text()))
        pairs.update({b['timestamp']: (b, a) for b, a in zip(*sides)})
    sessions = cash_sessions(json.loads((snapshots/'calendar.json').read_text(encoding='utf-8')))
    final = json.loads((args.run/'result.json').read_text(encoding='utf-8'))
    reviews = {}
    for row in final['results']:
        path = args.run/(row['scenario']+'.json')
        if digest(path) != row['sha256']:
            raise ValueError('result_binding')
        result = json.loads(path.read_text(encoding='utf-8'))
        if result['candidate'] != manifest['candidate']:
            raise ValueError('candidate_binding')
        reviews[row['scenario']] = inspect_scenario(result, pairs, sessions)
    output = dict(status='artifact_arithmetic_and_fill_bindings_verified', scenarios=reviews,
        reviewer_sha256=digest(Path(__file__)), manifest_sha256=digest(args.run/'manifest.json'),
        limits=['Separately implemented arithmetic checks, not independent model/reviewer sign-off.',
                'Does not certify intrabar ordering, missing paths, broker costs, edge or prop compliance.'])
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: {f: v[f] for f in ('net_usd', 'closed_trades', 'unresolved_positions')}
                      for k, v in reviews.items()}))


if __name__ == '__main__':
    main()
