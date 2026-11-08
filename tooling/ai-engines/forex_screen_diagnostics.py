"""Read sealed EURUSD coarse books and compare bounded coarse/native evidence.

This is accounting/approximation diagnosis, never a strategy selector or engine.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import time


def decimal(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('invalid monetary value') from error
    if not result.is_finite():
        raise ValueError('nonfinite monetary value')
    return result


def money(value):
    return value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cost_diagnostic(row, *, slippage, commission_per_side):
    """Independent USD/100k EURUSD arithmetic under explicit declared costs."""
    slip, commission = decimal(slippage), decimal(commission_per_side)
    if slip < 0 or commission < 0:
        raise ValueError('negative explicit cost')
    if (row['schema'] != 'forex-coarse-pnl-v1'
            or row['promotion_authorized'] is not False
            or row['automatic_rejection_authorized'] is not False
            or not row['candidate'].startswith('eurusd-')
            or row.get('input_basis', 'observed_bidask') != 'observed_bidask'):
        raise ValueError('unsupported coarse EURUSD scope')
    initial = decimal(row['starting_balance_usd'])
    if initial <= 0:
        raise ValueError('invalid starting balance')
    totals = dict(gross_after_embedded_spread_usd=Decimal(0), commission_usd=Decimal(0),
                  slippage_usd=Decimal(0), component_rounding_residual_usd=Decimal(0))
    closed_net = Decimal(0)
    positions = set()
    attributed_finance = Decimal(0)
    for trade in row['trades']:
        identity = trade['position_id']
        if identity in positions or not identity:
            raise ValueError('duplicate or empty position')
        positions.add(identity)
        quantity = decimal(trade['quantity'])
        entry, exit_price = decimal(trade['entry_fill']), decimal(trade['exit_fill'])
        if quantity <= 0 or min(entry, exit_price) <= 0 or trade['side'] not in ('BUY', 'SELL'):
            raise ValueError('invalid trade geometry')
        gross = (exit_price-entry)*quantity*100000*(1 if trade['side'] == 'BUY' else -1)
        fee, friction = 2*commission*quantity, 2*slip*quantity*100000
        net = money(gross-fee-friction)
        costs = trade['costs']
        if (costs['spread_basis'] != 'bid_ask_embedded' or costs['account_ccy'] != 'USD'
                or decimal(costs['quote_to_account_rate']) != 1 or costs['rounding_decimals'] != 2
                or costs['side'] != trade['side']
                or decimal(costs['entry_fill']) != entry or decimal(costs['exit_fill']) != exit_price
                or decimal(costs['gross_account']) != money(gross)
                or decimal(costs['commission_account']) != money(fee)
                or decimal(costs['slippage_account']) != money(friction)
                or decimal(costs['financing_account']) != 0 or decimal(costs['spread_cost_account']) != 0
                or decimal(costs['net_account']) != net or decimal(trade['price_net_usd']) != net
                or decimal(trade['net_usd']) != net-decimal(trade['timed_financing_usd'])):
            raise ValueError('trade arithmetic or declared cost mismatch')
        totals['gross_after_embedded_spread_usd'] += money(gross)
        totals['commission_usd'] += money(fee)
        totals['slippage_usd'] += money(friction)
        totals['component_rounding_residual_usd'] += net-(money(gross)-money(fee)-money(friction))
        closed_net += net
        attributed_finance += decimal(trade['timed_financing_usd'])
    opened = row['open_position']
    if opened is not None and opened['position_id'] in positions:
        raise ValueError('open position already closed')
    funding = decimal(row['financing_debit_usd'])
    event_ids = [event['event_id'] for event in row['financing_events']]
    if (len(set(event_ids)) != len(event_ids)
            or sum((decimal(event['debit_usd']) for event in row['financing_events']), Decimal(0)) != funding
            or attributed_finance+decimal(row['open_position_financing_usd']) != funding
            or (opened is None and decimal(row['open_position_financing_usd']) != 0)):
        raise ValueError('funding attribution mismatch')
    floating, balance, net_equity = map(decimal, (row['floating_usd'], row['balance_usd'], row['net_equity_usd']))
    if (type(row['closed_trades']) is not int or type(row['entry_fills']) is not int
            or row['closed_trades'] != len(positions)
            or row['entry_fills'] != len(positions)+int(opened is not None)
            or balance != initial+closed_net-funding
            or net_equity != balance+floating-initial
            or (opened is None and floating != 0)):
        raise ValueError('cash, floating or count mismatch')
    totals.update(timed_financing_debit_usd=funding, open_floating_net_usd=floating,
                  closed_price_net_usd=closed_net, net_equity_usd=net_equity)
    return {key: str(value) for key, value in totals.items()}


def compare_case(coarse, native, native_decisions, native_diagnostics, *, starting_balance):
    """Keep uncertainty visible; matching a total never certifies a screen."""
    initial = decimal(starting_balance)
    if initial <= 0 or coarse['candidate'] != native['candidate'] or coarse['scenario'] != native['scenario']:
        raise ValueError('comparison identity mismatch')
    first, second = decimal(coarse['net_equity_usd']), decimal(native['equity_usd'])-initial
    decisions_match = coarse['decisions'] == native_decisions
    counts_match = (coarse['entry_fills'] == native['entry_fills']
                    and coarse['closed_trades'] == native['closed_trades']
                    and bool(coarse['open_position']) == bool(native['open_position'])
                    and coarse['pending_entry'] == native['pending_entry'])
    native_trades = native_diagnostics['trades']
    if native['closed_trades'] != len(native_trades):
        raise ValueError('native trade diagnostic count mismatch')
    pairs = []
    for first_trade, second_trade in zip(coarse['trades'], native_trades):
        same_entry = all(first_trade[a] == second_trade[b] for a, b in (
            ('side', 'side'), ('quantity', 'quantity'), ('entry_time_msc', 'entry_time_msc'),
            ('entry_fill', 'entry_fill_price')))
        lower, upper = first_trade['exit_interval_msc']
        pairs.append(dict(same_entry=same_entry,
                          native_exit_in_coarse_interval=lower <= second_trade['exit_time_msc'] <= upper,
                          coarse_exit=first_trade['exit_fill'], native_exit=second_trade['exit_fill_price'],
                          coarse_reason=first_trade['reason'], native_reason=second_trade['exit_reason'],
                          net_delta_usd=str(decimal(first_trade['net_usd'])-decimal(second_trade['net_usd']))))
    entries_match = counts_match and all(p['same_entry'] for p in pairs)
    if coarse['open_position'] and native['open_position']:
        entries_match = entries_match and all(decimal(coarse['open_position'][key]) == decimal(native['open_position'][key])
            for key in ('quantity', 'entry_fill', 'stop_loss')) and coarse['open_position']['side'] == native['open_position']['side']
    native_floating = decimal(native['equity_usd'])-decimal(native['balance_usd'])
    floating_delta = decimal(coarse['floating_usd'])-native_floating
    open_finance_delta = decimal(coarse['open_position_financing_usd'])-decimal(native_diagnostics['open_position_financing_usd'])
    closed_delta = sum((decimal(t['net_usd']) for t in coarse['trades']), Decimal(0))-sum(
        (decimal(t['net_usd']) for t in native_trades), Decimal(0))
    if first-second != closed_delta-open_finance_delta+floating_delta:
        raise ValueError('comparison cash attribution mismatch')
    risk_affected = bool(native['risk_stops'] or native['risk_rejections'])
    sign = lambda value: (value > 0)-(value < 0)
    status = ('requires_transition_review' if not decisions_match or not entries_match or risk_affected
              else 'inconclusive_no_fills' if native['entry_fills'] == 0
              else 'requires_fill_review' if first != second else 'matched_within_bounded_scope')
    return dict(candidate=coarse['candidate'], scenario=coarse['scenario'], status=status,
                coarse_net_usd=str(first), native_net_usd=str(second),
                coarse_minus_native_usd=str(first-second), same_decisions=decisions_match,
                same_counts=counts_match, same_sign=sign(first) == sign(second),
                all_entries_match=entries_match, trade_pairs=pairs,
                closed_net_delta_usd=str(closed_delta), floating_net_delta_usd=str(floating_delta),
                open_financing_delta_usd=str(open_finance_delta),
                risk_affected=risk_affected, fills=native['entry_fills'],
                false_negative_rate=None, annual_error_bound_usd=None,
                promotion_authorized=False, automatic_rejection_authorized=False)


def catalogue_diagnostic(root):
    root = Path(root)
    config = json.loads((root/'config.json').read_bytes())
    summary = json.loads((root/'summary-review.json').read_bytes())
    config_hash = digest(root/'config.json')
    if (config['years'] != list(range(2010, 2023)) or len(config['candidates']) != 24
            or len(set(config['candidates'])) != 24 or set(config['costs']) != {'reference', 'cost-stress'}
            or summary['config_sha256'] != config_hash
            or summary['status'] != 'completed_observed_triage_only'):
        raise ValueError('unsupported catalogue scope or binding')
    rows, proofs = [], []
    for year in config['years']:
        path = root/str(year)/'result.json'
        seal = json.loads((path.parent/'completed.json').read_bytes())
        book = json.loads(path.read_bytes())
        if (seal['result_sha256'] != digest(path) or seal['config_sha256'] != config_hash
                or book['config_sha256'] != config_hash or book['source_files'] != config['source_files']
                or book['status'] != 'completed_observed_triage_only' or len(book['rows']) != 48
                or {(r['candidate'], r['scenario'], r['year']) for r in book['rows']}
                != {(c, s, year) for c in config['candidates'] for s in config['costs']}):
            raise ValueError('year seal, source or matrix mismatch')
        for row in book['rows']:
            costs = config['costs'][row['scenario']]
            decomposition = cost_diagnostic(row, slippage=costs['slippage'], commission_per_side='2.50')
            rows.append(dict(year=year, candidate=row['candidate'], scenario=row['scenario'],
                             **decomposition))
        proofs.append(dict(path=str(path), sha256=seal['result_sha256']))
    if (len(summary['summary']) != 24
            or {r['candidate'] for r in summary['summary']} != set(config['candidates'])):
        raise ValueError('summary candidate matrix mismatch')
    aggregate = []
    for item in summary['summary']:
        for scenario in config['costs']:
            selected = [r for r in rows if r['candidate'] == item['candidate'] and r['scenario'] == scenario]
            totals = {key: str(sum((decimal(r[key]) for r in selected), Decimal(0)))
                      for key in selected[0] if key.endswith('_usd')}
            if decimal(totals['net_equity_usd']) != decimal(item['scenarios'][scenario]['sum_annual_books_usd']):
                raise ValueError('summary total mismatch')
            aggregate.append(dict(candidate=item['candidate'], scenario=scenario, **totals))
    return dict(schema='forex-screen-cost-diagnosis-v1', rows=rows, aggregate=aggregate,
                input_proofs=proofs, config_sha256=config_hash, summary_sha256=digest(root/'summary-review.json'),
                gross_is_frictionless_alpha=False, open_floating_decomposition='not_available_in_coarse_row',
                cross_scenario_delta_is_cost_only=False, automatic_rejection_authorized=False,
                promotion_authorized=False, broker_calls=0, model_calls=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError('output already exists')
    began = time.perf_counter()
    report = catalogue_diagnostic(args.catalogue)
    report.update(wall_seconds=time.perf_counter()-began,
                  checked_at_utc=datetime.now(timezone.utc).isoformat(), tool_sha256=digest(__file__))
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(dict(rows=len(report['rows']), groups=len(report['aggregate']),
                          wall_seconds=report['wall_seconds'], promotion_authorized=False)))


if __name__ == '__main__':
    main()
