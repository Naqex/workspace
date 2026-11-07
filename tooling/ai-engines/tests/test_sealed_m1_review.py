from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sealed_m1_review import cash_sessions, digest, paired_spreads, review, validate_rows

CALENDAR = Path(__file__).resolve().parents[1]/'fixtures/nyse-2022.json'


def row(stamp=1640995200000, price=100.0):
    return dict(timestamp=stamp, open=price, close=price, high=price+1, low=price-1, volume=0)


class M1ReviewTests(unittest.TestCase):
    def test_calendar_holidays_half_day_and_dst_have_exact_utc_bounds(self):
        sessions = cash_sessions(json.loads(CALENDAR.read_text()))
        self.assertEqual(len(sessions), 251)
        self.assertNotIn('2022-06-20', sessions)
        self.assertIn('2022-12-30', sessions)
        self.assertEqual(len(sessions['2022-11-25']), 210)
        for day, first, last in [('2022-03-11', '14:30', '20:59'),
                                 ('2022-03-14', '13:30', '19:59'),
                                 ('2022-11-07', '14:30', '20:59'),
                                 ('2022-11-25', '14:30', '17:59')]:
            stamps = sessions[day]
            for stamp, expected in [(stamps[0], first), (stamps[-1], last)]:
                self.assertEqual(datetime.fromtimestamp(stamp/1000, timezone.utc).strftime('%H:%M'), expected)

    def test_price_and_timestamp_corruption_are_rejected(self):
        good = row()
        validate_rows([good], good['timestamp'], good['timestamp']+60000, .001)
        for changes in [dict(close=float('nan')), dict(open=100.0005), dict(volume=-1),
                        dict(timestamp=True), dict(high=99), dict(low=101)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_rows([{**good, **changes}], good['timestamp'], good['timestamp']+60000, .001)
        with self.assertRaisesRegex(ValueError, 'order'):
            validate_rows([good, good], good['timestamp'], good['timestamp']+60000, .001)

    def test_later_frozen_years_keep_official_half_days_and_holidays(self):
        for year, count, short_days in [(2023, 250, ['2023-07-03', '2023-11-24']),
                                       (2024, 252, ['2024-07-03', '2024-11-29', '2024-12-24'])]:
            sessions = cash_sessions(json.loads(CALENDAR.with_name(f'nyse-{year}.json').read_text()))
            self.assertEqual(len(sessions), count)
            self.assertEqual([day for day, stamps in sessions.items() if len(stamps) == 210], short_days)

    def test_independent_side_extrema_are_not_treated_as_simultaneous_spreads(self):
        bid = row()
        ask = {**row(price=100.1), 'low': 98, 'high': 103}
        self.assertEqual(len(paired_spreads([bid], [ask])), 2)
        with self.assertRaisesRegex(ValueError, 'negative_endpoint'):
            paired_spreads([bid], [{**ask, 'close': 99}])
        with self.assertRaisesRegex(ValueError, 'alignment'):
            paired_spreads([bid], [{**ask, 'timestamp': bid['timestamp']+60000}])

    def test_complete_review_keeps_gaps_and_rejects_changed_raw_or_seal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = {'requests': []}
            result = dict(status='downloaded_verified_M1_sides_needs_calendar_review',
                          strategySimulated=False, holdoutRead=False, brokerCalls=0, modelCalls=0,
                          requests=[])
            for q in range(1, 5):
                start = datetime(2022, 3*(q-1)+1, 1, tzinfo=timezone.utc)
                stop = datetime(2023, 1, 1, tzinfo=timezone.utc) if q == 4 else datetime(2022, 3*q+1, 1, tzinfo=timezone.utc)
                for side in ('bid', 'ask'):
                    stem = f'q{q}-{side}'
                    stamp = int(start.timestamp()*1000)
                    path = root/f'{stem}.json'
                    path.write_text(json.dumps([row(stamp, 100 if side == 'bid' else 100.1)]))
                    seal = dict(request=stem, rows=1, first=stamp, last=stamp, sha256=digest(path))
                    (root/f'{stem}-seal.json').write_text(json.dumps(seal))
                    result['requests'].append(seal)
                    manifest['requests'].append(dict(instrument='usa500idxusd', timeframe='m1',
                        priceType=side, dates={'from': start.isoformat(), 'to': stop.isoformat()}))
            (root/'manifest.json').write_text(json.dumps(manifest))
            (root/'result.json').write_text(json.dumps(result))
            report = review(root, CALENDAR, .001)
            self.assertEqual(report['status'], 'cash_gaps_require_protocol')
            self.assertEqual(report['expected_cash_minutes'], 97710)
            self.assertEqual(report['observed_cash_minutes'], 0)
            self.assertEqual(len(report['incomplete_sessions']), 251)
            original = (root/'q1-bid.json').read_bytes()
            (root/'q1-bid.json').write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError, 'seal_binding'):
                review(root, CALENDAR, .001)
            (root/'q1-bid.json').write_bytes(original)
            changed = deepcopy(result)
            changed['requests'][0]['rows'] = 2
            (root/'result.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'seal_binding'):
                review(root, CALENDAR, .001)


if __name__ == '__main__':
    unittest.main()
