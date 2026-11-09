"""Hierarchical accounting on sealed closed trades; no strategy selection.

Inputs are already valued in USD on one declared mid-price benchmark. Scenario
paths remain separate and annual books reset capital. Open equity is bridged at
book/scenario level only. Consumers must bind input files and valuation evidence.
"""
from collections import defaultdict
from decimal import Decimal
import json

from forex_screen_diagnostics import adverse_budget, decimal, money


ZERO = Decimal(0)
DEBITS = ('mid_price_losses', 'embedded_spread', 'commission', 'slippage',
          'funding_debits', 'rounding_debits')
CREDITS = ('mid_price_wins', 'funding_credits', 'rounding_credits')
COSTS = ('embedded_spread', 'commission', 'slippage', 'funding_debits')
LEVELS = ('strategy', 'scenario', 'annual_book', 'side', 'exit_reason',
          'holding_bucket', 'trade')


def percentage(numerator, denominator, *, unit, scope):
    """Keep the actual denominator beside every displayed percentage."""
    num = decimal(numerator)
    den = None if denominator is None else decimal(denominator)
    if den is not None and den < 0:
        raise ValueError('negative_percentage_denominator')
    return dict(percent=None if not den else str(money(num / den * 100)),
                numerator=str(num), denominator=None if den is None else str(den),
                unit=unit, denominator_scope=scope)


def _capital(value):
    try:
        amount = decimal(value)
        return amount if amount > 0 else None
    except (ValueError, TypeError):
        return None


