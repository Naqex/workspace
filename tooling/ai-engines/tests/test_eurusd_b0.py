import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from decimal import Decimal as D

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eurusd_b0 as b0
import eurusd_b0_source as source

ROOT = Path(__file__).resolve().parents[3]
b0.bind_native(ROOT/'projects/trader/foundation_v2')


def fixture(day='2022-06-01'):
    s = source.session(day)
    features = {}
    for at in range(s[7]+15*source.MINUTE, s[8]+1, 15*source.MINUTE):
        features[at] = dict(bar=[at-15*source.MINUTE, 99980, 100000, 99950, 99990, 15],
                            atr_before=D(20), bias='BUY')
    features[s[8]+15*source.MINUTE] = dict(
        bar=[s[8], 100000, 100050, 99995, 100040, 15], atr_before=D(20), bias='BUY')
    features[s[8]+30*source.MINUTE] = dict(
        bar=[s[8]+15*source.MINUTE, 100003, 100040, 99850, 100020, 15], atr_before=D(20), bias='BUY')
    entry = s[8]+30*source.MINUTE
    quotes = [(entry-1, 1, 100019, 100021), (entry, 2, 100020, 100022),
              (entry+1000, 3, 100371, 100373)]
    return s, features, quotes


class B0Tests(unittest.TestCase):
    def test_entry_after_retest_close_and_native_accounting(self):
        s, f, quotes = fixture()
        account = b0.Account()
        d = b0.run_day('2022-06-01', f, quotes, account, 'stress')
        t = d['trades'][0]
        self.assertEqual(t['entry_msc'], s[8]+30*source.MINUTE)
        self.assertEqual(t['entry_sequence'], 2)
        self.assertEqual(t['natural_stop_units'], 99848)
        self.assertEqual(t['take_units']-t['entry_units'], 2*(t['entry_units']-t['natural_stop_units']))
        self.assertEqual(t['exit_units'], t['take_units'])
        self.assertTrue(t['native_accounting_reconciled'])
        self.assertFalse(t['news_checked'])
        self.assertEqual(d['counters']['filled_entries'], 1)
        self.assertLessEqual(t['planned_stress_friction_r0'], .12)

    def test_friction_reject_does_not_widen_stop(self):
        _, f, quotes = fixture()
        for row in f.values():
            if row['bar'][3] == 99850:
                row['bar'][3] = 99999
        d = b0.run_day('2022-06-01', f, quotes, b0.Account(), 'stress')
        self.assertEqual(d['counters']['pre_cost_confirmed_signals'], 1)
        self.assertEqual(d['counters']['friction_cap_rejected'], 1)
        self.assertEqual(d['intents'][0]['natural_stop_units'], 99997)
        self.assertEqual(d['trades'], [])

    def test_first_touch_failure_consumes_setup(self):
        s, f, quotes = fixture()
        f[s[8]+30*source.MINUTE]['bar'][4] = 100001
        d = b0.run_day('2022-06-01', f, quotes, b0.Account(), 'stress')
        self.assertEqual(d['counters']['first_touch_not_confirmed'], 1)
        self.assertNotIn('pre_cost_confirmed_signals', d['counters'])

    def test_bias_change_abstains(self):
        s, f, quotes = fixture()
        f[s[8]+30*source.MINUTE]['bias'] = 'SELL'
        d = b0.run_day('2022-06-01', f, quotes, b0.Account(), 'stress')
        self.assertEqual(d['counters']['setup_bias_cancelled'], 1)
        self.assertEqual(d['trades'], [])

    def test_no_quote_substitution_and_missing_zone(self):
        s, f, quotes = fixture()
        d = b0.run_day('2022-06-01', f, [], b0.Account(), 'stress')
        self.assertEqual(d['intents'][0]['status'], 'entry_quote_unavailable')
        del f[s[8]]
        d = b0.run_day('2022-06-01', f, quotes, b0.Account(), 'stress')
        self.assertEqual(d['counters']['invalid_zone_missing_m15'], 1)

    def test_sell_symmetry_and_outward_grid(self):
        self.assertEqual(b0.natural_stop('BUY', 100, 110, D('2.2')), 97)
        self.assertEqual(b0.natural_stop('SELL', 100, 110, D('2.2')), 113)
        a = b0.admission('SELL', 100200, 100000, 100002, b0.INITIAL_CENTS)
        self.assertEqual(a['status'], 'accepted')
        self.assertEqual(a['take_units'], 99600)
        self.assertEqual(b0.protection(dict(side='SELL', natural_stop_units=100200, take_units=99600), 100205, 100207), (100207, 'stop_loss'))

    def test_tick_order_resolves_same_minute_sl_tp(self):
        _, f, quotes = fixture()
        entry = quotes[1][0]
        stop_first = quotes[:2]+[(entry+1, 3, 99840, 99842), (entry+2, 4, 100380, 100382)]
        d = b0.run_day('2022-06-01', f, stop_first, b0.Account(), 'stress')
        self.assertEqual(d['trades'][0]['exit_reason'], 'stop_loss')
        self.assertEqual(d['trades'][0]['exit_units'], 99840)
        self.assertLess(d['trades'][0]['net_r0'], -1)

    def test_two_entry_limit_and_no_same_event_setup_reuse(self):
        s, f, quotes = fixture()
        for minute in (45, 75):
            at = s[8]+minute*source.MINUTE
            f[at] = dict(bar=[at-15*source.MINUTE, 100000, 100050, 99995, 100040, 15],
                         atr_before=D(20), bias='BUY')
        for minute in (60, 90):
            at = s[8]+minute*source.MINUTE
            f[at] = dict(bar=[at-15*source.MINUTE, 100003, 100040, 99850, 100020, 15],
                         atr_before=D(20), bias='BUY')
            quotes.extend([(at, minute, 100020, 100022), (at+1000, minute+1, 100371, 100373)])
        d = b0.run_day('2022-06-01', f, quotes, b0.Account(), 'stress')
        self.assertEqual(d['counters']['filled_entries'], 2)
        self.assertEqual(d['counters']['bias_breakouts'], 2)
        same_event_quotes = quotes[:2]+[(s[8]+45*source.MINUTE, 3, 100371, 100373)]
        d = b0.run_day('2022-06-01', f, same_event_quotes, b0.Account(), 'stress')
        self.assertNotIn(s[8]+45*source.MINUTE, [e['at'] for e in d['events'] if e['kind'] == 'setup'])

    def test_four_bar_expiry_and_11am_cutoff(self):
        s, f, quotes = fixture()
        for minute in (30, 45, 60, 75):
            at = s[8]+minute*source.MINUTE
            f[at] = dict(bar=[at-15*source.MINUTE, 100100, 100200, 100090, 100150, 15],
                         atr_before=D(20), bias='BUY')
        d = b0.run_day('2022-06-01', f, quotes, b0.Account(), 'stress')
        self.assertEqual(d['counters']['setup_expired'], 1)
        f = {at: v for at, v in f.items() if at <= s[8]}
        f[s[11]-15*source.MINUTE] = dict(bar=[s[11]-30*source.MINUTE, 100000, 100050, 99995, 100040, 15],
                                      atr_before=D(20), bias='BUY')
        f[s[11]] = dict(bar=[s[11]-15*source.MINUTE, 100003, 100040, 99850, 100020, 15],
                       atr_before=D(20), bias='BUY')
        d = b0.run_day('2022-06-01', f, quotes, b0.Account(), 'stress')
        self.assertEqual(d['counters']['setup_cutoff_cancelled'], 1)
        self.assertEqual(d['trades'], [])

    def test_session_time_exit_requires_observed_quote(self):
        s, f, quotes = fixture()
        late = quotes[:2]+[(s[12], 3, 100040, 100042)]
        d = b0.run_day('2022-06-01', f, late, b0.Account(), 'stress')
        self.assertEqual(d['trades'][0]['exit_reason'], 'session_cutoff')
        self.assertFalse(d['trades'][0]['path_complete_under_60s_policy'])
        d = b0.run_day('2022-06-01', f, quotes[:2], b0.Account(), 'stress')
        self.assertIsNotNone(d['open_position'])

    def test_atr_before_bar_and_closed_h1_only(self):
        hour = 60*source.MINUTE
        h1 = [[i*hour, 100+i, 110+i, 90+i, 100+i, 60] for i in range(24)]
        m15 = [[i*15*source.MINUTE, 100, 110, 90, 100, 15] for i in range(100)]
        m15[20][2] = 100000
        f = b0.features(m15, h1)
        self.assertEqual(f[20*15*source.MINUTE]['atr_before'], D(20))
        self.assertEqual(f[21*15*source.MINUTE]['atr_before'], D(20))
        self.assertGreater(f[22*15*source.MINUTE]['atr_before'], 20)
        self.assertIsNone(f[23*hour-15*source.MINUTE]['bias'])
        self.assertEqual(f[23*hour]['bias'], 'BUY')

    def test_dst(self):
        from datetime import date, datetime, timedelta, timezone
        from zoneinfo import ZoneInfo
        winter = source.session('2022-01-10')
        summer = source.session('2022-06-01')
        self.assertEqual((winter[8]//3_600_000)%24, 8)
        self.assertEqual((summer[8]//3_600_000)%24, 7)
        day = date(2022, 1, 1)
        while day < date(2025, 1, 1):
            for at in source.session(day.isoformat()).values():
                self.assertEqual(datetime.fromtimestamp(at/1000, timezone.utc).astimezone(
                    ZoneInfo('Europe/Prague')).date(), day)
            day += timedelta(days=1)

    def test_daily_dd_is_not_peak_dd_and_fees_are_counted(self):
        a = b0.Account()
        a.mark(b0.INITIAL_CENTS+10000, b0.INITIAL_CENTS+9900, b0.INITIAL_CENTS, 1)
        a.mark(b0.INITIAL_CENTS-1000, b0.INITIAL_CENTS-1100, b0.INITIAL_CENTS, 2)
        self.assertEqual(a.max_dd, 11000)
        self.assertEqual(a.worst_daily_loss, 1000)
        self.assertEqual(a.worst_liquidation_daily_loss, 1100)

    def test_holdout_and_input_grid_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'not_authorized'):
            source.bounds('20240101', '20250101')
        with self.assertRaises(ValueError):
            source.units('1.000001')
        with self.assertRaises(ValueError):
            source.units('nan')

    def test_prepared_view_reuse_verifies_content_and_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            cfg = dict(path=str(p/'not_opened.csv'), sha256='already_sealed',
                       first_day='20220101', last_day='20221231')
            (p/'bars.json').write_text('{}')
            packet = dict(binding=dict(source=cfg, decoder_sha256=source.digest(source.__file__)),
                          files=[dict(name='bars.json', sha256=source.digest(p/'bars.json'))])
            source.write_json(p/'seal.json', packet)
            self.assertEqual(source.prepare(cfg, p, lambda **kw: None), packet)
            (p/'bars.json').write_text('{"tampered":true}')
            with self.assertRaisesRegex(ValueError, 'tamper'):
                source.prepare(cfg, p, lambda **kw: None)
            with self.assertRaisesRegex(ValueError, 'binding_changed'):
                source.prepare(dict(cfg, first_day='20230101'), p, lambda **kw: None)

    def test_csv_matches_native_and_seek_does_not_drop_first_tick(self):
        from trading_workspace_v2.forex_h4 import read_qdm_ticks
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'ticks.csv'
            text = 'DateTime,Bid,Ask,Volume\n'
            for i in range(300):
                text += f'20211029 12:00:00.{i:03d},1.00000,1.00002,0\n'
            for i in range(200):
                text += f'20211101 08:00:00.{i:03d},1.00001,1.00003,0\n'
            path.write_text(text, encoding='ascii')
            cfg = dict(path=str(path), sha256=source.digest(path), first_day='20211101',
                       last_day='20211231', slice_from_annual=True)
            rows = list(source.csv_rows(cfg))
            self.assertEqual(len(rows), 200)
            self.assertEqual(rows[0][0] % 1000, 0)
            subset = Path(tmp)/'subset.csv'
            subset.write_text('DateTime,Bid,Ask,Volume\n'+''.join(text.splitlines(keepends=True)[301:]))
            native = list(read_qdm_ticks(subset, sha256=source.digest(subset), first_day='20211101', last_day='20211231'))
            self.assertEqual(rows, [(q.time_msc, q.sequence, int(q.bid/ b0.GRID), int(q.ask/b0.GRID)) for q in native])


if __name__ == '__main__':
    unittest.main()
