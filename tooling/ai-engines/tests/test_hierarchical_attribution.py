from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hierarchical_attribution import build_hierarchy, render_markdown


def trade(position='p1', *, year=2020, scenario='reference', mid='100',
          spread='10', funding='5', net='82', side='BUY', reason='strategy_exit'):
    return dict(year=year, scenario=scenario, position_id=position, side=side,
                reason=reason, holding_bucket='over_5_days', mid_benchmark_gross=mid,
                bidask_gross=str(Decimal(mid)-Decimal(spread)), embedded_spread=spread,
                commission='1', slippage='2', funding=funding, net=net, rounding_residual='0')


def book(trades, capital='10000', *, open_financing='3', floating='7'):
    net = sum((Decimal(t['net']) for t in trades), Decimal(0))
    return dict(year=trades[0]['year'], scenario=trades[0]['scenario'], trades=len(trades),
                closed_net=str(net), open_financing=open_financing, terminal_floating=floating,
                net_equity=str(net-Decimal(open_financing)+Decimal(floating)),
                starting_balance_usd=capital, source_locator='sealed-book.json', source_sha256='a'*64)


def make(trades, books=None):
    return build_hierarchy('candidate-v1', trades, [book(trades)] if books is None else books)


class HierarchicalAttributionTests(unittest.TestCase):
    def test_disjoint_partition_reconciles_every_level_and_keeps_open_bridge_separate(self):
        rows = [trade(), trade('p2', mid='-50', net='-68', side='SELL', reason='stop_loss')]
        out = make(rows)
        nodes = {n['id']: n for n in out['nodes']}
        for n in nodes.values():
            if not n['children'] or n['level'] == 'strategy':
                continue
            children = [nodes[k] for k in n['children']]
            for key in ('trades', 'wins', 'losses', 'breakeven', 'net_usd',
                        'winning_net_pool_usd', 'losing_net_pool_usd', 'cost_debit_pool_usd'):
                self.assertEqual(sum(Decimal(str(c['totals'][key])) for c in children),
                                 Decimal(str(n['totals'][key])))
            for side in ('debits', 'credits'):
                for key, value in n['totals']['ledger'][side].items():
                    self.assertEqual(sum(Decimal(c['totals']['ledger'][side][key]) for c in children), Decimal(value))
        scenario = out['nodes'][1]
        self.assertEqual(scenario['totals']['net_usd'], '14')
        self.assertEqual(scenario['percentages']['local']['win_rate']['percent'], '50.00')
        self.assertEqual(scenario['equity_bridge']['net_equity'], '18')
        self.assertTrue(all('equity_bridge' not in n for n in nodes.values()
                            if n['level'] in ('side', 'exit_reason', 'holding_bucket', 'trade')))
        self.assertIn('annual_book', render_markdown(out))

    def test_scenarios_are_alternatives_and_identity_is_composite(self):
        rows = [trade(), trade(year=2021), trade(scenario='stress')]
        out = make(rows, [book([r]) for r in rows])
        root = out['nodes'][0]
        self.assertIsNone(root['totals'])
        self.assertEqual(root['closed_trade_cost_cases'], 3)
        leaves = [n for n in out['nodes'] if n['level'] == 'trade']
        self.assertEqual(len({n['id'] for n in leaves}), 3)
        self.assertEqual(len({tuple(n['trade_identity']) for n in leaves}), 3)
        self.assertEqual(len(root['children']), 2)
        with self.assertRaisesRegex(ValueError, 'duplicate_composite'):
            make([rows[0], rows[0]])

    def test_local_and_parent_and_scenario_denominators_differ(self):
        rows = [trade(), trade('p2', mid='-50', net='-68', side='SELL')]
        out = make(rows)
        buy = next(n for n in out['nodes'] if n['level'] == 'side' and n['label'] == 'BUY')
        pct = buy['percentages']
        self.assertEqual(pct['local']['adverse_components']['funding_debits']['percent'], '27.78')
        self.assertEqual(pct['parent']['funding_debits']['percent'], '50.00')
        self.assertEqual(pct['scenario']['total_adverse_usd']['denominator'], '86')
        self.assertEqual(pct['parent']['losing_net_pool_usd']['percent'], '0.00')
        self.assertEqual(pct['parent']['winning_net_pool_usd']['percent'], '100.00')

    def test_mixed_capital_uses_each_book_and_mean_is_not_compounded_return(self):
        rows = [trade(), trade(year=2021)]
        out = make(rows, [book([rows[0]], capital='10000'), book([rows[1]], capital='100')])
        scenario = out['nodes'][1]
        self.assertEqual(scenario['equity_bridge']['mean_annual_book_return_pct'], '43.43')
        contributions = [n['closed_return_contribution_pct']['percent'] for n in out['nodes'] if n['level'] == 'trade']
        self.assertEqual(contributions, ['0.82', '82.00'])
        self.assertNotIn('equity_return_pct', scenario)

    def test_unknown_capital_propagates_without_dropping_a_book(self):
        rows = [trade(), trade(year=2021)]
        for invalid in (None, '0', '-100', 'NaN', 'wrong'):
            with self.subTest(capital=invalid):
                out = make(rows, [book([rows[0]]), book([rows[1]], capital=invalid)])
                self.assertIsNone(out['nodes'][1]['equity_bridge']['mean_annual_book_return_pct'])
                self.assertEqual(out['nodes'][1]['equity_bridge']['missing_capital_books'], 1)
                leaf = next(n for n in out['nodes'] if n['level'] == 'trade' and n['path'][2] == 2021)
                self.assertIsNone(leaf['closed_return_contribution_pct']['percent'])
                self.assertEqual(out['nodes'][1]['totals']['trades'], 2)

    def test_zero_adverse_cost_and_no_trade_books_are_explicit(self):
        row = trade(mid='0', spread='0', funding='0', net='0')
        row.update(commission='0', slippage='0')
        empty = book([row])
        empty.update(year=2021, trades=0, closed_net='0', open_financing='0', terminal_floating='0', net_equity='0')
        out = make([row], [book([row]), empty])
        p = out['nodes'][1]['percentages']['local']
        self.assertIsNone(p['adverse_components']['embedded_spread']['percent'])
        self.assertIsNone(p['favorable_components']['mid_price_wins']['percent'])
        self.assertEqual(out['nodes'][1]['totals']['breakeven'], 1)
        empty_node = next(n for n in out['nodes'] if n['level'] == 'annual_book' and n['label'] == 2021)
        self.assertEqual(empty_node['children'], [])
        self.assertIsNone(empty_node['percentages']['local']['win_rate']['percent'])

    def test_financing_credit_and_signed_rounding_reconcile(self):
        row = trade(funding='-5', net='92.01')
        row['rounding_residual'] = '0.01'
        got = make([row])['nodes'][1]['totals']
        self.assertEqual(got['ledger']['credits']['funding_credits'], '5')
        self.assertEqual(got['ledger']['credits']['rounding_credits'], '0.01')
        self.assertEqual(got['cost_debit_pool_usd'], '13')

    def test_invalid_accounting_classification_and_identity_fail_closed(self):
        rows = [trade()]
        changes = [('mid_benchmark_gross', '101'), ('net', '81'), ('embedded_spread', '-1'),
                   ('commission', 'NaN'), ('side', 'other'), ('reason', ''), ('holding_bucket', ''),
                   ('position_id', ''), ('year', True)]
        for key, value in changes:
            with self.subTest(field=key):
                bad = deepcopy(rows)
                bad[0][key] = value
                with self.assertRaises(ValueError):
                    make(bad, [book(rows)])
        for key, value in [('net_equity', '99'), ('source_sha256', ''), ('trades', 3), ('open_financing', '-1')]:
            badbook = book(rows)
            badbook[key] = value
            with self.assertRaises(ValueError):
                make(rows, [badbook])
        with self.assertRaises(ValueError):
            make(rows, [])
        with self.assertRaises(ValueError):
            make(rows, [book(rows), book(rows)])


if __name__ == '__main__':
    unittest.main()