def _label(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('explicit_classification_required')
    return value


def _key(row):
    if type(row['year']) is not int:
        raise ValueError('integer_book_year_required')
    return _label(row['scenario']), row['year']


def _trade(row):
    scenario, year = _key(row)
    identity = (scenario, year, _label(row['position_id']))
    if row['side'] not in ('BUY', 'SELL'):
        raise ValueError('invalid_side')
    _label(row['reason'])
    _label(row['holding_bucket'])
    mid, bidask, spread, fee, slip, funding, residual, net = (
        decimal(row[k]) for k in ('mid_benchmark_gross', 'bidask_gross',
            'embedded_spread', 'commission', 'slippage', 'funding',
            'rounding_residual', 'net'))
    if min(spread, fee, slip) < 0:
        raise ValueError('negative_explicit_cost')
    if mid - spread != bidask or bidask - fee - slip - funding + residual != net:
        raise ValueError('trade_components_do_not_reconcile')
    debit = dict(zip(DEBITS, (max(-mid, ZERO), spread, fee, slip,
                             max(funding, ZERO), max(-residual, ZERO))))
    credit = dict(zip(CREDITS, (max(mid, ZERO), max(-funding, ZERO),
                               max(residual, ZERO))))
    return dict(identity=list(identity), source=row, debit=debit, credit=credit, net=net)


def _totals(trades):
    debits = {k: sum((t['debit'][k] for t in trades), ZERO) for k in DEBITS}
    credits = {k: sum((t['credit'][k] for t in trades), ZERO) for k in CREDITS}
    net = sum((t['net'] for t in trades), ZERO)
    ledger = adverse_budget(debits, credits, net=net)
    return dict(trades=len(trades), wins=sum(t['net'] > 0 for t in trades),
                losses=sum(t['net'] < 0 for t in trades),
                breakeven=sum(t['net'] == 0 for t in trades),
                net_usd=str(net),
                winning_net_pool_usd=str(sum((max(t['net'], ZERO) for t in trades), ZERO)),
                losing_net_pool_usd=str(sum((max(-t['net'], ZERO) for t in trades), ZERO)),
                cost_debit_pool_usd=str(sum((debits[k] for k in COSTS), ZERO)),
                ledger=ledger)


def _shares(totals, denominator, scope):
    pairs = {k: (totals[k], denominator[k], 'trades' if k == 'trades' else 'USD')
             for k in ('trades', 'winning_net_pool_usd', 'losing_net_pool_usd',
                       'cost_debit_pool_usd')}
    pairs.update({k: (totals['ledger'][k], denominator['ledger'][k], 'USD')
                  for k in ('total_adverse_usd', 'total_favorable_usd')})
    for side in ('debits', 'credits'):
        pairs.update({k: (v, denominator['ledger'][side][k], 'USD')
                      for k, v in totals['ledger'][side].items()})
    return {k: percentage(n, d, unit=u, scope=scope) for k, (n, d, u) in pairs.items()}


def _local_percentages(totals, scope):
    ledger = totals['ledger']
    return dict(
        win_rate=percentage(totals['wins'], totals['trades'], unit='trades', scope=scope),
        loss_rate=percentage(totals['losses'], totals['trades'], unit='trades', scope=scope),
        breakeven_rate=percentage(totals['breakeven'], totals['trades'], unit='trades', scope=scope),
        adverse_components={k: percentage(v, ledger['total_adverse_usd'], unit='USD', scope=scope)
                            for k, v in ledger['debits'].items()},
        favorable_components={k: percentage(v, ledger['total_favorable_usd'], unit='USD', scope=scope)
                              for k, v in ledger['credits'].items()},
        cost_components={k: percentage(ledger['debits'][k], totals['cost_debit_pool_usd'],
                                     unit='USD', scope=scope) for k in COSTS})


def build_hierarchy(candidate, trades, books):
    """Return one disjoint tree, percentages, capital contributions and bridges.

    Book inputs must identify their own starting_balance_usd (invalid -> N/A),
    source locator/hash, closed_net, open_financing, terminal_floating, net_equity
    and closed trade count. No fallback to another book's capital is permitted.
    """
    _label(candidate)
    prepared = [_trade(t) for t in trades]
    identities = [tuple(t['identity']) for t in prepared]
    if len(set(identities)) != len(identities):
        raise ValueError('duplicate_composite_trade_identity')
    book_map = {}
    by_book = defaultdict(list)
    for t in prepared:
        by_book[tuple(t['identity'][:2])].append(t)
    for book in books:
        key = _key(book)
        if key in book_map:
            raise ValueError('duplicate_book_identity')
        _label(book['source_locator'])
        sha = book['source_sha256']
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('source_sha256_required')
        members = by_book[key]
        net = sum((t['net'] for t in members), ZERO)
        if (type(book['trades']) is not int or book['trades'] != len(members)
                or net != decimal(book['closed_net'])
                or decimal(book['open_financing']) < 0
                or net - decimal(book['open_financing']) + decimal(book['terminal_floating'])
                != decimal(book['net_equity'])):
            raise ValueError('book_equity_bridge_does_not_reconcile')
        book_map[key] = book
    if not book_map or set(by_book) - set(book_map):
        raise ValueError('explicit_book_for_every_trade_required')

    nodes = []

    def add(path, members, parent=None, scenario=None, book=None):
        node_id = json.dumps(path, ensure_ascii=False, separators=(',', ':'))
        level = LEVELS[len(path) - 1]
        node = dict(id=node_id, path=path, parent_id=None if parent is None else parent['id'],
                    level=level, label=path[-1], children=[])
        nodes.append(node)
        if parent is not None:
            parent['children'].append(node_id)
        if level == 'strategy':
            node.update(closed_trade_cost_cases=len(members), totals=None,
                        financial_aggregate_status='not_applicable_alternative_scenarios')
            for value in sorted({key[0] for key in book_map}):
                add(path + [value], [t for t in members if t['identity'][0] == value], node)
            return node
        totals = _totals(members)
        scenario = node if level == 'scenario' else scenario
        node['totals'] = totals
        node['percentages'] = dict(
            local=_local_percentages(totals, node_id),
            parent={} if level == 'scenario' else _shares(totals, parent['totals'], parent['id']),
            scenario=_shares(totals, scenario['totals'], scenario['id']))
        if book is not None:
            book_id = json.dumps(path[:3], ensure_ascii=False, separators=(',', ':'))
            node['closed_return_contribution_pct'] = percentage(
                totals['net_usd'], _capital(book.get('starting_balance_usd')),
                unit='USD', scope=book_id + ':starting_balance_usd')
            node['source_book'] = dict(locator=book['source_locator'], sha256=book['source_sha256'])
        if level in ('scenario', 'annual_book'):
            selected = [b for (s, _), b in book_map.items() if s == path[1]] if book is None else [book]
            bridge = {key: str(sum((decimal(b[key]) for b in selected), ZERO))
                      for key in ('closed_net', 'open_financing', 'terminal_floating', 'net_equity')}
            valid = all(_capital(b.get('starting_balance_usd')) is not None for b in selected)
            mean = (sum((decimal(b['net_equity']) / _capital(b.get('starting_balance_usd'))
                         for b in selected), ZERO) / len(selected)) if valid else None
            node['equity_bridge'] = dict(**bridge, annual_reset_books=len(selected),
                mean_annual_book_return_pct=None if mean is None else str(money(mean * 100)),
                return_basis='arithmetic_mean_of_each_book_net_equity_over_own_capital',
                missing_capital_books=sum(_capital(b.get('starting_balance_usd')) is None for b in selected),
                open_items_allocated_to_closed_groups=False)
            if level == 'annual_book':
                node['equity_return_pct'] = percentage(bridge['net_equity'],
                    _capital(book.get('starting_balance_usd')), unit='USD', scope=node_id + ':starting_balance_usd')
        if level == 'trade':
            node['trade_identity'] = members[0]['identity']
            return node
        if level == 'scenario':
            for key in sorted(k for k in book_map if k[0] == path[1]):
                add(path + [key[1]], by_book[key], node, scenario, book_map[key])
        else:
            field = {'annual_book': 'side', 'side': 'reason', 'exit_reason': 'holding_bucket',
                     'holding_bucket': 'position_id'}[level]
            groups = defaultdict(list)
            for t in members:
                groups[t['source'][field]].append(t)
            for value in sorted(groups):
                add(path + [value], groups[value], node, scenario, book)
        return node

    root = add([candidate], prepared)
    return dict(schema='hierarchical-pnl-attribution-v1', candidate=candidate,
                annual_resets=True, hierarchy=list(LEVELS), root_id=root['id'], nodes=nodes,
                percentage_policy='explicit_numerator_denominator_scope; zero_or_unknown_denominator_null; ROUND_HALF_UP_2dp',
                classification_basis='existing_side_exit_reason_earliest_modeled_holding_not_new_filters',
                metric_definitions=dict(
                    currency='USD; exact Decimal amounts, round displayed percentages only',
                    net_outcomes='closed net after all declared costs; >0 win, <0 loss, =0 breakeven',
                    adverse_pool='mid-price losses + nonnegative cost debits + rounding debits',
                    favorable_pool='mid-price gains + funding credits + rounding credits',
                    cost_debit_pool='spread + commission + slippage + funding debits; credits separate',
                    winning_net_pool='sum positive closed trade net; disjoint from losing net pool',
                    losing_net_pool='sum absolute negative closed trade net; do not add to adverse pool',
                    parent_shares='same component divided by same component in immediate parent',
                    scenario_shares='same component divided by same component in alternative scenario',
                    capital_contribution='closed net / source annual book capital; not group standalone ROI',
                    annual_return='equity PnL / own capital, arithmetic mean across annual reset books; not CAGR',
                    null_policy='zero share denominator or missing/invalid capital -> null; any invalid capital -> null mean',
                    rounding='ROUND_HALF_UP to 0.01 percentage point; displayed children may sum to 99.99 or 100.01'),
                causal_attribution_proven=False, promotion_authorized=False)


def render_markdown(result):
    """Render all nodes so a human can follow the same hierarchy as an agent."""
    lines = ['# Phân rã lời/lỗ theo tầng', '',
        'Mỗi dòng có đường dẫn đầy đủ. Chỉ cộng các con cùng cha; hai kịch bản phí không cộng chung.',
        'Sổ năm reset vốn. % vốn nhóm là đóng góp lợi suất của sổ, không phải ROI riêng của nhóm.',
        'Open financing/floating chỉ nằm ở cầu nối equity của sổ/kịch bản. N/A nghĩa là mẫu số 0 hoặc thiếu.', '',
        '| Tầng / đường dẫn | Lệnh | Net đóng, USD | Win rate | % bất lợi của cha | % cost của cha | % lãi của cha | % lỗ của cha | Net đóng / vốn sổ |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']

    def pct(record):
        return 'N/A' if not record or record['percent'] is None else record['percent'] + '%'

    for node in result['nodes']:
        if node['level'] == 'strategy':
            continue
        totals, percentages = node['totals'], node['percentages']
        shares = percentages['parent']
        path = ' → '.join(str(v).replace('|', '\\|').replace('\n', ' ') for v in node['path'][1:])
        lines.append(f"| {node['level']}: {path} | {totals['trades']} | {totals['net_usd']} | "
            + ' | '.join((pct(percentages['local']['win_rate']), pct(shares.get('total_adverse_usd')),
                pct(shares.get('cost_debit_pool_usd')), pct(shares.get('winning_net_pool_usd')),
                pct(shares.get('losing_net_pool_usd')), pct(node.get('closed_return_contribution_pct')))) + ' |')
    lines += ['', '## Thành phần và cầu nối equity', '',
        'JSON kèm theo giữ mọi thành phần debit/credit, % local, % cùng khoản so với cha và kịch bản,',
        'tử số/mẫu số, nguồn/hash sổ và trade identity. Win rate dùng net sau phí; không phải tỷ lệ lợi nhuận.',
        'Tỷ trọng accounting không là % nguyên nhân có thể loại bỏ hoặc bằng chứng edge.', '']
    for node in result['nodes']:
        if 'equity_bridge' in node:
            b = node['equity_bridge']
            lines.append(f"- {node['path'][1:]}: closed {b['closed_net']} − open financing {b['open_financing']} "
                f"+ floating {b['terminal_floating']} = equity PnL {b['net_equity']} USD; "
                f"mean annual return {b['mean_annual_book_return_pct'] if b['mean_annual_book_return_pct'] is not None else 'N/A'}%.")
    return '\n'.join(lines) + '\n'
