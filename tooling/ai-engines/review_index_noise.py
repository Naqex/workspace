"""Recompute frozen study arithmetic/fill bindings without invoking its simulator."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal as D, ROUND_HALF_UP
import json
from pathlib import Path

from sealed_m1_review import cash_sessions, digest


def commission_for_result(result, manifest=None):
    # Configuration is checked here without calling the simulator's cost helper.
    declared = {'us500-declared-commission05-v1': D('.5'),
                'ftmo-index-zero-commission-public-20261108': D(0)}
    scenario = result.get('cost_scenario', 'us500-declared-commission05-v1')
    commission = D(str(result.get('commission_per_lot_per_side_usd', '.5')))
    if not commission.is_finite() or scenario not in declared or commission != declared[scenario]:
        raise ValueError('result_commission_scenario_binding')
    if manifest is not None:
        registered = manifest.get('cost_scenario', 'us500-declared-commission05-v1')
        amount = D(str(manifest.get('commission_per_lot_per_side_usd', '.5')))
        if registered != scenario or not amount.is_finite() or amount != commission:
            raise ValueError('manifest_result_commission_binding')
    return commission


def inspect_funded_scenario(result,pairs,sessions):
    slip,rate=D(result['slippage_per_side']),D(result['funding_per_lot_per_day'])
    commission=commission_for_result(result)
    decisions={d['time_msc']:d for d in result['decisions']}
    positions={}
    for trade in result['trades']:
        identity=trade['position_id']
        if identity in positions:raise ValueError('duplicate_position_id')
        positions[identity]=trade
    opened=result['open_position']
    if opened is not None:
        if opened['id'] in positions:raise ValueError('position_open_and_closed')
        positions[opened['id']]=opened
    funding_by_id=defaultdict(lambda:D(0))
    seen=set()
    for event in result['funding_events']:
        identity,at=event['position_id'],event['time_msc']
        pos=positions[identity];quantity=D(pos['quantity'])
        entry=pos.get('entry_time_msc',pos.get('time'))
        exit_at=pos['exit_interval_msc'][0] if 'exit_interval_msc' in pos else result.get('evaluation_end_msc') or max(pairs)+60000
        if at%86400000 or not entry<at<=exit_at or (identity,at) in seen:
            raise ValueError('funding_clock_or_position_binding')
        seen.add((identity,at))
        debit=(quantity*rate).quantize(D('.01'),rounding=ROUND_HALF_UP)
        if debit!=D(event['debit_usd']):raise ValueError('funding_arithmetic')
        funding_by_id[identity]+=debit
    net_price_total=D(0)
    for identity,pos in positions.items():
        entry_at=pos.get('entry_time_msc',pos.get('time'))
        decision=decisions[entry_at-60000]
        quantity=D(pos['quantity']);side=pos['side']
        entry=D(str(pairs[entry_at][1 if side=='BUY' else 0]['open']))
        if 'entry_fill' in pos:
            if D(pos['entry_fill'])!=entry:raise ValueError('funded_entry_quote_binding')
        elif any(D(pos[side_name])!=D(str(pairs[entry_at][number]['open']))
                 for number,side_name in enumerate(('bid','ask'))):
            raise ValueError('funded_entry_quote_binding')
        if decision['side']!=side or not D('.01')<=quantity<=50 or quantity%D('.01'):
            raise ValueError('funded_entry_or_quantity')
        distance=D(decision['stop_distance']);stop=D(pos['stop'])
        actual=entry-stop if side=='BUY' else stop-entry
        if not 0<=actual-distance<D('.001') or (actual+2*slip+2*commission)*quantity>25:
            raise ValueError('funded_stop_or_risk')
        claimed=D(pos['funding_usd'] if 'funding_usd' in pos else pos['funding'])
        funding_end=(pos['exit_interval_msc'][0]+1 if 'exit_interval_msc' in pos
                     else result.get('evaluation_end_msc') or max(pairs)+60000)
        expected_times=set(range((entry_at//86400000+1)*86400000,funding_end,86400000))
        actual_times={at for pid,at in seen if pid==identity}
        if expected_times!=actual_times:raise ValueError('missing_or_extra_calendar_funding')
        if claimed!=funding_by_id[identity]:raise ValueError('position_funding_sum')
        if 'exit_interval_msc' not in pos:continue
        at=pos['exit_interval_msc'][0];price=D(pos['exit_fill']);row=pairs[at][0 if side=='BUY' else 1]
        if pos['reason']=='stop_loss':
            if price!=stop or not D(str(row['low']))<=stop<=D(str(row['high'])):raise ValueError('funded_stop_fill')
        elif price!=D(str(row['open'])):raise ValueError('funded_exit_quote')
        elif pos['reason']=='stop_loss_gap' and not (price<=stop if side=='BUY' else price>=stop):
            raise ValueError('funded_gap_stop_direction')
        gross=(price-entry if side=='BUY' else entry-price)*quantity
        price_net=(gross-(2*slip+2*commission)*quantity).quantize(D('.01'),rounding=ROUND_HALF_UP)
        if price_net!=D(pos['price_net_usd']) or price_net-claimed!=D(pos['net_usd']):raise ValueError('funded_trade_arithmetic')
        net_price_total+=price_net
    total_funding=sum(funding_by_id.values(),D(0))
    if total_funding!=D(result['funding_total_usd']) or D(10000)+net_price_total-total_funding!=D(result['balance_usd']):
        raise ValueError('funded_cash_reconcile')
    floating=D(0)
    if opened is not None:
        last=pairs[max(pairs)];side=opened['side'];q=D(opened['quantity'])
        entry=D(opened['ask'] if side=='BUY' else opened['bid'])
        price=D(str(last[0 if side=='BUY' else 1]['close']))
        gross=(price-entry if side=='BUY' else entry-price)*q
        floating=(gross-(2*slip+2*commission)*q).quantize(D('.01'),rounding=ROUND_HALF_UP)
    if floating!=D(result['floating_usd']) or D(result['balance_usd'])+floating-10000!=D(result['net_equity_usd']):
        raise ValueError('funded_mark_or_equity')
    if (result['closed_trades']!=len(result['trades']) or
            result['entries']!=len(result['trades'])+(opened is not None)):
        raise ValueError('funded_position_count')
    return dict(net_usd=result['net_equity_usd'],closed_trades=len(result['trades']),open_position=opened is not None,
        funding_usd=str(total_funding),unresolved_positions=[p.get('position_id',p.get('id')) for p in positions.values() if p['path_unresolved']])


def inspect_scenario(result, pairs, sessions):
    if result['open_position'] is not None or result.get('pending_action') is not None:
        raise ValueError('open_or_pending_book_requires_separate_mark_review')
    slip = D(result['slippage_per_side'])
    commission = commission_for_result(result)
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
        if distance <= 0 or (distance+D('.001')+2*slip+2*commission)*q > 25:
            raise ValueError('planned_risk_exceeded')
        exit_stamp = trade['exit_interval_msc'][0]
        if exit_stamp//86400000 != stamp//86400000:
            raise ValueError('carry_requires_funded_review')
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
        net = (gross-(2*slip+2*commission)*q).quantize(D('.01'), rounding=ROUND_HALF_UP)
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
        commission_for_result(result, manifest)
        inspector=inspect_funded_scenario if manifest.get('study_metadata',{}).get('cash_bid_daily_signal') else inspect_scenario
        reviews[row['scenario']] = inspector(result, pairs, sessions)
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
