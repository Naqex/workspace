from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tooling/ai-engines'))
import index_noise_study as study


def fixture():
    sessions, pairs = {}, {}
    start = datetime(2022, 1, 3, 14, 30, tzinfo=timezone.utc)
    for day in range(16):
        at = start+timedelta(days=day)
        stamps = list(range(int(at.timestamp()*1000), int(at.timestamp()*1000)+390*60000, 60000))
        sessions[at.date().isoformat()] = stamps
        for slot, stamp in enumerate(stamps):
            mid = 101 if day >= 14 and slot >= 29 else 100
            pairs[stamp] = tuple(dict(timestamp=stamp, open=mid+offset, close=mid+offset,
                high=mid+offset, low=mid+offset, volume=0) for offset in (-.01, .01))
    return sessions, pairs


class IndexNoiseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_band_arithmetic_uses_exact_14_past_slots(self):
        history = [dict(open=D(100), closes={29: D(102)}) for _ in range(14)]
        self.assertEqual(study.bands(history, D(110), D(100), 29), (D(98), D('112.20')))
        self.assertIsNone(study.bands(history[:-1], D(110), D(100), 29))
        history[0]['closes'].clear()
        self.assertIsNone(study.bands(history, D(110), D(100), 29))

    def test_unregistered_year_is_rejected_before_data_or_output_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            calendar = root/'calendar.json'
            calendar.write_text('{"year":2025}')
            output = root/'must-not-exist'
            argv = ['study', '--source-root', str(root/'missing-source'), '--data-root', str(root/'closed-holdout'),
                    '--calendar', str(calendar), '--protocol', str(root/'missing-protocol'), '--output', str(output)]
            with patch.object(sys, 'argv', argv), self.assertRaisesRegex(ValueError, 'holdout_closed'):
                study.main()
            self.assertFalse(output.exists())

    def test_decisions_fill_after_delay_and_flat_before_cash_close(self):
        sessions, pairs = fixture()
        result = study.simulate(sessions, pairs, slippage=D('.25'))
        stamps = list(sessions.values())[14]
        trade = result['trades'][0]
        self.assertEqual(trade['entry_time_msc'], stamps[31])
        self.assertEqual(trade['exit_time_msc'], stamps[-1])
        self.assertEqual(trade['reason'], 'scheduled_cash_flat')
        # The following day's prior-close anchor101 suppresses another entry.
        self.assertEqual(result['entries'], 1)
        self.assertIsNone(result['open_position'])
        self.assertEqual(D(result['balance_usd']), D(10000)+sum(D(t['net_usd']) for t in result['trades']))
        for trade in result['trades']:
            quantity, stop, entry = D(trade['quantity']), D(trade['stop']), D(trade['entry_fill'])
            self.assertLessEqual((abs(entry-stop)+D('.001')+D('.50'))*quantity+quantity, D(25))

    def test_missing_fill_expires_and_active_gap_remains_visible(self):
        sessions, pairs = fixture()
        stamps = list(sessions.values())[14]
        del pairs[stamps[31]]
        del pairs[stamps[100]]
        result = study.simulate(sessions, pairs, slippage=D('.25'))
        self.assertEqual(result['rejected'][0]['reason'], 'pending_fill_minute_missing')
        self.assertEqual(result['trades'][0]['entry_time_msc'], stamps[61])
        self.assertTrue(result['trades'][0]['path_unresolved'])
        self.assertEqual(result['gap_events'][0]['time_msc'], stamps[100])

    def test_future_changes_cannot_change_earlier_decisions_or_trades(self):
        sessions, pairs = fixture()
        base = study.simulate(sessions, pairs, slippage=D('.25'))
        modified = deepcopy(pairs)
        for stamp in list(sessions.values())[-1]:
            for row in modified[stamp]:
                for key in ('open', 'high', 'low', 'close'):
                    row[key] *= 2
        changed = study.simulate(sessions, modified, slippage=D('.25'))
        cutoff = list(sessions.values())[-1][0]
        self.assertEqual([d for d in base['decisions'] if d['time_msc'] < cutoff],
                         [d for d in changed['decisions'] if d['time_msc'] < cutoff])
        self.assertEqual(base['trades'][0], changed['trades'][0])

    def test_null_control_and_gap_stop_have_known_outcomes(self):
        sessions, pairs = fixture()
        control = study.simulate(sessions, pairs, slippage=D('.25'), null_control=True)
        self.assertEqual((control['entries'], control['net_equity_usd']), (0, '0'))
        stamp = list(sessions.values())[14][40]
        pairs[stamp] = tuple(dict(timestamp=stamp, open=99+offset, close=99+offset,
            high=99+offset, low=99+offset, volume=0) for offset in (-.01, .01))
        result = study.simulate(sessions, pairs, slippage=D('.25'))
        first = result['trades'][0]
        self.assertEqual(first['reason'], 'stop_loss_gap')
        self.assertEqual(D(first['exit_fill']), D('98.99'))
        # Gap beyond the stop may lose more than planned25USD; do not cap the loss.
        self.assertLess(D(first['net_usd']), D(-25))

    def test_missing_scheduled_flat_is_not_invented_and_short_session_exits_early(self):
        sessions, pairs = fixture()
        day = list(sessions)[14]
        sessions[day] = sessions[day][:210]
        result = study.simulate(sessions, pairs, slippage=D('.25'))
        self.assertEqual(result['trades'][0]['exit_time_msc'], sessions[day][-1])
        del pairs[sessions[day][-1]]
        unresolved = study.simulate(sessions, pairs, slippage=D('.25'))
        self.assertEqual(unresolved['trades'][0]['reason'], 'delayed_cash_flat')
        self.assertTrue(unresolved['trades'][0]['path_unresolved'])
        self.assertEqual(unresolved['trades'][0]['exit_time_msc'], list(sessions.values())[15][0])


if __name__ == '__main__':
    unittest.main()
