from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forex_screen_diagnostics import cost_diagnostic, compare_case, catalogue_diagnostic


def fixture(side='BUY', *, opened=False, credit=False):
    # 0.1 lot, 10 pip favorable move: $10 gross, $.50 commission, $.40 slip.
    entry, exit_price = ('1.10000', '1.10100') if side == 'BUY' else ('1.10000', '1.09900')
    finance = '-.20' if credit else '.20'
    trade = dict(position_id='closed-1', side=side, quantity='.1', entry_fill=entry,
        exit_fill=exit_price, entry_time_msc=1, exit_interval_msc=[2, 3], reason='stop_loss',
        price_net_usd='9.10', timed_financing_usd=finance,
        net_usd='9.30' if credit else '8.90', costs=dict(spread_basis='bid_ask_embedded',
        account_ccy='USD', quote_to_account_rate=1, rounding_decimals=2, side=side,
        entry_fill=entry, exit_fill=exit_price, gross_account='10', commission_account='.50',
        slippage_account='.40', financing_account=0, spread_cost_account=0, net_account='9.10'))
    return dict(schema='forex-coarse-pnl-v1', promotion_authorized=False,
        automatic_rejection_authorized=False, candidate='eurusd-h1-fixture', scenario='fixture',
        starting_balance_usd='10000', trades=[trade], closed_trades=1,
        entry_fills=2 if opened else 1, open_position=dict(position_id='open-2') if opened else None,
        financing_debit_usd=finance, open_position_financing_usd=0,
        financing_events=[dict(event_id='fee-1', debit_usd=finance)],
        floating_usd='-1' if opened else '0', balance_usd='10009.30' if credit else '10008.90',
        net_equity_usd=('8.30' if credit else '7.90') if opened else ('9.30' if credit else '8.90'),
        decisions=[] , pending_entry=False)


