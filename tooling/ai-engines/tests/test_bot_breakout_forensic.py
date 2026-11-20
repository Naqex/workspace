from datetime import datetime, timezone
from dataclasses import replace
import unittest
from unittest.mock import patch

import bot_breakout_forensic as forensic
from quant_core.live_trade_log import Trade


def wall(stamp):
    return int(datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc).timestamp()*1000)


def trade(row, sym='USDJPY', *, side='BUY', opened='2025-02-03T08:00:00', closed='2025-02-03T18:00:01', **kwargs):
    return Trade(row, sym, side, open_wall_ms=wall(opened), close_wall_ms=wall(closed),
                 open_date=opened[:10], close_date=closed[:10], **kwargs)


class BreakoutForensicsTests(unittest.TestCase):
    def test_far_tagged_stop_is_not_reclassified_as_a_time_exit(self):
        x=trade(1,open_price=140.,sl=139.9,close_price=139.894)
        hit=forensic.exit_evidence(x,'[sl]',.001)
        self.assertEqual((hit['label'],hit['mechanism']),('SL_TAG_OUTSIDE_ONE_TICK','SL'))
        self.assertEqual(forensic.exit_evidence(replace(x,close_price=139.899),'[sl]',.001)['label'],'HIT_EXACT_SL')
        self.assertEqual(forensic.exit_evidence(replace(x,close_price=140.0,sl=140.0),'[sl]',.001)['label'],
                         'BREAKEVEN_OR_TRAILING_STOP')
        self.assertEqual(forensic.exit_evidence(replace(x,close_price=140.2,tp=140.2),'[tp]',.001)['label'],'HIT_EXACT_TP')

    def test_concurrency_counts_opposite_side_and_removes_exact_timestamp_close(self):
        rows=[trade(1,closed='2025-02-03T12:00:00'),
              trade(2,side='SELL',opened='2025-02-03T11:59:52',closed='2025-02-03T13:00:00'),
              trade(3,opened='2025-02-03T12:00:00',closed='2025-02-03T13:01:00')]
        result=forensic.concurrency([{'trade':x} for x in rows])
        self.assertEqual((result['peak'],result['peak_same_symbol_and_side'],result['minimum_inter_entry_seconds']),
                         (2,1,8))

    def test_closed_drawdown_uses_grouped_closes_and_static_floor_is_separate(self):
        rows=[(trade(1,closed='2025-02-03T10:00:00',profit=100),100),
              (trade(2,closed='2025-02-03T11:00:00',profit=-90),100),
              (trade(3,closed='2025-02-03T11:00:00',profit=30),100)]
        d=forensic.drawdown([{'trade':x,'display_risk_usd':risk} for x,risk in rows])
        self.assertAlmostEqual(d['closed_R_proxy']['peak_to_valley'],.60)
        self.assertEqual(d['closed_R_proxy']['static_below_initial'],0)
        self.assertIsNone(d['true_initial_R_drawdown'])

    def test_real_shaped_export_keeps_profit_and_risk_proxies_separate_from_path(self):
        raw=(
            'Time;Type;Volume;Symbol;Price;S/L;T/P;Time;Price;Commission;Swap;Profit;Comment\n'
            '2025.01.31 17:00:00;Balance;;Deposit;;;;;;;;10 000.00;\n'
            '2025.02.03 05:01:00;Buy Stop;0.10;USDJPY;140.000;139.000;;'
            '2025.02.03 18:00:00;140.000;;;;cancelled\n'
            '2025.02.03 08:00:00;Buy;0.10;USDJPY;140.000;139.000;;'
            '2025.02.03 18:00:01;141.000;;;71.00;\n'
        ).encode('utf-8-sig')
        with patch('quant_core.ftmo_track_replay.Market.store',side_effect=AssertionError('Path access prohibited')):
            res,rows=forensic.analyze(raw)
        self.assertEqual(res['scope']['time_cohorts'],{'pre_2025':0,'post_2025':1,'straddles_2025':0})
        self.assertFalse(res['scope']['market_store_opened'])
        self.assertEqual(res['aggregate']['source_net_coverage'],0)
        self.assertIsNone(res['assets']['USDJPY']['actual_initial_r_multiple'])
        self.assertEqual(res['assets']['USDJPY']['clock']['pending_expiry_at_asset_cutoff'],1)
        self.assertEqual(rows[0]['bar_path'],'bar_path_skipped_holdout_lock')
        self.assertTrue(rows[0]['cutoff_5s'])