class ScreenDiagnosisTests(unittest.TestCase):
    def test_independent_buy_sell_cash_credit_and_open_floating(self):
        for side in ('BUY', 'SELL'):
            for opened in (False, True):
                for credit in (False, True):
                    row = fixture(side, opened=opened, credit=credit)
                    result = cost_diagnostic(row, slippage='.00002', commission_per_side='2.50')
                    self.assertEqual(result['gross_after_embedded_spread_usd'], '10.00')
                    self.assertEqual(result['net_equity_usd'], row['net_equity_usd'])

    def test_tampered_cash_cost_fill_count_and_nonfinite_rejected(self):
        for change in ('cash', 'cost', 'fill', 'count', 'duplicate', 'funding', 'nan', 'initial', 'scope'):
            row = fixture()
            if change == 'cash': row['balance_usd'] = '10008.91'
            if change == 'cost': row['trades'][0]['costs']['commission_account'] = '.49'
            if change == 'fill': row['trades'][0]['exit_fill'] = '1.10101'
            if change == 'count': row['entry_fills'] = 2
            if change == 'duplicate': row['trades'] *= 2
            if change == 'funding': row['financing_events'][0]['debit_usd'] = '.21'
            if change == 'nan': row['floating_usd'] = 'NaN'
            if change == 'initial': row['starting_balance_usd'] = 0
            if change == 'scope': row['promotion_authorized'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                cost_diagnostic(row, slippage='.00002', commission_per_side='2.50')

    def test_round_components_are_not_silently_forced_to_equal_unrounded_net(self):
        row = fixture(credit=True)
        # 0.015 lots yields .075 commission and .06 slip; gross .15 -> net .015 -> .02.
        trade = row['trades'][0]
        trade.update(quantity='.015', exit_fill='1.10010', price_net_usd='.02', net_usd='.22')
        trade['costs'].update(exit_fill='1.10010', gross_account='.15', commission_account='.08',
                              slippage_account='.06', net_account='.02')
        row.update(balance_usd='10000.22', net_equity_usd='.22')
        result = cost_diagnostic(row, slippage='.00002', commission_per_side='2.50')
        self.assertEqual(result['component_rounding_residual_usd'], '0.01')

    def test_negative_movement_is_preserved(self):
        row = fixture()
        trade = row['trades'][0]
        trade.update(exit_fill='1.09900', price_net_usd='-10.90', net_usd='-11.10')
        trade['costs'].update(exit_fill='1.09900', gross_account='-10', net_account='-10.90')
        row.update(balance_usd='9988.90', net_equity_usd='-11.10')
        self.assertEqual(cost_diagnostic(row, slippage='.00002', commission_per_side='2.50')['closed_price_net_usd'], '-10.90')

    def test_identical_total_cannot_hide_different_signals_or_entry(self):
        row = fixture()
        native = dict(candidate=row['candidate'], scenario=row['scenario'], equity_usd='10008.90',
            balance_usd='10008.90', entry_fills=1, closed_trades=1, open_position=None,
            pending_entry=False, risk_stops=[], risk_rejections=[])
        diagnostic = dict(open_position_financing_usd=0, trades=[dict(side='BUY', quantity='.1',
            entry_time_msc=1, entry_fill_price='1.10000', exit_time_msc=2,
            exit_fill_price='1.10100', exit_reason='stop_loss', net_usd='8.90')])
        result = compare_case(row, native, [], diagnostic, starting_balance='10000')
        self.assertEqual(result['status'], 'matched_within_bounded_scope')
        self.assertIsNone(result['false_negative_rate'])
        for changed in ('signals', 'entry', 'risk'):
            altered = deepcopy(diagnostic)
            other = deepcopy(native)
            signals = []
            if changed == 'signals': signals = [dict(signal='SELL')]
            if changed == 'entry': altered['trades'][0]['entry_fill_price'] = '1.10001'
            if changed == 'risk': other['risk_stops'] = ['stop']
            result = compare_case(row, other, signals, altered, starting_balance='10000')
            self.assertEqual(result['status'], 'requires_transition_review')

    def test_no_fills_is_inconclusive_not_filter_certification(self):
        row = fixture()
        row.update(trades=[], entry_fills=0, closed_trades=0, net_equity_usd=0)
        native = dict(candidate=row['candidate'], scenario=row['scenario'], equity_usd='10000',
            balance_usd='10000', entry_fills=0, closed_trades=0, open_position=None,
            pending_entry=False, risk_stops=[], risk_rejections=[])
        result = compare_case(row, native, [], dict(trades=[], open_position_financing_usd=0), starting_balance=10000)
        self.assertEqual(result['status'], 'inconclusive_no_fills')
        self.assertFalse(result['automatic_rejection_authorized'])

    def test_sealed_catalogue_checks_matrix_sources_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write = lambda p, value: p.write_text(json.dumps(value), encoding='utf-8')
            sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            candidates = [f'eurusd-fixture-{i}' for i in range(24)]
            config = dict(years=list(range(2010, 2023)), candidates=candidates,
                costs={s: dict(slippage='.00002') for s in ('reference', 'cost-stress')}, source_files={'fixture': 'a'*64})
            write(root/'config.json', config)
            config_sha = sha(root/'config.json')
            summary = dict(config_sha256=config_sha, status='completed_observed_triage_only', summary=[dict(
                candidate=c, scenarios={s: dict(sum_annual_books_usd='115.70') for s in config['costs']}) for c in candidates])
            write(root/'summary-review.json', summary)
            for year in config['years']:
                folder = root/str(year);folder.mkdir()
                rows = []
                for candidate in candidates:
                    for scenario in config['costs']:
                        rows.append(fixture() | dict(candidate=candidate, scenario=scenario, year=year))
                write(folder/'result.json', dict(config_sha256=config_sha, source_files=config['source_files'],
                    status='completed_observed_triage_only', rows=rows))
                write(folder/'completed.json', dict(config_sha256=config_sha, result_sha256=sha(folder/'result.json')))
            report = catalogue_diagnostic(root)
            self.assertEqual(len(report['rows']), 624)
            self.assertEqual(len(report['aggregate']), 48)
            path = root/'2010/result.json';original = json.loads(path.read_bytes())
            seal = root/'2010/completed.json'
            for change in ('hash', 'source', 'matrix'):
                bad = deepcopy(original)
                if change == 'source':bad['source_files'] = {'other': 'a'*64}
                if change == 'matrix':bad['rows'][-1] = deepcopy(bad['rows'][0])
                write(path, bad)
                write(seal, dict(config_sha256=config_sha, result_sha256='0'*64 if change == 'hash' else sha(path)))
                with self.subTest(change=change), self.assertRaises(ValueError):catalogue_diagnostic(root)
            write(path, original)
            write(seal, dict(config_sha256=config_sha, result_sha256=sha(path)))
            summary['summary'][0]['scenarios']['reference']['sum_annual_books_usd'] = '115.71'
            write(root/'summary-review.json', summary)
            with self.assertRaises(ValueError):catalogue_diagnostic(root)


if __name__ == '__main__':
    unittest.main()
